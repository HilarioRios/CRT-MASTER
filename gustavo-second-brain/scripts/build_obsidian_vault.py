"""Genera un vault de Obsidian (carpeta de archivos .md planos, sin API --
Obsidian no necesita nada mas que abrir la carpeta) a partir de SQLite, para
poder navegar el Segundo Cerebro de forma visual (grafo, backlinks, busqueda
de texto completo). Reusa data/processed/youtube/<video_id>/transcript_clean.txt
tal cual (mismo archivo que sync_drive.py sube a Drive) -- no reprocesa ni
reinventa nada.

No incluye Shorts (include_in_knowledge_base=0, nunca llegan aca). Los 30
PENDING_ACCESS (YOUTUBE_MEMBERS_ONLY_EXCLUSIVE) aparecen como nota-stub sin
transcript (nunca se inventa contenido que no tenemos).

Uso:
    .venv/bin/python scripts/build_obsidian_vault.py
    .venv/bin/python scripts/build_obsidian_vault.py --out /ruta/a/otro/vault
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT = ROOT / "obsidian_vault"

INVALID_CHARS_RE = re.compile(r'[\\/:*?"<>|#\[\]^]')


def sanitize_filename(title: str, video_id: str, max_len: int = 80) -> str:
    """Un titulo real puede traer '/', '¡', '#', emojis, etc. -- cualquiera
    de esos rompe un path o un wikilink de Obsidian. video_id siempre va al
    final: garantiza nombre unico aunque dos titulos sanitizados coincidan."""
    clean = INVALID_CHARS_RE.sub("", title or "Sin titulo").strip()
    clean = re.sub(r"\s+", " ", clean)
    if len(clean) > max_len:
        clean = clean[:max_len].rstrip()
    return f"{clean} ({video_id})"


def sanitize_channel(channel: str) -> str:
    return INVALID_CHARS_RE.sub("", channel or "Sin canal").strip()


TAG_INVALID_RE = re.compile(r"[^a-zA-Z0-9_/-]")


def tag_slug(value: str) -> str:
    """Tags de Obsidian no aceptan espacios/puntos/acentos de forma
    confiable -- un slug plano evita que el tag se corte a la mitad."""
    slug = TAG_INVALID_RE.sub("-", value or "")
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "sin-dato"


def transcript_path_for(video_id: str) -> Path:
    """Mismo path que sync_drive.py FILE_ROLES['processed']['local'] -- no
    se reimplementa, solo se replica la convencion (un import cruzado aca
    agregaria una dependencia circular por poco beneficio real)."""
    return ROOT / "data" / "processed" / "youtube" / video_id / "transcript_clean.txt"


def fetch_sources(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT s.source_id, s.channel, s.original_title AS title, s.original_url,
                  s.published_at, s.published_year, s.processing_status,
                  s.internal_classification, s.transcript_source,
                  yv.video_id, yv.duration_sec,
                  (SELECT COUNT(*) FROM chunks c WHERE c.source_id = s.source_id) AS chunk_count
           FROM sources s JOIN youtube_videos yv ON yv.source_id = s.source_id
           WHERE s.include_in_knowledge_base = 1
           ORDER BY s.channel, s.published_at"""
    ).fetchall()
    return [dict(r) for r in rows]


def write_video_note(vault: Path, row: dict) -> Path | None:
    channel_dir = vault / sanitize_channel(row["channel"])
    channel_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(row["title"], row["video_id"]) + ".md"
    note_path = channel_dir / filename

    channel_link = sanitize_channel(row["channel"])
    year = row["published_year"] or "unknown"
    status_tag = "status/pending" if row["processing_status"] == "PENDING_ACCESS" else "status/synced"

    tags = ["youtube", tag_slug(row["channel"]), f"year/{year}", status_tag]
    tags_yaml = "[" + ", ".join(tags) + "]"

    frontmatter = [
        "---",
        f"source_id: {row['source_id']}",
        f"video_id: {row['video_id']}",
        f"channel: \"{row['channel']}\"",
        f"published_at: {row['published_at'] or ''}",
        f"url: {row['original_url'] or ''}",
        f"processing_status: {row['processing_status']}",
        f"transcript_source: {row['transcript_source'] or ''}",
        f"chunk_count: {row['chunk_count']}",
        f"tags: {tags_yaml}",
        "---",
        "",
    ]

    title = row["title"] or row["video_id"]
    header = [
        f"# {title}",
        "",
        f"[[{channel_link}]] · [[{year}]] · [Ver en YouTube]({row['original_url']})",
        "",
    ]

    if row["processing_status"] == "PENDING_ACCESS":
        body = [
            "> [!warning] Sin contenido",
            f"> `{row['internal_classification']}` -- contenido exclusivo de membresia paga de "
            "YouTube. No se pudo obtener el transcript (ni via OAuth de propietario, cuota de la "
            "API agotada al momento de generar este vault). Sin texto inventado.",
            "",
        ]
    else:
        transcript_path = transcript_path_for(row["video_id"])
        if transcript_path.exists():
            body = ["## Transcript", "", "```", transcript_path.read_text(encoding="utf-8").strip(), "```", ""]
        else:
            body = ["> [!warning] Transcript no encontrado localmente en "
                    f"`{transcript_path.relative_to(ROOT)}` al generar este vault.", ""]

    note_path.write_text("\n".join(frontmatter + header + body), encoding="utf-8")
    return note_path


def write_channel_moc(vault: Path, channel: str, rows: list[dict]) -> None:
    channel_link = sanitize_channel(channel)
    lines = [f"# {channel}", "", f"{len(rows)} fuentes en el knowledge base.", "", "## Videos", ""]
    by_year: dict[str, list[dict]] = {}
    for r in rows:
        by_year.setdefault(str(r["published_year"] or "unknown"), []).append(r)
    for year in sorted(by_year, reverse=True):
        lines.append(f"### {year}")
        for r in sorted(by_year[year], key=lambda r: r["published_at"] or ""):
            filename = sanitize_filename(r["title"], r["video_id"])
            marker = " ⛔ pendiente (membresia)" if r["processing_status"] == "PENDING_ACCESS" else ""
            lines.append(f"- [[{filename}|{r['title'] or r['video_id']}]]{marker}")
        lines.append("")
    (vault / f"{channel_link}.md").write_text("\n".join(lines), encoding="utf-8")


def write_root_index(vault: Path, rows: list[dict]) -> None:
    channels = sorted({r["channel"] for r in rows})
    ready = sum(1 for r in rows if r["processing_status"] == "DRIVE_SYNCED")
    pending = sum(1 for r in rows if r["processing_status"] == "PENDING_ACCESS")
    lines = [
        "# Gustavo Second Brain", "",
        f"{len(rows)} fuentes totales -- {ready} con transcript, {pending} pendientes (membresia paga).",
        "", "## Canales", "",
    ]
    for ch in channels:
        lines.append(f"- [[{sanitize_channel(ch)}]]")
    lines += ["", "---", "_Generado por `scripts/build_obsidian_vault.py` desde SQLite -- no editar a mano, se sobreescribe._"]
    (vault / "00_Index.md").write_text("\n".join(lines), encoding="utf-8")


def build(vault_path: Path = DEFAULT_VAULT, db_path: Path = None) -> dict:
    """db_path deja apuntar a una DB aislada en tests, igual que
    build_master_index.build() -- nunca caer silenciosamente a la DB de
    produccion cuando se pasa una explicita."""
    if db_path:
        init_db(db_path=db_path)
        conn = get_connection(db_path=db_path)
    else:
        init_db()
        conn = get_connection()
    try:
        rows = fetch_sources(conn)
    finally:
        conn.close()

    vault_path.mkdir(parents=True, exist_ok=True)
    written = 0
    for row in rows:
        write_video_note(vault_path, row)
        written += 1

    by_channel: dict[str, list[dict]] = {}
    for row in rows:
        by_channel.setdefault(row["channel"], []).append(row)
    for channel, channel_rows in by_channel.items():
        write_channel_moc(vault_path, channel, channel_rows)

    write_root_index(vault_path, rows)

    return {"notes_written": written, "channels": len(by_channel)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_VAULT)
    args = parser.parse_args()

    result = build(args.out)
    print(f"Vault generado en {args.out}: {result['notes_written']} notas, {result['channels']} canales.")
