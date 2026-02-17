import asyncio
import random
import signal
import sys
from datetime import datetime

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from .config import Config
from .browser import create_browser, create_browser_context
from .coupon_activator import activate_all_coupons, keep_session_alive
from .web.app import create_app
from .web.state import app_state


def setup_logging() -> None:
    Config.ensure_directories()
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        Config.LOGS_DIR / "payback_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
    )


async def run_activation() -> None:
    app_state.is_running = True
    start = datetime.now()
    logger.info("=" * 40)
    logger.info("Starting coupon activation")

    try:
        async with create_browser() as browser:
            async with create_browser_context(browser) as ctx:
                page = await ctx.new_page()
                result = await activate_all_coupons(page)
                duration = (datetime.now() - start).total_seconds()
                logger.info(f"Done: {result.activated} activated ({duration:.1f}s)")
                logger.info("=" * 40)
                app_state.last_activation_time = datetime.now().isoformat()
                app_state.last_activation_result = {
                    "total_found": result.total_found,
                    "activated": result.activated,
                    "failed": result.failed,
                }
    except Exception as e:
        logger.exception(f"Error: {e}")
        app_state.last_activation_time = datetime.now().isoformat()
        app_state.last_activation_result = {"error": "Activation failed"}
    finally:
        app_state.is_running = False


async def run_keepalive() -> None:
    delay = random.randint(0, 1800)
    await asyncio.sleep(delay)

    try:
        async with create_browser() as browser:
            async with create_browser_context(browser) as ctx:
                page = await ctx.new_page()
                await keep_session_alive(page)
                app_state.last_keepalive_time = datetime.now().isoformat()
                app_state.last_keepalive_ok = True
    except Exception as e:
        logger.warning(f"Keepalive error: {e}")
        app_state.last_keepalive_time = datetime.now().isoformat()
        app_state.last_keepalive_ok = False


async def main() -> None:
    setup_logging()
    logger.info("Payback Coupon Activator")
    logger.info(f"Interval: {Config.SCHEDULE_INTERVAL_HOURS}h | Cooldown: {Config.COOLDOWN_SECONDS}s")

    try:
        Config.validate()
    except ValueError as e:
        logger.warning(f"Config: {e} — upload via Web UI")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_activation, IntervalTrigger(hours=Config.SCHEDULE_INTERVAL_HOURS), id="activation", max_instances=1)
    scheduler.add_job(run_keepalive, IntervalTrigger(hours=1), id="keepalive", max_instances=1)
    scheduler.start()

    # Update next run in state
    job = scheduler.get_job("activation")
    if job and job.next_run_time:
        app_state.next_scheduled_run = job.next_run_time.isoformat()

    # Run first activation if cookies exist
    if Config.COOKIES_FILE.exists():
        await run_activation()
    else:
        logger.info("No cookies.json found — waiting for upload via Web UI")

    logger.info(f"Next activation in {Config.SCHEDULE_INTERVAL_HOURS}h, keepalive every 1h")
    logger.info(f"Web UI: http://0.0.0.0:{Config.WEB_PORT}")

    # Start web server (replaces sleep loop)
    app = create_app(scheduler, activation_func=run_activation)
    config = uvicorn.Config(app, host="0.0.0.0", port=Config.WEB_PORT, log_level="warning")
    server = uvicorn.Server(config)

    # Graceful shutdown on SIGTERM (Docker stop)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: loop.create_task(_shutdown(scheduler, server)))

    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Stopped")


async def _shutdown(scheduler: AsyncIOScheduler, server: uvicorn.Server) -> None:
    """Graceful shutdown handler for SIGTERM/SIGINT."""
    logger.info("Shutdown signal received")
    scheduler.shutdown(wait=False)
    server.should_exit = True


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
