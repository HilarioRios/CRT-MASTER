"""FASE 12/21 -- Master Index. Exports a CSV snapshot of every source's
pipeline state, for human inspection and as the local source of truth
(a Drive-hosted copy in 00_ADMIN is a mirror of this, not the primary).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "database" / "MASTER_INDEX.csv"
DRIVE_STRUCTURE_PATH = ROOT / "config" / "drive_structure.json"
DRIVE_ADMIN_FILENAME = "MASTER_INDEX.csv"

COLUMNS = [
    "source_id", "source_type", "video_id", "title", "channel",
    "published_at", "published_year", "original_url", "transcript_source",
    "processing_status", "internal_classification", "topics", "raw_path", "processed_path",
    "drive_raw_url", "drive_processed_url", "drive_metadata_url", "chunk_count",
    "last_processed", "last_synced", "error",
    # Capa de clasificacion/gobernanza (ver classify_videos.py)
    "content_format", "youtube_privacy_status", "primary_content_type",
    "secondary_topics", "distribution_policy", "allowed_audience",
    "temporal_status", "source_authority_type", "include_in_knowledge_base",
    "potential_conflict",
]

DRIVE_FILE_URL = "https://drive.google.com/file/d/{file_id}/view"


def fetch_rows(conn) -> list:
    return conn.execute(
        """SELECT s.source_id, s.source_type, yv.video_id, s.original_title AS title,
                  s.channel, s.published_at, s.published_year, s.original_url,
                  s.transcript_source, s.processing_status, s.internal_classification,
                  s.raw_path, s.processed_path, s.last_processed,
                  s.content_format, s.youtube_privacy_status, s.primary_content_type,
                  s.distribution_policy, s.temporal_status, s.source_authority_type,
                  s.include_in_knowledge_base, s.potential_conflict,
                  ds.drive_raw_file_id, ds.drive_processed_file_id, ds.drive_metadata_file_id,
                  ds.synced_at AS last_synced,
                  (SELECT COUNT(*) FROM chunks c WHERE c.source_id = s.source_id) AS chunk_count,
                  (SELECT GROUP_CONCAT(message, ' | ') FROM errors e
                     WHERE e.source_id = s.source_id AND e.resolved = 0) AS error,
                  (SELECT GROUP_CONCAT(topic, '|') FROM source_secondary_topics t
                     WHERE t.source_id = s.source_id) AS secondary_topics,
                  (SELECT GROUP_CONCAT(audience, '|') FROM source_allowed_audience a
                     WHERE a.source_id = s.source_id) AS allowed_audience
           FROM sources s
           LEFT JOIN youtube_videos yv ON yv.source_id = s.source_id
           LEFT JOIN drive_sync ds ON ds.source_id = s.source_id
           ORDER BY s.channel, s.published_at"""
    ).fetchall()


def write_csv(rows: list, out_path: Path) -> int:
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for r in rows:
            # This CSV is mirrored to a shared Drive folder (see module
            # docstring). For an UNLISTED video the URL *is* the access
            # control, so never let a non-PUBLIC source's watchable link
            # leak into it -- unknown privacy is treated as non-public too.
            is_public = r["youtube_privacy_status"] == "PUBLIC"
            original_url = r["original_url"] if is_public else ""
            drive_raw_url = DRIVE_FILE_URL.format(file_id=r["drive_raw_file_id"]) if (is_public and r["drive_raw_file_id"]) else ""
            drive_processed_url = DRIVE_FILE_URL.format(file_id=r["drive_processed_file_id"]) if (is_public and r["drive_processed_file_id"]) else ""
            drive_metadata_url = DRIVE_FILE_URL.format(file_id=r["drive_metadata_file_id"]) if (is_public and r["drive_metadata_file_id"]) else ""

            writer.writerow([
                r["source_id"], r["source_type"], r["video_id"], r["title"],
                r["channel"], r["published_at"], r["published_year"] or "",
                original_url, r["transcript_source"],
                r["processing_status"], r["internal_classification"] or "", "",
                r["raw_path"] or "", r["processed_path"] or "",
                drive_raw_url, drive_processed_url, drive_metadata_url,
                r["chunk_count"], r["last_processed"] or "", r["last_synced"] or "", r["error"] or "",
                r["content_format"], r["youtube_privacy_status"] or "",
                r["primary_content_type"] or "", r["secondary_topics"] or "",
                r["distribution_policy"], r["allowed_audience"] or "",
                r["temporal_status"], r["source_authority_type"] or "",
                r["include_in_knowledge_base"], r["potential_conflict"],
            ])
    return len(rows)


def build(db_path: Path = None, out_path: Path = None) -> int:
    """db_path/out_path let tests point this at an isolated DB/file instead
    of the real production database -- db.get_connection()/init_db()'s own
    default arguments are bound once at import time, so passing None through
    to them would silently always target the production DB_PATH."""
    if db_path:
        init_db(db_path=db_path)
        conn = get_connection(db_path=db_path)
    else:
        init_db()
        conn = get_connection()
    try:
        rows = fetch_rows(conn)
        return write_csv(rows, out_path or OUT_PATH)
    finally:
        conn.close()


def publish_to_drive(drive_service, csv_path: Path = OUT_PATH) -> dict:
    """Espeja MASTER_INDEX.csv a 00_ADMIN/ en Drive. Idempotente: busca un
    archivo existente con el mismo nombre en esa carpeta y lo actualiza
    (mismo file_id, contenido nuevo) en vez de crear uno nuevo cada vez --
    igual que sync_drive.py hace con processed/metadata."""
    from googleapiclient.http import MediaFileUpload

    structure = json.loads(DRIVE_STRUCTURE_PATH.read_text())
    admin_folder_id = structure["sections"]["00_ADMIN"]

    existing = drive_service.files().list(
        q=f"name='{DRIVE_ADMIN_FILENAME}' and '{admin_folder_id}' in parents and trashed=false",
        fields="files(id,name)",
    ).execute().get("files", [])

    media = MediaFileUpload(str(csv_path), mimetype="text/csv", resumable=True)
    if existing:
        file_id = existing[0]["id"]
        drive_service.files().update(fileId=file_id, media_body=media).execute()
        return {"action": "updated", "file_id": file_id}

    created = drive_service.files().create(
        body={"name": DRIVE_ADMIN_FILENAME, "parents": [admin_folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    return {"action": "created", "file_id": created["id"]}


if __name__ == "__main__":
    n = build()
    print(f"MASTER_INDEX.csv escrito con {n} filas en {OUT_PATH}")
