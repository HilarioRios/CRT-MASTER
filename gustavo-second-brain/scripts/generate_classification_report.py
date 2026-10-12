"""Genera CLASSIFICATION_REPORT.md a partir de la metadata ya clasificada
(ver classify_videos.py) MAS la seccion DISCOVERY_RECONCILIATION (ver
reconcile_discovery.py). Solo lee la DB -- no llama a ninguna API, no
procesa videos. No expone URLs de videos privados/no publicos en el
reporte."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402
from reconcile_discovery import build_section as build_reconciliation_section  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "CLASSIFICATION_REPORT.md"

CONTENT_FORMATS = ["LONG_FORM", "SHORT", "LIVE", "CLIP", "UNKNOWN"]

MANUAL_REVIEW_WHERE = """
    content_format = 'UNKNOWN'
    OR youtube_privacy_status IS NULL
    OR internal_classification = 'PRIVATE_UNCLASSIFIED'
"""


def _count(conn, where: str, params: tuple = ()) -> int:
    # LEFT JOIN (not INNER): a source with no matching youtube_videos row
    # must still be counted here, consistent with how every other section's
    # totals count `sources` directly -- an INNER JOIN would silently
    # undercount this section relative to the rest of the same report if an
    # orphan source ever appeared.
    return conn.execute(
        f"SELECT COUNT(*) c FROM sources s LEFT JOIN youtube_videos yv ON yv.source_id=s.source_id "
        f"WHERE s.source_type='youtube' AND ({where})",
        params,
    ).fetchone()["c"]


def build_total_section(conn) -> list[str]:
    total = conn.execute("SELECT COUNT(*) c FROM sources WHERE source_type='youtube'").fetchone()["c"]
    return ["## Total", f"- TOTAL CANONICO DE VIDEOS UNICOS: {total}", ""]


def build_per_channel_section(conn) -> list[str]:
    rows = conn.execute(
        """SELECT channel,
                  COUNT(*) total,
                  SUM(CASE WHEN youtube_privacy_status='PUBLIC' THEN 1 ELSE 0 END) public,
                  SUM(CASE WHEN youtube_privacy_status='UNLISTED' THEN 1 ELSE 0 END) unlisted,
                  SUM(CASE WHEN youtube_privacy_status='PRIVATE' THEN 1 ELSE 0 END) private
           FROM sources WHERE source_type='youtube' GROUP BY channel ORDER BY total DESC"""
    ).fetchall()
    lines = ["## Por canal", "", "| canal | total | public | unlisted | private |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['channel']} | {r['total']} | {r['public']} | {r['unlisted']} | {r['private']} |")
    lines.append("")
    return lines


def build_format_section(conn) -> list[str]:
    rows = conn.execute(
        """SELECT content_format, COUNT(*) c FROM sources
           WHERE source_type='youtube' GROUP BY content_format"""
    ).fetchall()
    counts = {r["content_format"]: r["c"] for r in rows}
    lines = ["## Content format", ""]
    for fmt in CONTENT_FORMATS:
        lines.append(f"- {fmt}: {counts.get(fmt, 0)}")
    lines.append("")
    return lines


def build_shorts_summary_section(conn) -> list[str]:
    """Shorts are inventory-only (see classify_videos.classify_short_as_inventory_only)
    -- no thematic/semantic breakdown of them belongs here, just the count
    and the confirmation that none leaked into the knowledge base."""
    short_confirmed = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE source_type='youtube' AND content_format='SHORT'"
    ).fetchone()["c"]
    short_in_kb = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE source_type='youtube' "
        "AND content_format='SHORT' AND include_in_knowledge_base=1"
    ).fetchone()["c"]
    return [
        "## Shorts",
        f"- SHORTS CONFIRMADOS: {short_confirmed}",
        f"- EXCLUIDOS DEL KNOWLEDGE BASE: {short_confirmed}",
        f"- SHORTS_IN_KNOWLEDGE_BASE = {short_in_kb}",
        "",
    ]


def build_candidate_universe_section(conn) -> list[str]:
    """El universo real a procesar: todo lo NO-SHORT (los unicos
    excluidos de la knowledge base por ahora). Desglosado por
    content_format y por youtube_privacy_status."""
    total = conn.execute("SELECT COUNT(*) c FROM sources WHERE source_type='youtube'").fetchone()["c"]
    shorts = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE source_type='youtube' AND content_format='SHORT'"
    ).fetchone()["c"]
    candidate_total = total - shorts

    by_format = conn.execute(
        """SELECT content_format, COUNT(*) c FROM sources
           WHERE source_type='youtube' AND content_format != 'SHORT'
           GROUP BY content_format"""
    ).fetchall()
    format_counts = {r["content_format"]: r["c"] for r in by_format}

    by_privacy = conn.execute(
        """SELECT COALESCE(youtube_privacy_status, 'DESCONOCIDO') p, COUNT(*) c FROM sources
           WHERE source_type='youtube' AND content_format != 'SHORT'
           GROUP BY 1"""
    ).fetchall()
    privacy_counts = {r["p"]: r["c"] for r in by_privacy}

    lines = [
        "## Universo candidato para el Segundo Cerebro",
        f"- TOTAL = {total}",
        f"- menos SHORTS = {shorts}",
        f"- **CANDIDATOS = {candidate_total}**",
        "",
        "### Por content_format",
        f"- videos largos (LONG_FORM): {format_counts.get('LONG_FORM', 0)}",
        f"- lives (LIVE): {format_counts.get('LIVE', 0)}",
        f"- unknown (UNKNOWN): {format_counts.get('UNKNOWN', 0)}",
        f"- CLIP: {format_counts.get('CLIP', 0)}",
        "",
        "### Por youtube_privacy_status",
        f"- public: {privacy_counts.get('PUBLIC', 0)}",
        f"- unlisted: {privacy_counts.get('UNLISTED', 0)}",
        f"- private: {privacy_counts.get('PRIVATE', 0)}",
        f"- desconocido: {privacy_counts.get('DESCONOCIDO', 0)}",
        "",
    ]
    return lines


def build_knowledge_base_section(conn) -> list[str]:
    total = conn.execute("SELECT COUNT(*) c FROM sources WHERE source_type='youtube'").fetchone()["c"]
    included = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE source_type='youtube' AND include_in_knowledge_base=1"
    ).fetchone()["c"]
    excluded_short = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE source_type='youtube' "
        "AND include_in_knowledge_base=0 AND content_format='SHORT'"
    ).fetchone()["c"]
    excluded_total = total - included
    excluded_other = excluded_total - excluded_short
    pending_unknown = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE source_type='youtube' AND content_format='UNKNOWN'"
    ).fetchone()["c"]

    return [
        "## Knowledge base",
        f"- Incluidos (include_in_knowledge_base=true): {included}",
        f"- Excluidos por SHORT confirmado: {excluded_short}",
        f"- Excluidos por otra razon: {excluded_other}",
        f"- Pendientes (content_format=UNKNOWN -- NO excluidos de KB automaticamente, "
        f"requieren revision): {pending_unknown}",
        "",
    ]


def build_manual_review_section(conn) -> list[str]:
    manual_review = conn.execute(
        f"SELECT COUNT(*) c FROM sources WHERE source_type='youtube' AND ({MANUAL_REVIEW_WHERE})"
    ).fetchone()["c"]
    return [
        "## Revision manual requerida",
        f"- Videos con content_format=UNKNOWN, privacy desconocida, o "
        f"internal_classification=PRIVATE_UNCLASSIFIED: {manual_review}",
        "",
    ]


def build_private_videos_section(conn) -> list[str]:
    private_rows = conn.execute(
        """SELECT source_id, channel, youtube_privacy_status
           FROM sources
           WHERE source_type='youtube' AND youtube_privacy_status IN ('PRIVATE', 'UNLISTED')
           ORDER BY channel, source_id"""
    ).fetchall()
    lines = ["## Videos privados/no-publicos encontrados", f"- Total: {len(private_rows)}"]
    if private_rows:
        lines.append("")
        lines.append("| source_id | canal | youtube_privacy_status |")
        lines.append("|---|---|---|")
        for r in private_rows:
            lines.append(f"| {r['source_id']} | {r['channel'] or ''} | {r['youtube_privacy_status']} |")
    lines.append("")
    return lines


def build_shorts_live_evidence_section(conn) -> list[str]:
    short_by_tab = _count(
        conn,
        "s.content_format='SHORT' AND EXISTS (SELECT 1 FROM video_tab_membership t "
        "WHERE t.video_id=yv.video_id AND t.tab_type='shorts')",
    )
    short_total = _count(conn, "s.content_format='SHORT'")
    short_heuristic_only = short_total - short_by_tab

    live_by_tab = _count(
        conn,
        "s.content_format='LIVE' AND EXISTS (SELECT 1 FROM video_tab_membership t "
        "WHERE t.video_id=yv.video_id AND t.tab_type='streams')",
    )
    live_total = _count(conn, "s.content_format='LIVE'")
    live_api_only = live_total - live_by_tab

    discrepancies = conn.execute(
        """SELECT COUNT(*) c FROM video_tab_membership t
           JOIN youtube_videos yv ON yv.video_id = t.video_id
           WHERE t.tab_type='shorts' AND yv.duration_sec IS NOT NULL AND yv.duration_sec > 180"""
    ).fetchone()["c"]

    tab_only_not_in_main_discovery = conn.execute(
        """SELECT COUNT(*) c FROM video_tab_membership t
           LEFT JOIN youtube_videos yv ON yv.video_id = t.video_id
           WHERE yv.video_id IS NULL"""
    ).fetchone()["c"]

    return [
        "## Evidencia de SHORT y LIVE (pestañas /shorts, /streams vs heuristica)",
        f"- SHORT confirmados por pestaña /shorts (yt-dlp, evidencia fuerte): {short_by_tab}",
        f"- SHORT detectados solo por heuristica (#shorts/#short en titulo o descripcion, "
        f"sin confirmacion de pestaña): {short_heuristic_only}",
        f"- LIVE confirmados por pestaña /streams (yt-dlp): {live_by_tab}",
        f"- LIVE confirmados solo por la API (liveStreamingDetails, sin estar en /streams): {live_api_only}",
        f"- Discrepancias: video_id en /shorts con duration_sec>180s almacenado "
        f"(se prioriza la pestaña igual, duration tratada como no confiable aqui): {discrepancies}",
        f"- video_id presentes en /shorts o /streams pero NO encontrados en el discovery "
        f"principal (uploads playlist / yt-dlp /videos): {tab_only_not_in_main_discovery}",
        "",
    ]


def build_chronological_section(conn) -> list[str]:
    rows = conn.execute(
        """SELECT COALESCE(published_year, 0) published_year, COUNT(*) c
           FROM sources WHERE source_type='youtube' GROUP BY 1 ORDER BY 1"""
    ).fetchall()
    lines = ["## Distribucion cronologica por año"]
    for r in rows:
        year_label = r["published_year"] if r["published_year"] else "(sin fecha)"
        lines.append(f"- {year_label}: {r['c']}")
    lines.append("")
    return lines


def build_report(conn) -> str:
    lines = ["# CLASSIFICATION_REPORT", ""]
    lines.append(build_reconciliation_section(conn))
    lines += build_total_section(conn)
    lines += build_per_channel_section(conn)
    lines += build_format_section(conn)
    lines += build_shorts_summary_section(conn)
    lines += build_candidate_universe_section(conn)
    lines += build_knowledge_base_section(conn)
    lines += build_manual_review_section(conn)
    lines += build_private_videos_section(conn)
    lines += build_shorts_live_evidence_section(conn)
    lines += build_chronological_section(conn)
    return "\n".join(lines) + "\n"


def run() -> str:
    init_db()
    conn = get_connection()
    try:
        content = build_report(conn)
    finally:
        conn.close()
    OUT_PATH.write_text(content)
    return content


if __name__ == "__main__":
    run()
    print(f"CLASSIFICATION_REPORT.md escrito en {OUT_PATH}")
