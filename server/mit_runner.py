"""Start the existing manga-image-translator API without modifying its tree."""

from __future__ import annotations

import atexit
import os
import pickle
import secrets
import signal
import subprocess
import sys
from pathlib import Path


SUITE_ROOT = Path(__file__).resolve().parents[1]
MIT_ROOT = Path(os.environ.get("MANGALENS_MIT_ROOT", SUITE_ROOT.parent / "manga-image-translator")).resolve()
MODEL_DIR = Path(os.environ.get("MANGALENS_MODEL_DIR", r"F:\AI\MangaLens\models")).resolve()
REQUESTED_FONT_PATH = Path(
    os.environ.get("MANGALENS_THAI_FONT", r"F:\AI\MangaLens\models\fonts\NotoSansThai-Regular.ttf")
).resolve()
WINDOWS_THAI_FONT = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "tahoma.ttf"
FONT_PATH = REQUESTED_FONT_PATH if REQUESTED_FONT_PATH.is_file() else WINDOWS_THAI_FONT
OUTER_PORT = int(os.environ.get("MANGALENS_MIT_PORT", "8766"))
INNER_PORT = OUTER_PORT + 1

if not (MIT_ROOT / "manga_translator").is_dir():
    raise SystemExit(f"manga-image-translator was not found: {MIT_ROOT}")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(MIT_ROOT))

import uvicorn  # noqa: E402
import aiohttp  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from server import main as mit_main  # noqa: E402
from server import instance as mit_instance  # noqa: E402
from server.instance import ExecutorInstance, executor_instances  # noqa: E402


async def fetch_pickled_data(url, image, config, headers=None):
    """Read the loopback worker's documented binary Context response.

    The pinned upstream non-streaming client incorrectly calls response.text()
    and json.loads() even though the worker returns application/octet-stream.
    """
    payload = pickle.dumps({"image": image, "config": config})
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers or {}) as response:
            if response.status != 200:
                raise HTTPException(response.status, detail=await response.text())
            return pickle.loads(await response.read())


mit_instance.fetch_data = fetch_pickled_data


# The upstream ExecutorInstance does not forward X-Nonce when it calls its
# loopback worker.  Disable the worker nonce while keeping it bound to
# 127.0.0.1; the LAN-facing MangaLens gateway is still protected by its token.
nonce = secrets.token_hex(24)
command = [
    sys.executable,
    str(Path(__file__).resolve().parent / "mit_worker.py"),
    "shared",
    "--host",
    "127.0.0.1",
    "--port",
    str(INNER_PORT),
    "--nonce",
    "None",
]
# Upstream reparses options that appear after the subcommand. Its second parser
# otherwise overwrites root options with defaults, silently losing model-dir,
# GPU, and font settings.
command.extend(
    [
        "--model-dir",
        str(MODEL_DIR),
        "--use-gpu",
    ]
)
if FONT_PATH.is_file():
    command.extend(["--font-path", str(FONT_PATH)])

creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
child = subprocess.Popen(command, cwd=MIT_ROOT, creationflags=creationflags)
mit_main.nonce = nonce
executor_instances.register(ExecutorInstance(ip="127.0.0.1", port=INNER_PORT))


@mit_main.app.get("/worker-health")
async def worker_health():
    try:
        timeout = aiohttp.ClientTimeout(total=2.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"http://127.0.0.1:{INNER_PORT}/is_locked") as response:
                if response.status != 200:
                    raise HTTPException(503, "Image worker is not ready")
                return {"ready": True, **(await response.json())}
    except (aiohttp.ClientError, TimeoutError) as exc:
        raise HTTPException(503, "Image worker is not ready") from exc


def stop_child(*_: object) -> None:
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()


atexit.register(stop_child)
signal.signal(signal.SIGINT, stop_child)
signal.signal(signal.SIGTERM, stop_child)

try:
    uvicorn.run(mit_main.app, host="127.0.0.1", port=OUTER_PORT, log_level="info")
finally:
    stop_child()
