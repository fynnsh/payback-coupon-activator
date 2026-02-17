import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Dict, Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from .config import Config


def load_cookies() -> List[Dict[str, Any]]:
    """Load cookies from file and convert to Playwright format."""
    if not Config.COOKIES_FILE.exists():
        logger.warning(f"Cookies file not found: {Config.COOKIES_FILE}")
        return []

    with open(Config.COOKIES_FILE, "r") as f:
        raw_cookies = json.load(f)

    cookies = []
    for c in raw_cookies:
        cookie = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
        }
        if "expirationDate" in c and not c.get("session"):
            cookie["expires"] = c["expirationDate"]
        if "secure" in c:
            cookie["secure"] = c["secure"]
        if "httpOnly" in c:
            cookie["httpOnly"] = c["httpOnly"]
        if c.get("sameSite") == "no_restriction":
            cookie["sameSite"] = "None"
        cookies.append(cookie)

    logger.info(f"Loaded {len(cookies)} cookies")
    return cookies


@asynccontextmanager
async def create_browser() -> AsyncGenerator[Browser, None]:
    """Create browser instance."""
    logger.info(f"Starting browser (headless={Config.HEADLESS})")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=Config.HEADLESS,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        try:
            yield browser
        finally:
            try:
                await browser.close()
            except Exception:
                pass


@asynccontextmanager
async def create_browser_context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create browser context with cookies."""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="de-DE",
    )
    context.set_default_timeout(Config.DEFAULT_TIMEOUT)
    context.set_default_navigation_timeout(Config.NAVIGATION_TIMEOUT)

    cookies = load_cookies()
    if cookies:
        await context.add_cookies(cookies)

    try:
        yield context
    finally:
        await context.close()


async def save_screenshot(page: Page, name: str) -> None:
    """Save screenshot for debugging."""
    Config.ensure_directories()
    path = Config.SCREENSHOTS_DIR / f"{name}.png"
    await page.screenshot(path=str(path), full_page=True)
    logger.debug(f"Screenshot: {path}")
