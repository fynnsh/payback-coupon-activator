import asyncio
from dataclasses import dataclass

from playwright.async_api import Page
from loguru import logger

from .config import Config


@dataclass
class ActivationResult:
    total_found: int = 0
    activated: int = 0
    failed: int = 0


async def _dismiss_cookie_banner(page: Page) -> None:
    """Dismiss cookie consent banner if visible."""
    try:
        btn = page.locator('button:has-text("Alle Cookies akzeptieren")').first
        if await btn.is_visible(timeout=2000):
            await btn.click()
            await page.wait_for_timeout(1000)
    except Exception:
        pass


async def activate_all_coupons(page: Page) -> ActivationResult:
    """Activate all available coupons."""
    result = ActivationResult()

    await page.goto(Config.COUPONS_URL, wait_until="load")
    await page.wait_for_load_state("networkidle")
    await _dismiss_cookie_banner(page)

    # Wait for content to render
    await page.wait_for_timeout(3000)

    # Find buttons
    selector = 'button.coupon__activate-button.not-activated'
    result.total_found = await page.locator(selector).count()
    logger.info(f"Found {result.total_found} coupons")

    # Activate
    batch_count = 0
    while True:
        btn = page.locator(selector).first
        try:
            if not await btn.is_visible(timeout=500):
                break
            await btn.click()
            result.activated += 1
            batch_count += 1
            if result.activated % 25 == 0:
                logger.info(f"Progress: {result.activated}/{result.total_found}")

            # Rate limit: pause after batch size reached
            if batch_count >= Config.RATE_LIMIT_BATCH_SIZE:
                pause_seconds = Config.RATE_LIMIT_PAUSE_HOURS * 3600
                logger.info(f"Rate limit reached ({batch_count} coupons). Pausing for {Config.RATE_LIMIT_PAUSE_HOURS}h...")
                await asyncio.sleep(pause_seconds)
                batch_count = 0
                logger.info("Resuming — reloading page...")
                await page.goto(Config.COUPONS_URL, wait_until="load")
                await page.wait_for_load_state("networkidle")
                await _dismiss_cookie_banner(page)
                await page.wait_for_timeout(3000)
            else:
                await page.wait_for_timeout(Config.COOLDOWN_SECONDS * 1000)
        except Exception as e:
            result.failed += 1
            logger.warning(f"Coupon activation failed: {e}")
            break

    logger.info(f"Result: {result.activated} activated, {result.failed} failed (of {result.total_found} found)")
    return result


async def keep_session_alive(page: Page) -> None:
    """Visit page briefly to keep cookies active."""
    try:
        await page.goto(Config.COUPONS_URL, wait_until="load")
        await page.wait_for_timeout(2000)
        logger.info("Session keepalive done")
    except Exception as e:
        logger.warning(f"Keepalive failed: {e}")
