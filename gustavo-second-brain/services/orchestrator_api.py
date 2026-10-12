"""Bridge local entre n8n (contenedor Docker) y el pipeline Python existente
(este repo, corriendo en .venv con ffmpeg/yt-dlp/faster-whisper locales).

NO reimplementa logica del pipeline: cada endpoint importa y llama
directamente a las funciones ya existentes y probadas en scripts/ (db,
sync_drive, build_master_index). Este servicio solo decide QUE fuentes
estan listas para sincronizar y expone eso como HTTP para que n8n pueda
orquestarlo, tal como sync_drive.run() ya estaba disenado para aceptar
("un futuro trigger, n8n u otro orquestador").

Corre con el venv del proyecto, nunca dentro del contenedor de n8n:
    .venv/bin/uvicorn services.orchestrator_api:app --host 0.0.0.0 --port 8731

n8n (en Docker, macOS) le pega via host.docker.internal:8731 -- no via
localhost, porque localhost dentro del contenedor es el contenedor mismo.
"""
from __future__ import annotations

import re
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from db import get_connection, DB_PATH  # noqa: E402
from sync_drive import (  # noqa: E402
    sync_source,
    get_drive_service,
    DRIVE_TOKEN_FILE,
    DRIVE_STRUCTURE_PATH,
)
from build_master_index import build as build_master_index, publish_to_drive  # noqa: E402
import discover_videos_api  # noqa: E402
import discover_shorts_live_tabs  # noqa: E402
import classify_videos  # noqa: E402
import run_pipeline  # noqa: E402

app = FastAPI(title="Gustavo Second Brain Orchestrator", version="1.0.0")

# -- Fuentes "listas para sincronizar": ya pasaron fetch/normalize/chunk
# localmente (processing_status en este set) pero todavia no llegaron a
# DRIVE_SYNCED. FAILED y PENDING_ACCESS (members-only) quedan afuera a
# proposito -- ver scripts/run_pipeline.py STEP_RANK para el significado
# de cada estado.
READY_STATUSES = ("PROCESSED", "CHUNKED", "INDEXED")

# -------------------------------------------------------------------------
# Jobs en memoria -- este servicio es efimero por diseno (un bridge local,
# no un sistema de colas). Si el proceso se reinicia a mitad de un job, el
# job se pierde, pero el trabajo YA HECHO en SQLite/Drive no se pierde ni
# se duplica (sync_source es idempotente) -- solo hay que volver a llamar
# POST /jobs/sync-ready.
# -------------------------------------------------------------------------
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_SECRET_PATTERNS = [
    re.compile(r"key=[^&\s\"']+", re.IGNORECASE),       # ?key=<API key> in Google API URLs
    re.compile(r"access_token=[^&\s\"']+", re.IGNORECASE),
    re.compile(r"Bearer [A-Za-z0-9_\-.]+", re.IGNORECASE),
]


def _sanitize(message: str) -> str:
    """Las HttpError de googleapiclient incluyen la URL completa del
    request en su __str__, que para llamadas con API key (discover_videos_api,
    classify_videos) incluye `?key=...` en texto plano. Nunca se debe
    persistir ni devolver eso tal cual -- ver seccion 12 del pedido del
    usuario (no imprimir API keys/tokens)."""
    out = message
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(lambda m: m.group(0).split("=")[0] + "=***REDACTED***" if "=" in m.group(0) else "***REDACTED***", out)
    return out


def _db_counts() -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM sources WHERE include_in_knowledge_base=1) AS total,
                 (SELECT COUNT(*) FROM sources WHERE include_in_knowledge_base=1
                    AND processing_status NOT IN ('DISCOVERED','METADATA_READY','TRANSCRIPT_PENDING',
                                                   'PENDING_ACCESS')) AS processed,
                 (SELECT COUNT(*) FROM sources WHERE include_in_knowledge_base=1
                    AND processing_status='DRIVE_SYNCED') AS drive_synced,
                 (SELECT COUNT(*) FROM sources WHERE include_in_knowledge_base=1
                    AND processing_status IN ('DISCOVERED','METADATA_READY','TRANSCRIPT_PENDING',
                                               'TRANSCRIPT_READY','PROCESSED','CHUNKED','INDEXED')) AS pending,
                 (SELECT COUNT(*) FROM sources WHERE include_in_knowledge_base=1
                    AND processing_status='FAILED') AS failed,
                 (SELECT COUNT(*) FROM sources WHERE include_in_knowledge_base=1
                    AND processing_status='PENDING_ACCESS') AS members_only
            """
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def _ready_source_ids() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT source_id FROM sources
                WHERE include_in_knowledge_base=1
                  AND processing_status IN ({",".join("?" * len(READY_STATUSES))})
                ORDER BY source_id""",
            READY_STATUSES,
        ).fetchall()
        return [r["source_id"] for r in rows]
    finally:
        conn.close()


def _failed_source_ids() -> list[str]:
    """FAILED, excluyendo PENDING_ACCESS (esos tienen su propio estado y
    su propio flujo -- no se tocan aca)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT source_id FROM sources
               WHERE include_in_knowledge_base=1 AND processing_status='FAILED'
               ORDER BY source_id"""
        ).fetchall()
        return [r["source_id"] for r in rows]
    finally:
        conn.close()


class JobStatus(BaseModel):
    job_id: str
    kind: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "PARTIAL", "FAILED"]
    created_at: str
    finished_at: str | None = None
    metrics: dict


def _run_sync_job(job_id: str, source_ids: list[str]) -> None:
    with JOBS_LOCK:
        JOBS[job_id]["status"] = "RUNNING"

    metrics = {
        "FOUND_READY": len(source_ids),
        "UPLOADED": 0,
        "SKIPPED_ALREADY_SYNCED": 0,
        "FAILED": 0,
        "PENDING_MEMBERS_ONLY": _db_counts()["members_only"],
        "details": [],
    }

    try:
        drive_service = get_drive_service()
        conn = get_connection()
        try:
            for source_id in source_ids:
                try:
                    summary = sync_source(conn, drive_service, source_id)
                except Exception as exc:  # noqa: BLE001 -- una fuente mala no debe tumbar el job
                    metrics["FAILED"] += 1
                    metrics["details"].append({"source_id": source_id, "status": "error", "detail": _sanitize(str(exc))})
                    continue

                statuses = {role: r["status"] for role, r in summary["files"].items()}
                if summary["all_ok"]:
                    if all(s == "already_synced" for s in statuses.values()):
                        metrics["SKIPPED_ALREADY_SYNCED"] += 1
                    else:
                        metrics["UPLOADED"] += 1
                    metrics["details"].append({"source_id": source_id, "status": "ok", "files": statuses})
                else:
                    metrics["FAILED"] += 1
                    metrics["details"].append({"source_id": source_id, "status": "drive_sync_failed", "files": statuses})
        finally:
            conn.close()

        build_master_index()
        try:
            drive_publish = publish_to_drive(drive_service)
            metrics["master_index_drive"] = drive_publish
        except Exception as exc:  # noqa: BLE001 -- el index local ya quedo bien, esto es best-effort
            metrics["master_index_drive_error"] = _sanitize(str(exc))

        final_status = "COMPLETED" if metrics["FAILED"] == 0 else ("PARTIAL" if metrics["UPLOADED"] or metrics["SKIPPED_ALREADY_SYNCED"] else "FAILED")
        with JOBS_LOCK:
            JOBS[job_id]["status"] = final_status
            JOBS[job_id]["finished_at"] = _now()
            JOBS[job_id]["metrics"] = metrics
    except Exception as exc:  # noqa: BLE001 -- fallo de infraestructura (p.ej. Drive no autenticado)
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "FAILED"
            JOBS[job_id]["finished_at"] = _now()
            metrics["error"] = _sanitize(str(exc))
            JOBS[job_id]["metrics"] = metrics


@app.get("/health")
def health():
    checks = {"sqlite_accessible": False, "drive_config_present": False, "pipeline_available": False}
    detail = {}

    try:
        conn = get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        checks["sqlite_accessible"] = True
    except Exception as exc:  # noqa: BLE001
        detail["sqlite_error"] = _sanitize(str(exc))

    checks["drive_config_present"] = DRIVE_TOKEN_FILE.exists() and DRIVE_STRUCTURE_PATH.exists()
    if not checks["drive_config_present"]:
        detail["drive_missing"] = [
            p for p in (str(DRIVE_TOKEN_FILE), str(DRIVE_STRUCTURE_PATH))
            if not Path(p).exists()
        ]

    checks["pipeline_available"] = (ROOT / "scripts" / "run_pipeline.py").exists() and (ROOT / ".venv").exists()

    ok = all(checks.values())
    return {"ok": ok, "checks": checks, "detail": detail, "db_path": str(DB_PATH)}


@app.get("/status")
def status():
    return _db_counts()


@app.post("/jobs/sync-ready")
def sync_ready():
    source_ids = _ready_source_ids()
    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id, "kind": "sync-ready", "status": "QUEUED",
            "created_at": _now(), "finished_at": None, "metrics": {"FOUND_READY": len(source_ids)},
        }
    thread = threading.Thread(target=_run_sync_job, args=(job_id, source_ids), daemon=True)
    thread.start()
    return {"job_id": job_id, "found_ready": len(source_ids)}


@app.post("/jobs/retry-drive-failed")
def retry_drive_failed():
    source_ids = _failed_source_ids()
    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id, "kind": "retry-drive-failed", "status": "QUEUED",
            "created_at": _now(), "finished_at": None, "metrics": {"FOUND_READY": len(source_ids)},
        }
    thread = threading.Thread(target=_run_sync_job, args=(job_id, source_ids), daemon=True)
    thread.start()
    return {"job_id": job_id, "found_failed": len(source_ids)}


def _all_source_ids(conn) -> set[str]:
    return {r["source_id"] for r in conn.execute("SELECT source_id FROM sources").fetchall()}


def _run_detect_job(job_id: str) -> None:
    with JOBS_LOCK:
        JOBS[job_id]["status"] = "RUNNING"

    metrics: dict = {}
    try:
        conn = get_connection()
        try:
            before_ids = _all_source_ids(conn)
        finally:
            conn.close()

        discover_summary = discover_videos_api.run()
        metrics["discover_per_channel"] = discover_summary

        discover_shorts_live_tabs.run()
        classify_videos.run()

        conn = get_connection()
        try:
            after_ids = _all_source_ids(conn)
            new_ids = after_ids - before_ids
            metrics["NEW_VIDEOS_FOUND"] = len(new_ids)

            if new_ids:
                placeholders = ",".join("?" * len(new_ids))
                rows = conn.execute(
                    f"""SELECT content_format, include_in_knowledge_base, COUNT(*) AS n
                        FROM sources WHERE source_id IN ({placeholders})
                        GROUP BY content_format, include_in_knowledge_base""",
                    tuple(new_ids),
                ).fetchall()
                metrics["new_by_classification"] = [dict(r) for r in rows]
                metrics["NEW_READY_FOR_PIPELINE"] = sum(
                    r["n"] for r in rows if r["include_in_knowledge_base"] == 1
                )
                metrics["NEW_EXCLUDED_SHORTS"] = sum(
                    r["n"] for r in rows if r["content_format"] == "SHORT"
                )
            else:
                metrics["new_by_classification"] = []
                metrics["NEW_READY_FOR_PIPELINE"] = 0
                metrics["NEW_EXCLUDED_SHORTS"] = 0
        finally:
            conn.close()

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "COMPLETED"
            JOBS[job_id]["finished_at"] = _now()
            JOBS[job_id]["metrics"] = metrics
    except Exception as exc:  # noqa: BLE001
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "FAILED"
            JOBS[job_id]["finished_at"] = _now()
            metrics["error"] = _sanitize(str(exc))
            JOBS[job_id]["metrics"] = metrics


def _run_pipeline_job(job_id: str) -> None:
    with JOBS_LOCK:
        JOBS[job_id]["status"] = "RUNNING"

    metrics: dict = {}
    try:
        result = run_pipeline.run_import()
        batch_reports = result.get("batch_reports", [])
        metrics["BATCHES_RUN"] = len(batch_reports)
        metrics["PROCESSED"] = sum(b["processed"] for b in batch_reports)
        metrics["SUCCEEDED"] = sum(b["succeeded"] for b in batch_reports)
        metrics["FAILED"] = sum(b["failed"] for b in batch_reports)
        metrics["CHUNKS_GENERATED"] = sum(b["chunks"] for b in batch_reports)
        metrics["retry_summary"] = result.get("retry_summary")
        metrics["stopped_early"] = result.get("stopped_early", False)

        drive_service = get_drive_service()
        build_master_index()
        try:
            metrics["master_index_drive"] = publish_to_drive(drive_service)
        except Exception as exc:  # noqa: BLE001
            metrics["master_index_drive_error"] = _sanitize(str(exc))

        final_status = "FAILED" if metrics["stopped_early"] and metrics["SUCCEEDED"] == 0 else (
            "PARTIAL" if metrics["FAILED"] > 0 else "COMPLETED"
        )
        with JOBS_LOCK:
            JOBS[job_id]["status"] = final_status
            JOBS[job_id]["finished_at"] = _now()
            JOBS[job_id]["metrics"] = metrics
    except Exception as exc:  # noqa: BLE001
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "FAILED"
            JOBS[job_id]["finished_at"] = _now()
            metrics["error"] = _sanitize(str(exc))
            JOBS[job_id]["metrics"] = metrics


@app.post("/jobs/detect-new")
def detect_new():
    """FASE 3 (discover_videos_api) + tabs (discover_shorts_live_tabs) +
    clasificacion (classify_videos), en ese orden -- el mismo orden que la
    fase original del proyecto. No descarga transcripts ni procesa nada,
    solo detecta y clasifica (Shorts quedan excluidos aca mismo, antes de
    que el pipeline los vea)."""
    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id, "kind": "detect-new", "status": "QUEUED",
            "created_at": _now(), "finished_at": None, "metrics": {},
        }
    thread = threading.Thread(target=_run_detect_job, args=(job_id,), daemon=True)
    thread.start()
    return {"job_id": job_id}


@app.post("/jobs/run-pipeline")
def run_pipeline_job():
    """Corre run_pipeline.run_import() completo (fetch/transcribe/normalize/
    chunk/index/sync-Drive, con retry pass) tal cual -- cero logica
    duplicada. Puede tardar minutos/horas segun cuanto haya pendiente;
    consultar el progreso via GET /jobs/{job_id}."""
    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id, "kind": "run-pipeline", "status": "QUEUED",
            "created_at": _now(), "finished_at": None, "metrics": {},
        }
    thread = threading.Thread(target=_run_pipeline_job, args=(job_id,), daemon=True)
    thread.start()
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job_id not found")
    return job
