"""Paper2Reality API.

Routes (documentation/Architecture.md section 4):
    GET  /api/health
    GET  /api/config
    POST /api/jobs                     multipart upload -> 202 + job id
    GET  /api/jobs/{job_id}            status/progress or full PaperAnalysis
    GET  /api/jobs/{job_id}/report     markdown executive report
    POST /api/jobs/{job_id}/chat       grounded Q&A over the paper (needs Gemini)

Uploads are written to the project-local data directory (or the Docker volume),
never to a system path.  The only heavy work happens in the background job thread.
"""

from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import __version__
from api.jobs import runner
from api.pipeline import PIPELINE_VERSION, chat, config, llm, models

logger = logging.getLogger("paper2reality.api")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
_STATUS_CODES = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    409: "NOT_READY",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_FILE",
    422: "VALIDATION_ERROR",
}


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)


def _error(code: str, message: str) -> dict:
    return {"status": "error", "error": {"code": code, "message": message}}


def _safe_filename(filename: str | None) -> str:
    raw = (filename or "").replace("\\", "/").split("/")[-1].strip()
    return raw or "upload"


def _safe_download_name(title: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "", title or "").strip().replace(" ", "-")
    cleaned = re.sub(r"-{2,}", "-", cleaned)[:70].strip("-") or "paper"
    return f"{cleaned}-report.md"


@asynccontextmanager
async def lifespan(_: FastAPI):
    config.ensure_dirs()
    logger.info(
        "Paper2Reality API ready | data=%s | gemini=%s | low_ram=%s",
        config.DATA_DIR,
        bool(config.GEMINI_API_KEY),
        config.LOW_RAM,
    )
    yield


app = FastAPI(
    title="Paper2Reality API",
    version=__version__,
    description="Research-to-commercialization intelligence: evidence-cited paper analysis.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or _STATUS_CODES.get(exc.status_code, "HTTP_ERROR"))
        message = str(detail.get("message") or "Request failed.")
    else:
        code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
        message = str(detail or "Request failed.")
    return JSONResponse(status_code=exc.status_code, content=_error(code, message))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error(
            "VALIDATION_ERROR",
            f"The request was malformed ({len(exc.errors())} validation error(s)).",
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error("INTERNAL_ERROR", "An unexpected server error occurred."),
    )


@app.get("/")
async def root():
    return {
        "name": "Paper2Reality",
        "version": __version__,
        "health": "/api/health",
        "docs": "/docs",
        "pipeline_version": PIPELINE_VERSION,
    }


@app.get("/api/health")
async def health():
    status = models.model_status()
    return {
        "status": "ok",
        "models_loaded": models.loaded_models(),
        "dependencies": status["dependencies"],
        "mode": config.public_config(),
        "pipeline_version": PIPELINE_VERSION,
    }


@app.get("/api/config")
async def get_config():
    status = models.model_status()
    return {
        **config.public_config(),
        "models_loaded": models.loaded_models(),
        "model_errors": status["errors"],
        "limits": {
            "max_upload_mb": config.MAX_UPLOAD_MB,
            "max_pages": config.MAX_PAGES,
            "max_claims": config.MAX_CLAIMS,
        },
        "pipeline_version": PIPELINE_VERSION,
    }


@app.post("/api/jobs", status_code=202)
async def create_job(file: UploadFile = File(...)):
    name = _safe_filename(file.filename)
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "UNSUPPORTED_FILE",
                "message": "Upload a PDF, .txt or .md file.",
            },
        )

    job_id = uuid4().hex[:12]
    config.ensure_dirs()
    destination = config.UPLOAD_DIR / f"{job_id}{suffix}"
    size = 0
    try:
        with destination.open("wb") as handle:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > config.MAX_UPLOAD_BYTES:
                    handle.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "code": "FILE_TOO_LARGE",
                            "message": f"Maximum upload size is {config.MAX_UPLOAD_MB} MB.",
                        },
                    )
                handle.write(chunk)
    except HTTPException:
        raise
    except OSError as exc:
        destination.unlink(missing_ok=True)
        logger.exception("Could not store upload")
        raise HTTPException(
            status_code=500,
            detail={"code": "UPLOAD_FAILED", "message": "The upload could not be stored."},
        ) from exc
    finally:
        await file.close()

    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail={"code": "EMPTY_FILE", "message": "The uploaded file is empty."},
        )

    job = runner.create_job(destination, name, job_id=job_id)
    return JSONResponse(
        status_code=202,
        content={"job_id": job["job_id"], "status": job["status"], "filename": name},
    )


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "That analysis job does not exist."},
        )
    return job


@app.get("/api/jobs/{job_id}/report")
async def job_report(job_id: str, format: str = "md"):
    if format.lower() not in {"md", "markdown"}:
        raise HTTPException(
            status_code=400,
            detail={"code": "UNSUPPORTED_FORMAT", "message": "Only markdown reports are available."},
        )
    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "That analysis job does not exist."},
        )
    if job["status"] == "error":
        message = (job.get("error") or {}).get("message", "The analysis failed.")
        raise HTTPException(
            status_code=409,
            detail={"code": "JOB_FAILED", "message": message},
        )
    if job["status"] != "done":
        raise HTTPException(
            status_code=409,
            detail={"code": "JOB_NOT_READY", "message": "The analysis is still running."},
        )
    markdown = runner.get_report(job_id)
    if not markdown:
        raise HTTPException(
            status_code=409,
            detail={"code": "REPORT_NOT_READY", "message": "The report is not available yet."},
        )
    title = (job.get("doc") or {}).get("title", "paper")
    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_download_name(title)}"'
        },
    )


@app.post("/api/jobs/{job_id}/chat")
def job_chat(job_id: str, body: ChatRequest):
    """Answer a question about the uploaded paper using Gemini over retrieved passages.

    Declared ``def`` (not ``async def``) so the blocking Gemini call runs in FastAPI's
    thread pool and never stalls the event loop.
    """
    if not llm.enabled():
        raise HTTPException(
            status_code=503,
            detail={"code": "CHAT_DISABLED", "message": chat.NO_KEY_MESSAGE},
        )

    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "That analysis job does not exist."},
        )
    if job["status"] == "error":
        message = (job.get("error") or {}).get("message", "The analysis failed.")
        raise HTTPException(status_code=409, detail={"code": "JOB_FAILED", "message": message})
    if job["status"] != "done":
        raise HTTPException(
            status_code=409,
            detail={"code": "JOB_NOT_READY", "message": "The analysis is still running."},
        )

    # The upload may already be deleted by the retention policy; the stored analysis
    # (the pipeline findings) can still ground the answer.
    source = runner.get_source(job_id)
    path, filename = source if source else (None, job.get("filename") or "paper")
    try:
        return chat.answer(
            job_id,
            path,
            filename,
            body.question,
            [turn.model_dump() for turn in body.history],
            analysis=job,
        )
    except chat.ChatError as exc:
        raise HTTPException(
            status_code=exc.status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
