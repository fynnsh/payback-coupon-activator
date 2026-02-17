import asyncio
import json
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from ..config import Config
from .state import app_state, extract_cookie_metadata

_activation_func = None
_scheduler = None


def create_app(scheduler, activation_func=None) -> FastAPI:
    """Create FastAPI app with routes.

    Args:
        scheduler: APScheduler instance for reading next run times.
        activation_func: Async function to trigger manual activation.
    """
    global _activation_func, _scheduler
    _activation_func = activation_func
    _scheduler = scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if Config.COOKIES_FILE.exists():
            meta = extract_cookie_metadata(Config.COOKIES_FILE)
            app_state.cookie_count = meta["count"]
            app_state.cookie_domains = meta["domains"]
            app_state.cookies_expired = meta["expired_count"] > 0
            app_state.cookies_loaded_at = datetime.now().isoformat()
            logger.info(f"Loaded cookie metadata: {meta['count']} cookies")

        job = _scheduler.get_job("activation")
        if job and job.next_run_time:
            app_state.next_scheduled_run = job.next_run_time.isoformat()
        yield

    app = FastAPI(title="Payback Coupon Activator", docs_url=None, redoc_url=None, lifespan=lifespan)

    static_dir = Path(__file__).parent / "static"

    @app.get("/")
    async def index():
        return FileResponse(static_dir / "index.html", media_type="text/html")

    @app.get("/api/status")
    async def status():
        job = _scheduler.get_job("activation")
        if job and job.next_run_time:
            app_state.next_scheduled_run = job.next_run_time.isoformat()

        return {
            "cookie_count": app_state.cookie_count,
            "cookie_domains": app_state.cookie_domains,
            "cookies_expired": app_state.cookies_expired,
            "cookies_loaded_at": app_state.cookies_loaded_at,
            "last_activation_time": app_state.last_activation_time,
            "last_activation_result": app_state.last_activation_result,
            "next_scheduled_run": app_state.next_scheduled_run,
            "last_keepalive_time": app_state.last_keepalive_time,
            "last_keepalive_ok": app_state.last_keepalive_ok,
            "is_running": app_state.is_running,
        }

    @app.post("/api/cookies")
    async def upload_cookies(file: UploadFile):
        # Read with size limit (1MB)
        content = await file.read(1_048_577)
        if len(content) > 1_048_576:
            raise HTTPException(400, "File too large (max 1MB)")

        # Parse and validate structure
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON")

        if not isinstance(data, list) or len(data) == 0:
            raise HTTPException(400, "Expected non-empty JSON array")

        for cookie in data:
            if not isinstance(cookie, dict):
                raise HTTPException(400, "Invalid cookie format")
            if not all(k in cookie for k in ("name", "value", "domain")):
                raise HTTPException(400, "Each cookie must have name, value, and domain")

        # Atomic write: temp file → os.replace (with cleanup on failure)
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=Config.COOKIES_FILE.parent,
                suffix=".tmp",
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp_path, Config.COOKIES_FILE)
            tmp_path = None  # Successfully replaced, no cleanup needed
        except OSError as e:
            logger.error(f"Failed to save cookies: {e}")
            raise HTTPException(500, "Failed to save file")
        finally:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        # Update state with metadata only
        meta = extract_cookie_metadata(Config.COOKIES_FILE)
        app_state.cookie_count = meta["count"]
        app_state.cookie_domains = meta["domains"]
        app_state.cookies_expired = meta["expired_count"] > 0
        app_state.cookies_loaded_at = datetime.now().isoformat()

        logger.info(f"Received {meta['count']} cookies via upload")

        return {
            "ok": True,
            "cookie_count": meta["count"],
            "domains": meta["domains"],
            "expired": meta["expired_count"] > 0,
        }

    @app.post("/api/trigger")
    async def trigger():
        if app_state.is_running:
            raise HTTPException(409, "Activation already running")
        if _activation_func is None:
            raise HTTPException(500, "Activation not configured")
        if app_state.cookie_count == 0:
            raise HTTPException(400, "No cookies loaded")

        # Set flag BEFORE scheduling to prevent race condition
        app_state.is_running = True
        asyncio.create_task(_activation_func(), name="manual-activation")
        return {"ok": True, "message": "Activation started"}

    return app
