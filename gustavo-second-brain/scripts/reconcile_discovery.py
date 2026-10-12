"""Reconcilia el conteo de videos descubiertos entre discover_videos.py
(yt-dlp) y discover_videos_api.py (YouTube Data API), para explicar
cualquier diferencia entre lo reportado por un run especifico y el total
real en SQLite. Solo lee la DB -- no llama a ninguna API externa."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402


def reconcile(conn) -> dict:
    total_distinct = conn.execute(
        "SELECT COUNT(DISTINCT video_id) c FROM youtube_videos"
    ).fetchone()["c"]

    by_channel = conn.execute(
        """SELECT yc.channel_name, COUNT(*) c
           FROM youtube_videos yv JOIN youtube_channels yc ON yc.channel_id = yv.channel_id
           GROUP BY 1 ORDER BY c DESC"""
    ).fetchall()

    duplicates = conn.execute(
        "SELECT COUNT(*) - COUNT(DISTINCT video_id) d FROM youtube_videos"
    ).fetchone()["d"]

    orphan_sources = conn.execute(
        """SELECT COUNT(*) c FROM sources s
           LEFT JOIN youtube_videos yv ON yv.source_id = s.source_id
           WHERE s.source_type = 'youtube' AND yv.video_id IS NULL"""
    ).fetchone()["c"]

    orphan_videos = conn.execute(
        """SELECT COUNT(*) c FROM youtube_videos yv
           LEFT JOIN sources s ON s.source_id = yv.source_id
           WHERE s.source_id IS NULL"""
    ).fetchone()["c"]

    by_availability = conn.execute(
        """SELECT yc.channel_name, yv.availability, COUNT(*) c,
                  MIN(s.created_at) first_inserted, MAX(s.created_at) last_inserted
           FROM youtube_videos yv
           JOIN youtube_channels yc ON yc.channel_id = yv.channel_id
           JOIN sources s ON s.source_id = yv.source_id
           GROUP BY 1, 2 ORDER BY 1, 2"""
    ).fetchall()

    return {
        "total_distinct": total_distinct,
        "by_channel": by_channel,
        "duplicates": duplicates,
        "orphan_sources": orphan_sources,
        "orphan_videos": orphan_videos,
        "by_availability": by_availability,
    }


# availability values a normal, fully-fetched video can have (one label per
# discovery method: yt-dlp's own classifier says 'public', the API-based
# script hardcodes 'available'). Anything else (e.g. 'members_only',
# 'unavailable') is content the API's public uploads-playlist enumeration
# cannot see at all -- that's the structural source of any found-vs-total gap.
NORMAL_AVAILABILITY = {"available", "public"}


def build_section(conn) -> str:
    r = reconcile(conn)

    gated_rows = [row for row in r["by_availability"] if row["availability"] not in NORMAL_AVAILABILITY]
    gated_total = sum(row["c"] for row in gated_rows)
    api_visible_total = r["total_distinct"] - gated_total

    lines = ["## DISCOVERY_RECONCILIATION", ""]
    lines.append(f"- **COUNT(DISTINCT video_id) real en SQLite: {r['total_distinct']}**")
    lines.append("")
    lines.append("### Por canal")
    for row in r["by_channel"]:
        lines.append(f"- {row['channel_name']}: {row['c']}")
    lines.append("")

    lines.append("### Integridad de datos")
    lines.append(f"- Duplicados logicos (mismo video_id repetido): {r['duplicates']}")
    lines.append(f"- Sources sin fila en youtube_videos (huerfanos): {r['orphan_sources']}")
    lines.append(f"- Filas en youtube_videos sin source (huerfanos): {r['orphan_videos']}")
    lines.append("")

    lines.append("### Desglose por canal + availability + cuando se insertaron")
    lines.append("| canal | availability | cantidad | primera insercion | ultima insercion |")
    lines.append("|---|---|---|---|---|")
    for row in r["by_availability"]:
        lines.append(
            f"| {row['channel_name']} | {row['availability']} | {row['c']} | "
            f"{row['first_inserted']} | {row['last_inserted']} |"
        )
    lines.append("")

    lines.append("### Explicacion del gap entre un run de discover_videos_api.py y el total real")
    lines.append(
        "Un run de discover_videos_api.py reporta como `found` lo que "
        "`playlistItems().list` devuelve sobre la uploads playlist oficial "
        "del canal. Ese endpoint NO incluye contenido con availability fuera "
        f"de {sorted(NORMAL_AVAILABILITY)} (p.ej. `members_only`): ese "
        "contenido es invisible para la API publica sin credenciales de "
        "miembro del canal, aunque yt-dlp (discover_videos.py) SI lo "
        "encuentra al recorrer el listado general de videos -- solo que no "
        "puede descargar su metadata completa, y queda con "
        "`processing_status='FAILED'`."
    )
    lines.append("")
    if gated_total:
        lines.append(
            f"En esta base de datos hay **{gated_total}** video(s) en esa "
            f"situacion (ver filas con availability fuera de "
            f"{sorted(NORMAL_AVAILABILITY)} en la tabla de arriba). Un run de "
            f"discover_videos_api.py nunca los cuenta en su `found`, pero "
            f"tampoco los borra ni los duplica -- simplemente nunca aparecen "
            f"en su enumeracion. Por eso `found` (lo que la API ve) = "
            f"**{api_visible_total}**, mientras que el total real en SQLite "
            f"(lo que la API ve + lo que yt-dlp encontro pero la API no ve) = "
            f"**{r['total_distinct']}**."
        )
    else:
        lines.append(
            f"En esta base de datos no hay actualmente ningun video con "
            f"availability fuera de {sorted(NORMAL_AVAILABILITY)}, asi que "
            f"`found` de un run de la API y el total real en SQLite deberian "
            f"coincidir ({r['total_distinct']})."
        )
    lines.append("")
    lines.append(
        f"**{r['total_distinct']} es la cifra canonica**, verificada arriba "
        f"por COUNT(DISTINCT video_id) directamente contra SQLite (no un "
        f"numero recordado de una corrida anterior). Duplicados logicos: "
        f"{r['duplicates']}. Huerfanos: {r['orphan_sources'] + r['orphan_videos']}. "
        "CLASSIFICATION_REPORT.md y MASTER_INDEX.csv son la fuente canonica "
        "de aqui en adelante; DISCOVERY_REPORT.md queda como registro "
        "historico de una corrida especifica (su `found` nunca pretendio "
        "ser el total del proyecto, solo lo que esa corrida en particular vio)."
    )
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    init_db()
    conn = get_connection()
    try:
        print(build_section(conn))
    finally:
        conn.close()
