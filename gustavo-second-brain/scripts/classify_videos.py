"""Capa de clasificacion/gobernanza (pre-piloto, ver instrucciones del
usuario). Usa la metadata ya descubierta (discover_videos_api.py /
discover_videos.py) MAS:
  - una llamada adicional READ-ONLY a
    videos().list(part='status,liveStreamingDetails') para youtube_privacy_status
    real (nunca inferido por el LLM) y deteccion de LIVE via la API.
  - video_tab_membership (ver discover_shorts_live_tabs.py): evidencia
    directa de yt-dlp enumerando las pestañas /shorts y /streams de cada
    canal -- lo que YouTube MISMO presenta ahi. Tiene prioridad sobre la
    heuristica de duracion/hashtag.

NO descarga transcripts, NO corre Whisper, NO genera embeddings, NO procesa
los videos. Solo clasifica con la metadata disponible y dejar pendiente
(NULL / UNKNOWN) lo que no se puede determinar con certeza.

Reglas deliberadas (no inventar clasificaciones; ver detect_content_format
para el orden de prioridad exacto):
- content_format: 1) /shorts tab -> SHORT, 2) /streams tab o
  liveStreamingDetails -> LIVE, 3) duration>180s -> LONG_FORM (regla dura de
  la plataforma, no heuristica debil), 4) '#shorts'/'#short' en titulo o
  descripcion (duration<=180s) -> SHORT, 5) cualquier otro caso -> UNKNOWN.
  Ausencia de hashtag NUNCA implica LONG_FORM por si sola -- es ausencia de
  evidencia, no evidencia de lo contrario.
- SHORT = inventario unicamente (ver classify_short_as_inventory_only). Los
  Shorts de Gustavo son en gran parte recortes de videos largos -- NO se
  tratan como fuentes independientes de conocimiento. Para un SHORT NUNCA se
  asigna primary_content_type, secondary_topics, source_authority_type,
  distribution_policy/internal_classification/allowed_audience, ni se
  analizan contradicciones. Solo se conserva metadata basica (video_id,
  channel, title, published_at/published_year, duration, url si es PUBLIC,
  youtube_privacy_status, content_format=SHORT) e
  include_in_knowledge_base=0 -- nunca se transcribe, nunca pasa por
  Whisper, nunca se chunkea ni se genera embedding, nunca entra a busquedas
  normales. Cualquier clasificacion semantica previa se limpia al
  reclasificar como SHORT (no se deja stale).
- derived_from_source_id / possible_parent_video_id / parent_match_confidence:
  columnas opcionales para una fase futura que relacione un Short con el
  video largo del que proviene. SIEMPRE NULL en esta fase -- no se gasta
  procesamiento intentando resolverlas ahora.
- primary_content_type / secondary_topics: para contenido NO-SHORT, se
  dejan sin clasificar (NULL / vacio) en esta pasada -- requieren transcript
  para una clasificacion confiable (se actualizan en una fase posterior).
  Cualquier clasificacion semantica futura debe ejecutarse SOLO sobre
  contenido con include_in_knowledge_base=1 (es decir, nunca sobre Shorts).
- temporal_status: siempre UNKNOWN por defecto -- no se infiere por fecha.
- potential_conflict: siempre 0 -- requiere evidencia de contenido real.
- distribution_policy / internal_classification / allowed_audience: para
  contenido NO-SHORT, se derivan de youtube_privacy_status via reglas fijas
  (ver privacy_to_distribution y audience_for_privacy), nunca por adivinanza.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402
from discover_videos_api import chunked  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SHORTS_MAX_DURATION_SEC = 180  # YouTube Shorts cap (expanded from 60s in 2024)


def detect_content_format(
    duration_sec: int | None,
    title: str | None,
    description: str | None,
    is_live: bool,
    is_short_tab: bool = False,
    is_live_tab: bool = False,
) -> str:
    """Priority order (strongest evidence first):
    1. is_short_tab -- video_id found in the channel's own /shorts tab
       (yt-dlp flat extraction, see discover_shorts_live_tabs.py). This is
       what YouTube itself presents as a Short; overrides everything else,
       including a duration that looks inconsistent with that (logged as a
       discrepancy in the report, not silently dropped).
    2. is_live_tab / is_live (API liveStreamingDetails) -- confirmed live.
    3. duration_sec > 180s -- a HARD platform rule (not a weak heuristic):
       YouTube caps Shorts at 180s, so anything longer cannot be one,
       regardless of hashtag presence or absence.
    4. '#shorts'/'#short' in title/description -- secondary signal, only
       used when duration_sec <= 180s.
    Anything else (duration <=180s, no tab confirmation, no hashtag) is
    UNKNOWN -- absence of a hashtag is NOT evidence of LONG_FORM, only
    absence of evidence."""
    if is_short_tab:
        return "SHORT"
    if is_live_tab or is_live:
        return "LIVE"
    if duration_sec is None:
        return "UNKNOWN"

    if duration_sec > SHORTS_MAX_DURATION_SEC:
        return "LONG_FORM"  # hard disqualifier, not duration-as-positive-evidence

    text = f"{title or ''} {description or ''}".lower()
    has_shorts_tag = "#shorts" in text or "#short" in text
    if has_shorts_tag:
        return "SHORT"
    return "UNKNOWN"  # duration<=180s, no tab/hashtag evidence either way


def privacy_to_distribution(privacy_status: str | None) -> tuple[str, str | None]:
    if privacy_status == "PUBLIC":
        return "SHAREABLE", None
    if privacy_status in ("PRIVATE", "UNLISTED"):
        return "ASK_BEFORE_SHARING", "PRIVATE_UNCLASSIFIED"
    return "ASK_BEFORE_SHARING", None  # unknown privacy -> safe default, no guess


def audience_for_privacy(privacy_status: str | None) -> list[str]:
    if privacy_status == "PUBLIC":
        return ["PUBLIC", "STUDENT", "VIP_STUDENT", "TEAM"]
    return ["TEAM"]  # PRIVATE, UNLISTED, or unknown -> most restrictive safe default


def compute_published_year(published_at: str | None) -> int | None:
    if not published_at or len(published_at) < 4:
        return None
    try:
        return int(published_at[:4])
    except ValueError:
        return None


def authority_type_for(content_format: str, privacy_status: str | None) -> str | None:
    """Never called for content_format='SHORT' in classify_all() -- Shorts
    get no semantic classification at all (see classify_short_as_inventory_only).
    Kept returning None here too so this function has no path that would
    assign a SHORT authority type, even if called directly."""
    if content_format == "LIVE":
        return "LIVE_STREAM"
    if content_format == "LONG_FORM" and privacy_status == "PUBLIC":
        return "LONG_FORM_YOUTUBE"
    return None  # SHORT, PRIVATE/UNLISTED long-form, CLIP, UNKNOWN -> no guess


def fetch_extra_metadata(youtube, video_ids: list[str]) -> dict[str, dict]:
    """READ-ONLY. Para cada video_id, devuelve {'privacy': 'PUBLIC'|'UNLISTED'|
    'PRIVATE'|None, 'is_live': bool}. Un id ausente en la respuesta (borrado)
    simplemente no aparece en el resultado."""
    result: dict[str, dict] = {}
    for batch in chunked(video_ids, 50):
        if not batch:
            continue
        resp = youtube.videos().list(
            part="status,liveStreamingDetails", id=",".join(batch)
        ).execute()
        for item in resp.get("items", []):
            status = item.get("status", {})
            privacy_raw = status.get("privacyStatus")
            privacy = privacy_raw.upper() if privacy_raw else None
            is_live = "actualStartTime" in item.get("liveStreamingDetails", {})
            result[item["id"]] = {"privacy": privacy, "is_live": is_live}
    return result


def fetch_tab_membership(conn) -> dict[str, set[str]]:
    """{video_id: {'shorts', 'streams'}} from video_tab_membership (see
    discover_shorts_live_tabs.py). Run that script first for this to have
    any effect; an empty table just means every video falls back to the
    duration/hashtag heuristic."""
    membership: dict[str, set[str]] = {}
    for row in conn.execute("SELECT video_id, tab_type FROM video_tab_membership"):
        membership.setdefault(row["video_id"], set()).add(row["tab_type"])
    return membership


def classify_short_as_inventory_only(conn, source_id: str, privacy: str | None, published_year: int | None) -> None:
    """A confirmed SHORT gets ONLY: content_format, youtube_privacy_status,
    include_in_knowledge_base=0, published_year (a reformatting of
    published_at, not analysis). Explicitly NEVER: primary_content_type,
    secondary_topics, source_authority_type, distribution_policy /
    internal_classification / allowed_audience derivation, temporal_status
    analysis, or conflict detection. Shorts are content-reuse clips of
    long-form videos (per the user) and exist only as inventory -- never as
    knowledge-base sources, never processed with transcripts/Whisper/
    embeddings. Any prior classification from before this video was
    (re)confirmed as a Short is wiped, not left stale -- including
    distribution_policy/temporal_status/potential_conflict, which are
    NOT NULL columns reset to their neutral schema default here rather than
    left at whatever a PRIOR non-SHORT classification pass computed (a video
    reclassified SHORT after new /shorts-tab evidence arrives must not keep
    carrying a stale 'SHAREABLE' distribution_policy from when it was still
    classified as regular PUBLIC content)."""
    conn.execute(
        """UPDATE sources SET
            content_format='SHORT', youtube_privacy_status=?, include_in_knowledge_base=0,
            published_year=?, source_authority_type=NULL, primary_content_type=NULL,
            internal_classification=NULL, distribution_policy='ASK_BEFORE_SHARING',
            temporal_status='UNKNOWN', potential_conflict=0
           WHERE source_id=?""",
        (privacy, published_year, source_id),
    )
    conn.execute("DELETE FROM source_allowed_audience WHERE source_id=?", (source_id,))
    conn.execute("DELETE FROM source_secondary_topics WHERE source_id=?", (source_id,))
    conn.execute(
        "DELETE FROM source_relations WHERE source_id=? OR related_source_id=?",
        (source_id, source_id),
    )


def classify_all(conn, youtube) -> int:
    rows = conn.execute(
        "SELECT video_id, source_id, title, description, duration_sec, published_at "
        "FROM youtube_videos"
    ).fetchall()
    video_ids = [r["video_id"] for r in rows]
    extra = fetch_extra_metadata(youtube, video_ids)
    tab_membership = fetch_tab_membership(conn)

    classified = 0
    for row in rows:
        meta = extra.get(row["video_id"], {})
        privacy = meta.get("privacy")
        is_live = meta.get("is_live", False)
        tabs = tab_membership.get(row["video_id"], set())

        content_format = detect_content_format(
            row["duration_sec"], row["title"], row["description"], is_live,
            is_short_tab="shorts" in tabs, is_live_tab="streams" in tabs,
        )
        published_year = compute_published_year(row["published_at"])

        if content_format == "SHORT":
            classify_short_as_inventory_only(conn, row["source_id"], privacy, published_year)
            classified += 1
            continue

        distribution_policy, internal_classification = privacy_to_distribution(privacy)
        audience = audience_for_privacy(privacy)
        authority = authority_type_for(content_format, privacy)

        conn.execute(
            """UPDATE sources SET
                content_format=?, youtube_privacy_status=?, include_in_knowledge_base=1,
                distribution_policy=?, internal_classification=?, published_year=?,
                source_authority_type=?
               WHERE source_id=?""",
            (content_format, privacy, distribution_policy,
             internal_classification, published_year, authority, row["source_id"]),
        )
        conn.execute(
            "DELETE FROM source_allowed_audience WHERE source_id=?", (row["source_id"],)
        )
        conn.executemany(
            "INSERT INTO source_allowed_audience (source_id, audience) VALUES (?, ?)",
            [(row["source_id"], aud) for aud in audience],
        )
        classified += 1

    conn.commit()
    return classified


def run() -> int:
    api_key = os.environ["YOUTUBE_API_KEY"]
    youtube = build("youtube", "v3", developerKey=api_key)

    init_db()
    conn = get_connection()
    try:
        return classify_all(conn, youtube)
    finally:
        conn.close()


if __name__ == "__main__":
    n = run()
    print(f"Clasificados {n} videos.")
