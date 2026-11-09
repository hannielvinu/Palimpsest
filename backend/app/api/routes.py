from functools import lru_cache
import json
from pathlib import Path
import subprocess
import sys
from threading import BoundedSemaphore
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile

from ..core.audit import append, now, verify
from ..core.config import DEMO_ONLY, MAX_BYTES, MAX_FILES, MAX_PAGES, ROOT
from ..core.hashing import sha256
from ..core.storage import db
from ..pipeline.dossier import dossier
from ..pipeline.ingest import inspect_upload

router = APIRouter(prefix="/api")
ANALYSES = BoundedSemaphore(2)
RENDERS = BoundedSemaphore(3)
SAMPLES = {"meena": "Meena / routine review", "ravi": "Ravi / payroll review",
           "injection": "Isha / embedded instruction", "degraded": "Unreadable source"}
CAPABILITIES = [
    ["Implemented", "Upload hashes, evidence regions, reviewer decisions, dossier and audit verification"],
    ["Implemented", "Retained PDF revision recovery and side-by-side raster views"],
    ["Partial", "Label extraction, typography, signature labels, hidden text, ELA and ORB region heuristics"],
    ["Planned", "Blind benchmark, calibrated thresholds and multilingual templates"],
    ["Unsupported", "Recovery after history is flattened, issuer verification and automatic verdicts"],
]


class NewCase(BaseModel):
    title: str = Field(default="Untitled investigation", min_length=1, max_length=100)


class Decision(BaseModel):
    action: str
    reason: str = Field(default="", max_length=1000)


def case_row(conn, case_id):
    row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Case not found.")
    return row


def snapshot(row):
    return {k: row[k] for k in ("id", "title", "state", "created")} | {
        key: json.loads(row[key]) if row[key] else None for key in ("progress", "decision")}


def insert_case(conn, title):
    case_id = uuid4().hex
    conn.execute("INSERT INTO cases(id,title,state,created) VALUES(?,?,?,?)", (case_id, title, "draft", now()))
    append(conn, case_id, "case_created", {"title": title})
    return case_id


def insert_upload(conn, case_id, name, mime, raw):
    document = {"id": uuid4().hex, "name": name, "mime": mime, "sha256": sha256(raw)}
    conn.execute("INSERT INTO documents(id,case_id,name,mime,sha256,original) VALUES(?,?,?,?,?,?)",
                 (document["id"], case_id, name, mime, document["sha256"], raw))
    append(conn, case_id, "upload", document)
    return document


def run_worker(*args, timeout):
    return subprocess.run([sys.executable, "-m", "backend.app.api.worker", *args],
                          cwd=ROOT, capture_output=True, timeout=timeout, check=False)


def background(case_id):
    try:
        job = run_worker(case_id, timeout=100)
        if job.returncode:
            print(job.stderr.decode(errors="replace")[-4000:], file=sys.stderr)
            raise RuntimeError("worker failed")
    except (RuntimeError, OSError, subprocess.TimeoutExpired):
        with db(write=True) as conn:
            conn.execute("UPDATE cases SET state='failed' WHERE id=?", (case_id,))
            append(conn, case_id, "analysis_failed", {"reason": "Processing failed or reached the time limit."})
    finally:
        ANALYSES.release()


def queue(conn, case_id):
    conn.execute("UPDATE cases SET state='processing',progress='[]',result=NULL WHERE id=?", (case_id,))
    append(conn, case_id, "analysis_queued", {})


@router.post("/cases", status_code=201)
def create(body: NewCase):
    if DEMO_ONLY:
        raise HTTPException(403, "This public demo accepts only bundled synthetic records.")
    with db(write=True) as conn:
        return {"id": insert_case(conn, body.title.strip() or "Untitled investigation")}


@router.post("/cases/{case_id}/documents", status_code=201)
async def upload(case_id: str, request: Request):
    if DEMO_ONLY:
        raise HTTPException(403, "Uploads are disabled in public demo mode.")
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        length = 0
    if not 0 < length <= MAX_BYTES * MAX_FILES + 65536:
        raise HTTPException(413, "The multipart request exceeds the upload limit or needs a content length.")
    uploads = []
    try:
        async with request.form(max_files=MAX_FILES, max_fields=0) as form:
            files = form.getlist("files")
            if not files or any(not isinstance(file, UploadFile) for file in files):
                raise ValueError("Send one to eight files using the files field.")
            for file in files:
                raw = await file.read(MAX_BYTES + 1)
                name, mime = inspect_upload(file.filename or "document", raw)
                uploads.append((name, mime, raw))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    with db(write=True) as conn:
        row = case_row(conn, case_id)
        existing = conn.execute("SELECT count(*) FROM documents WHERE case_id=?", (case_id,)).fetchone()[0]
        if row["state"] != "draft" or existing + len(uploads) > MAX_FILES:
            raise HTTPException(409, "A draft case may contain at most eight documents.")
        return {"documents": [insert_upload(conn, case_id, *file) for file in uploads]}


@router.post("/cases/{case_id}/analyze", status_code=202)
def start(case_id: str, tasks: BackgroundTasks):
    if not ANALYSES.acquire(blocking=False):
        raise HTTPException(429, "The desk is busy. Try again shortly.")
    try:
        with db(write=True) as conn:
            row = case_row(conn, case_id)
            if row["state"] not in {"draft", "failed"}:
                raise HTTPException(409, "This case is already queued or complete.")
            if not conn.execute("SELECT 1 FROM documents WHERE case_id=?", (case_id,)).fetchone():
                raise HTTPException(422, "Add at least one document.")
            queue(conn, case_id)
    except Exception:
        ANALYSES.release()
        raise
    tasks.add_task(background, case_id)
    return {"id": case_id}


@router.post("/samples/{name}/load", status_code=202)
def sample(name: str, tasks: BackgroundTasks):
    if name not in SAMPLES:
        raise HTTPException(404, "Unknown sample.")
    files = sample_inputs(name)
    if not files:
        raise HTTPException(503, "Sample fixtures are unavailable. Run scripts/make_samples.py.")
    if not ANALYSES.acquire(blocking=False):
        raise HTTPException(429, "The desk is busy. Try again shortly.")
    try:
        with db(write=True) as conn:
            case_id = insert_case(conn, SAMPLES[name])
            for file_name, mime, raw in files:
                insert_upload(conn, case_id, file_name, mime, raw)
            queue(conn, case_id)
    except Exception:
        ANALYSES.release()
        raise
    tasks.add_task(background, case_id)
    return {"id": case_id}


@lru_cache(maxsize=4)
def sample_inputs(name):
    records = []
    for file in sorted((ROOT / "data" / "samples" / f"{name}_case").iterdir()):
        if file.is_file() and file.suffix.lower() in {".pdf", ".png", ".jpg"}:
            raw = file.read_bytes()
            records.append((*inspect_upload(file.name, raw), raw))
    return records


@router.get("/cases/{case_id}/status")
def status(case_id: str):
    with db() as conn:
        return snapshot(case_row(conn, case_id))


def result_for(conn, case_id):
    row = case_row(conn, case_id)
    if row["state"] != "ready" or not row["result"]:
        raise HTTPException(409, "Investigation is not ready.")
    return row, json.loads(row["result"])


@router.get("/cases/{case_id}/findings")
def findings(case_id: str):
    with db() as conn:
        row, result = result_for(conn, case_id)
        return snapshot(row) | result


@router.get("/cases/{case_id}/crossmatrix")
def crossmatrix(case_id: str):
    with db() as conn:
        return result_for(conn, case_id)[1]["matrix"]


@router.get("/documents/{document_id}/render")
def render(document_id: str, page: int = 1, revision: int = 0):
    if not 1 <= page <= MAX_PAGES or not 0 <= revision <= 4:
        raise HTTPException(404, "Page or revision unavailable.")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM documents WHERE id=?", (document_id,)).fetchone():
            raise HTTPException(404, "Document not found.")
    if not RENDERS.acquire(blocking=False):
        raise HTTPException(429, "The page renderer is busy.")
    try:
        job = run_worker("render", document_id, str(page), str(revision), timeout=14)
        if job.returncode or not job.stdout.startswith(b"\x89PNG"):
            raise HTTPException(422, "Cannot determine: this page could not be rendered.")
        return Response(job.stdout, media_type="image/png", headers={"Cache-Control": "no-store"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(422, "Cannot determine: the page renderer reached its limit.") from exc
    finally:
        RENDERS.release()


@router.post("/cases/{case_id}/decision")
def decide(case_id: str, body: Decision):
    reason = body.reason.strip()
    if body.action not in {"Clear", "Request more documents", "Escalate"} or (body.action == "Escalate" and not reason):
        raise HTTPException(422, "Choose a reviewer action and give a reason for escalation.")
    decision = {"action": body.action, "reason": reason, "timestamp": now()}
    with db(write=True) as conn:
        result_for(conn, case_id)
        conn.execute("UPDATE cases SET decision=? WHERE id=?", (json.dumps(decision), case_id))
        head = append(conn, case_id, "reviewer_decision", decision)
    return decision | {"audit_head": head}


def chain_rows(conn, case_id):
    return conn.execute("SELECT seq,previous,payload,hash FROM audit WHERE case_id=? ORDER BY seq", (case_id,)).fetchall()


@router.get("/audit/verify")
def audit(case_id: str):
    with db() as conn:
        case_row(conn, case_id)
        rows = chain_rows(conn, case_id)
        return verify(rows) | {"entries": [dict(row) | {"event": json.loads(row["payload"])} for row in rows]}


@router.get("/cases/{case_id}/dossier.pdf")
def download(case_id: str):
    with db() as conn:
        row, result = result_for(conn, case_id)
        chain = verify(chain_rows(conn, case_id))
    return Response(dossier(snapshot(row), result, chain), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="palimpsest-dossier.pdf"', "Cache-Control": "no-store"})


@router.delete("/cases/{case_id}", status_code=204)
def purge(case_id: str):
    with db(write=True) as conn:
        if case_row(conn, case_id)["state"] == "processing":
            raise HTTPException(409, "Wait for analysis before purging.")
        conn.execute("DELETE FROM cases WHERE id=?", (case_id,))
    return Response(status_code=204)


@router.get("/capabilities")
def capabilities():
    return {"matrix": CAPABILITIES, "demo_only": DEMO_ONLY,
            "standards": "ISO/IEC 27037, 27041, 27042 · NIST SP 800-86 · OWASP ML Top 10 — referenced for guidance, no formal compliance claimed."}


@router.get("/benchmark")
def benchmark():
    folder = ROOT / "data" / "benchmark" / "results"
    return {name: json.loads((folder / f"{name}.json").read_text(encoding="utf8")) if (folder / f"{name}.json").is_file() else None
            for name in ("benchmark", "robustness")}
