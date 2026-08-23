"""MangaLens LAN HQ gateway.

The gateway keeps submitted images and translated results in memory only.  The
heavy image pipeline remains on loopback, while this process exposes a small,
versioned and token-protected API to the phone.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError


APP_VERSION = "1.0.0"
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 80_000_000
JOB_TTL_SECONDS = 30 * 60
TERMINAL_STATES = {"completed", "failed", "cancelled"}


def _env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser().resolve()


@dataclass
class Settings:
    token_file: Path = field(
        default_factory=lambda: _env_path(
            "MANGALENS_TOKEN_FILE", r"F:\AI\MangaLens\server\pairing-token.txt"
        )
    )
    mit_url: str = field(
        default_factory=lambda: os.environ.get("MANGALENS_MIT_URL", "http://127.0.0.1:8766").rstrip("/")
    )
    ollama_url: str = field(
        default_factory=lambda: os.environ.get("MANGALENS_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    )
    model: str = field(
        default_factory=lambda: os.environ.get("MANGALENS_TRANSLATION_MODEL", "translategemma:4b")
    )
    request_timeout_seconds: float = 15 * 60

    def token(self) -> str:
        value = os.environ.get("MANGALENS_PAIRING_TOKEN", "").strip()
        if value:
            return value
        try:
            return self.token_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""


settings = Settings()
app = FastAPI(title="MangaLens HQ API", version=APP_VERSION)


class PageOptions(BaseModel):
    source_language: Literal["auto", "ja", "ko", "zh"] = "auto"
    target_language: Literal["THA"] = "THA"
    quality_profile: Literal["balanced", "hq"] = "hq"
    reading_order: Literal["rtl", "ltr", "vertical"] = "rtl"
    glossary_version: str = Field(default="default", max_length=128)
    selected_sfx: list[str] = Field(default_factory=list, max_length=100)


@dataclass
class Job:
    id: str
    page_hash: str
    options: PageOptions
    state: str = "queued"
    stage: str = "queued"
    progress: int = 0
    submitted_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: bytes | None = None
    error: str | None = None
    timings_ms: dict[str, int] = field(default_factory=dict)
    task: asyncio.Task[None] | None = None
    event: asyncio.Event = field(default_factory=asyncio.Event)

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state,
            "stage": self.stage,
            "progress": self.progress,
            "page_hash": self.page_hash,
            "options": self.options.model_dump(),
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "timings_ms": self.timings_ms,
            "error": self.error,
            "result_url": f"/v1/jobs/{self.id}/result" if self.state == "completed" else None,
        }


jobs: dict[str, Job] = {}


def _source_code(text: str) -> tuple[str, str]:
    if any("\uac00" <= char <= "\ud7a3" for char in text):
        return "Korean", "ko"
    if any(("\u3040" <= char <= "\u30ff") for char in text):
        return "Japanese", "ja"
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        return "Chinese", "zh"
    return "Japanese", "ja"


def adapt_translategemma_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert generic OpenAI chat prompts to Ollama's documented TG prompt."""
    result = dict(payload)
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return result
    user_parts: list[str] = []
    requirements: list[str] = []
    for message in messages:
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            return result
        if message.get("role") == "user":
            user_parts.append(message["content"])
        elif message.get("role") == "system":
            requirements.append(message["content"])
    source_text = "\n".join(user_parts).strip()
    if not source_text:
        return result
    source_name, source_code = _source_code(source_text)
    manga_hint = ""
    if source_code == "ko":
        explicit_keep_objects = ("약속", "규칙", "법", "비밀", "시간", "말", "질서")
        ambiguous_protect = (
            ("지킬 거야" in source_text or "지킬거야" in source_text)
            and not any(term in source_text for term in explicit_keep_objects)
        )
        terminology = (
            " Mandatory terminology for this line: translate 지킬 as ปกป้อง (protect), "
            "never as ทำตาม (comply)."
            if ambiguous_protect
            else ""
        )
        manga_hint = (
            " Korean manga note: preserve omitted subjects and objects instead of inventing pronouns. "
            "Mandatory ambiguity rule: when 지키다/지킬 거야 has no explicitly stated rule, promise, "
            "appointment, or secret as its object, prefer ปกป้อง (protect) and never ทำตาม (comply). "
            f"For an explicitly stated rule or promise, use รักษา instead.{terminology}"
        )
    extra = ""
    if requirements:
        extra = " Follow these additional manga and output-format requirements: " + " ".join(requirements)
    prompt = (
        f"You are a professional {source_name} ({source_code}) to Thai (th) translator. "
        f"Your goal is to accurately convey the meaning and nuances of the original {source_name} text "
        f"while adhering to Thai grammar, vocabulary, and cultural sensitivities.{manga_hint}{extra}\n"
        f"Produce only the Thai translation, without any additional explanations or commentary. "
        f"Please translate the following {source_name} text into Thai:\n\n\n{source_text}"
    )
    result["messages"] = [{"role": "user", "content": prompt}]
    result["temperature"] = 0
    return result


def _provided_bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    scheme, _, value = authorization.partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


async def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = settings.token()
    provided = _provided_bearer(authorization)
    if not expected:
        raise HTTPException(503, "Pairing token is not configured")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(401, "Invalid pairing token", headers={"WWW-Authenticate": "Bearer"})


def parse_page_options(raw: str) -> PageOptions:
    try:
        payload = json.loads(raw or "{}")
        if not isinstance(payload, dict):
            raise ValueError("config must be a JSON object")
        return PageOptions.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(422, f"Invalid page config: {exc}") from exc


def validate_image(data: bytes) -> tuple[str, str]:
    if not data:
        raise HTTPException(422, "Empty image")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, f"Image exceeds {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            image_format = (image.format or "PNG").lower()
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(422, "Image dimensions are not allowed")
            image.verify()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "Unsupported or damaged image") from exc
    return hashlib.sha256(data).hexdigest(), image_format


def build_mit_config(options: PageOptions) -> dict[str, Any]:
    ocr = "mocr" if options.source_language == "ja" else "48px_ctc"
    detection_size = 2048 if options.quality_profile == "hq" else 1536
    inpainting_size = 1536 if options.quality_profile == "hq" else 1024
    return {
        "render": {
            "renderer": "manga2eng_pillow",
            "alignment": "center",
            "direction": "horizontal",
            "rtl": options.reading_order == "rtl",
            "no_hyphenation": True,
        },
        "translator": {
            "translator": "custom_openai",
            "target_lang": "THA",
            "no_text_lang_skip": True,
            "enable_post_translation_check": True,
            "post_check_max_retry_attempts": 2,
        },
        "detector": {
            "detector": "default",
            "detection_size": detection_size,
            "text_threshold": 0.45,
            "box_threshold": 0.65,
            "unclip_ratio": 2.3,
        },
        "ocr": {
            "ocr": ocr,
            "use_mocr_merge": options.source_language == "ja",
            "min_text_length": 1,
        },
        "inpainter": {
            "inpainter": "lama_large",
            "inpainting_size": inpainting_size,
            "inpainting_precision": "fp16",
        },
        "force_simple_sort": options.reading_order == "vertical",
        "kernel_size": 5,
        "mask_dilation_offset": 24,
    }


def _notify(job: Job, *, stage: str, progress: int) -> None:
    job.stage = stage
    job.progress = progress
    job.event.set()


async def _run_job(job: Job, image_data: bytes, filename: str, content_type: str) -> None:
    started = time.perf_counter()
    job.state = "running"
    job.started_at = time.time()
    _notify(job, stage="hq_pipeline", progress=10)
    try:
        timeout = httpx.Timeout(settings.request_timeout_seconds, connect=20.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.mit_url}/translate/with-form/image",
                files={"image": (filename, image_data, content_type)},
                data={"config": json.dumps(build_mit_config(job.options))},
            )
        if response.status_code != 200:
            detail = response.text[:800]
            raise RuntimeError(f"HQ image engine returned {response.status_code}: {detail}")
        if not response.content.startswith(b"\x89PNG"):
            raise RuntimeError("HQ image engine did not return a PNG")
        job.result = response.content
        job.state = "completed"
        job.timings_ms["hq_total"] = int((time.perf_counter() - started) * 1000)
        job.finished_at = time.time()
        _notify(job, stage="completed", progress=100)
    except asyncio.CancelledError:
        job.state = "cancelled"
        job.finished_at = time.time()
        _notify(job, stage="cancelled", progress=100)
        raise
    except Exception as exc:  # The client receives a sanitized, bounded message.
        job.error = str(exc)[:1000]
        job.state = "failed"
        job.finished_at = time.time()
        _notify(job, stage="failed", progress=100)
    finally:
        image_data = b""


def _prune_jobs() -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    expired = [job_id for job_id, job in jobs.items() if job.finished_at and job.finished_at < cutoff]
    for job_id in expired:
        jobs.pop(job_id, None)


def _get_job(job_id: str) -> Job:
    _prune_jobs()
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


async def _probe(client: httpx.AsyncClient, url: str, method: str = "GET") -> dict[str, Any]:
    try:
        response = await client.request(method, url)
        return {"ok": response.is_success, "status": response.status_code}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": type(exc).__name__}


@app.get("/v1/health")
async def health() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=2.5) as client:
        ollama, image_engine = await asyncio.gather(
            _probe(client, f"{settings.ollama_url}/api/tags"),
            _probe(client, f"{settings.mit_url}/worker-health"),
        )
    return {
        "service": "mangalens-hq",
        "version": APP_VERSION,
        "ready": bool(ollama.get("ok") and image_engine.get("ok") and settings.token()),
        "model": settings.model,
        "ollama": ollama,
        "image_engine": image_engine,
        "image_persistence": "memory-only",
    }


@app.get("/v1/models", dependencies=[Depends(require_token)])
async def models() -> dict[str, Any]:
    return {"object": "list", "data": [{"id": settings.model, "object": "model", "owned_by": "local"}]}


@app.post("/v1/chat/completions", dependencies=[Depends(require_token)])
async def chat_completions(payload: dict[str, Any]) -> Response:
    payload = adapt_translategemma_payload(payload)
    payload["model"] = settings.model
    stream = bool(payload.get("stream", False))
    client = httpx.AsyncClient(timeout=httpx.Timeout(settings.request_timeout_seconds, connect=10.0))
    request = client.build_request("POST", f"{settings.ollama_url}/v1/chat/completions", json=payload)
    response = await client.send(request, stream=stream)
    if not stream:
        content = await response.aread()
        await response.aclose()
        await client.aclose()
        return Response(content, status_code=response.status_code, media_type=response.headers.get("content-type"))

    async def body():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(body(), status_code=response.status_code, media_type=response.headers.get("content-type"))


@app.post("/v1/pages", status_code=202, dependencies=[Depends(require_token)])
async def submit_page(image: UploadFile = File(...), config: str = Form("{}")) -> dict[str, Any]:
    options = parse_page_options(config)
    data = await image.read(MAX_IMAGE_BYTES + 1)
    page_hash, image_format = validate_image(data)
    job_id = uuid.uuid4().hex
    job = Job(id=job_id, page_hash=page_hash, options=options)
    jobs[job_id] = job
    filename = image.filename or f"page.{image_format}"
    content_type = image.content_type or f"image/{image_format}"
    job.task = asyncio.create_task(_run_job(job, data, filename, content_type))
    return {"id": job_id, "state": job.state, "status_url": f"/v1/jobs/{job_id}"}


@app.get("/v1/jobs/{job_id}", dependencies=[Depends(require_token)])
async def get_job(job_id: str) -> dict[str, Any]:
    return _get_job(job_id).snapshot()


@app.delete("/v1/jobs/{job_id}", dependencies=[Depends(require_token)])
async def cancel_job(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if job.state not in TERMINAL_STATES and job.task:
        job.task.cancel()
        try:
            await job.task
        except asyncio.CancelledError:
            pass
    return job.snapshot()


@app.get("/v1/jobs/{job_id}/result", dependencies=[Depends(require_token)])
async def get_result(job_id: str) -> Response:
    job = _get_job(job_id)
    if job.state == "failed":
        raise HTTPException(409, job.error or "Job failed")
    if job.state != "completed" or job.result is None:
        raise HTTPException(425, "Result is not ready")
    return Response(job.result, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.websocket("/v1/jobs/{job_id}/events")
async def job_events(websocket: WebSocket, job_id: str) -> None:
    provided = _provided_bearer(websocket.headers.get("authorization")) or websocket.query_params.get("token", "")
    expected = settings.token()
    if not expected or not hmac.compare_digest(provided, expected):
        await websocket.close(code=4401)
        return
    job = jobs.get(job_id)
    if job is None:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(job.snapshot())
            if job.state in TERMINAL_STATES:
                break
            job.event.clear()
            try:
                await asyncio.wait_for(job.event.wait(), timeout=10.0)
            except TimeoutError:
                pass
    except WebSocketDisconnect:
        return
