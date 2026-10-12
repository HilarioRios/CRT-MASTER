"""FASE 18 -- Query CLI. SQLite FTS5 search with a small synonym
expansion table, since the raw question's exact words rarely appear
verbatim in auto-generated captions (see config/term_corrections.json
and build_search_index.py for why).

Anti-hallucination rule (FASE 9): this script NEVER generates a prose
answer. It only returns evidence -- title, channel, timestamp, fragment,
deep link -- or says explicitly that no evidence was found. Turning
evidence into a prose answer is a job for whoever reads the results
(a human, or an LLM strictly grounded in exactly this evidence), never
for this script.

Privacy (added for the pilot): only searches sources with
include_in_knowledge_base=1 -- this excludes SHORTS (inventory-only, never
a knowledge source, see classify_videos.py) and anything else not meant
for the knowledge base. A non-PUBLIC source (youtube_privacy_status
UNLISTED/PRIVATE/unknown) can still surface as evidence for an authorized
internal query (distribution_policy/allowed_audience govern WHO can query,
not whether this script itself hides the result) but every such result
carries `is_public=False` and a `privacy_warning` field the caller must
show -- never silently treat it like public evidence.

Usage:
    python scripts/query.py "¿Cómo define Gustavo el bias diario?"
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

PRIVACY_WARNING = (
    "⚠️ FUENTE PRIVADA / VIP\n"
    "Consultar antes de compartir el material o enlace fuera del entorno autorizado."
)

STOPWORDS = {
    "que", "el", "la", "los", "las", "un", "una", "de", "del", "y", "o",
    "a", "en", "con", "para", "por", "su", "sus", "es", "qué", "cómo",
    "cual", "cuál", "dice", "sobre", "mira", "primero", "plantea",
    "gustavo", "como", "diferencia",
}

# Synonym/expansion groups: if any word in the question matches a group's
# trigger(s), OR in the whole group when building the FTS query. Keeps
# the master spec's own example mappings (FASE 17) plus the known ASR
# corrections already applied at index time (so "bias" alone already
# matches "vallas"/"bías" -- these add further real synonyms on top).
SYNONYM_GROUPS: list[tuple[set[str], list[str]]] = [
    ({"bias"}, ["bias", "direccion", "sesgo", "dol"]),
    ({"diario", "diaria"}, ["diario", "dia", '"todos los dias"']),
    ({"sobreoperar", "sobreoperando"}, ["sobreoperar", '"operar de mas"', '"operar demasiado"', "paciencia", "timing"]),
    ({"timeframe", "temporalidad"}, ["temporalidad", "timeframe", "marco"]),
    ({"asia", "asiatica"}, ["asia", "asiatica", "tokio", "sesion"]),
    ({"riesgo"}, ["riesgo", "stoploss", "stop", '"stop loss"']),
    ({"estrategia"}, ["estrategia", "metodologia"]),
    ({"metodo", "método"}, ["metodo", "metodologia"]),
    ({"crt"}, ["crt"]),
    ({"error", "errores"}, ["error", "errores", "fallo", "falla"]),
]


def _fold(text: str) -> str:
    """Lowercase + strip accents, so 'días' and 'dias' compare equal."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def expand_query(question: str) -> tuple[list[set[str]], list[str]]:
    """Returns (concepts, fts_terms). Each concept is the set of plain
    (accent-folded, unquoted) surface forms that would satisfy it --
    either a question word on its own, or a whole synonym group it
    triggered. fts_terms (quoted where needed, for phrase matches) is
    used to build the FTS MATCH query; concepts are used by the
    relevance gate below so that e.g. "bias" matching via its synonym
    "direccion" still counts as satisfying the SAME concept, not a
    coincidental extra word."""
    words = [w for w in re.findall(r"[a-záéíóúñü]+", question.lower())
              if w not in STOPWORDS and len(w) >= 3]
    concepts: list[set[str]] = []
    fts_terms: set[str] = set()
    for w in words:
        group_surface_forms = None
        for triggers, synonyms in SYNONYM_GROUPS:
            if w in triggers:
                group_surface_forms = synonyms
                break
        surface_forms = group_surface_forms or [w]
        concepts.append({_fold(t.strip('"')) for t in surface_forms})
        fts_terms.update(surface_forms)
    # dedupe identical concepts (e.g. same group triggered twice)
    unique_concepts = []
    for c in concepts:
        if c not in unique_concepts:
            unique_concepts.append(c)
    return unique_concepts, sorted(fts_terms)


def _concepts_matched(text: str, concepts: list[set[str]]) -> int:
    folded = _fold(text)
    return sum(1 for concept in concepts if any(term in folded for term in concept))


def search(question: str, limit: int = 8, min_concept_matches: int = 2, db_path=None) -> list[dict]:
    """db_path: solo para tests -- apunta search() a una DB aislada en vez
    de la de produccion (get_connection()/init_db() con sus defaults, que
    de otro modo siempre apuntarian a la DB real)."""
    concepts, terms = expand_query(question)
    if not terms:
        return []
    match_query = " OR ".join(terms)

    if db_path:
        init_db(db_path=db_path)
        conn = get_connection(db_path=db_path)
    else:
        init_db()
        conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT cs.chunk_id, cs.text AS search_text, c.start_sec, c.text,
                      s.source_id, s.original_title, s.channel, s.original_url,
                      s.published_at, s.youtube_privacy_status,
                      bm25(chunks_search) AS rank
               FROM chunks_search cs
               JOIN chunks c ON c.chunk_id = cs.chunk_id
               JOIN sources s ON s.source_id = c.source_id
               WHERE chunks_search MATCH ? AND s.include_in_knowledge_base = 1
               ORDER BY rank
               LIMIT ?""",
            (match_query, limit * 4),  # overfetch, then filter by relevance
        ).fetchall()
    finally:
        conn.close()

    # Relevance gate: a single coincidental word match (e.g. "invertir"
    # meaning "spend time" matching a question about investing money)
    # is not evidence. Require the chunk to actually satisfy at least
    # `min_concept_matches` distinct concepts from the question -- or
    # all of them, if the question has fewer concepts than that
    # threshold. A concept counts as satisfied if ANY of its synonym
    # surface forms appears (so "bias" satisfied via "direccion" still
    # counts as one concept, not an extra). Checked against search_text
    # (term-corrected) since that's what words like "bias" actually
    # match against -- the verbatim text may only have the ASR
    # mistranscription ("vallas").
    required = min(min_concept_matches, len(concepts)) or 1
    rows = [r for r in rows if _concepts_matched(r["search_text"], concepts) >= required][:limit]

    results = []
    for row in rows:
        start = int(row["start_sec"])
        h, m, s = start // 3600, (start % 3600) // 60, start % 60
        timestamp = f"{h:02d}:{m:02d}:{s:02d}"
        is_public = row["youtube_privacy_status"] == "PUBLIC"
        deep_link = f"{row['original_url']}&t={start}s" if row["original_url"] else None
        results.append({
            "source_id": row["source_id"],
            "title": row["original_title"],
            "channel": row["channel"],
            "published_at": row["published_at"],
            "timestamp": timestamp,
            "fragment": row["text"][:400],
            "deep_link": deep_link,
            "chunk_id": row["chunk_id"],
            "is_public": is_public,
            "privacy_warning": None if is_public else PRIVACY_WARNING,
        })
    return results


def main(question: str) -> None:
    results = search(question)
    if not results:
        print("No encontré evidencia suficiente dentro de la base de conocimiento de Gustavo.")
        return

    print(f'Pregunta: "{question}"\n')
    for i, r in enumerate(results, 1):
        print(f"{i}.")
        print(f"Título: {r['title']}")
        print(f"Canal: {r['channel']}")
        print(f"Fecha: {r['published_at']}")
        print(f"Timestamp: {r['timestamp']}")
        print(f"Fragmento: {r['fragment']}")
        print(f"source_id: {r['source_id']}")
        if r["is_public"]:
            print(f"Fuente: {r['deep_link']}")
        else:
            print(r["privacy_warning"])
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python scripts/query.py "tu pregunta"')
        sys.exit(1)
    main(sys.argv[1])
