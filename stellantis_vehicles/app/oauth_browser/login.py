"""Headless-browser login to obtain the Stellantis OAuth authorization code.

Clean-room implementation (no code taken from the unlicensed worker-v2 repo).
Flow: open the OAuth authorize URL, fill the Gigya login form, confirm the
consent form, then catch the redirect to the app scheme (mym*://...?code=...)
which the browser cannot follow - it shows up as a failed request.

Chromium is launched per call and closed afterwards to keep the add-on's
memory footprint low on small hosts.
"""
import asyncio
import logging
from urllib.parse import parse_qs, urlsplit

_LOGGER = logging.getLogger(__name__)

# Selectors of the Stellantis/Gigya login page. Kept in one place because
# they are the part most likely to break on upstream UI changes.
SEL_EMAIL = "#gigya-login-form input[name='username']"
SEL_PASSWORD = "#gigya-login-form input[name='password']"
SEL_SUBMIT = "#gigya-login-form input[type='submit']"
SEL_AUTHORIZE = "#cvs_from input[type='submit']"

APP_SCHEME_PREFIX = "mym"

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--no-first-run",
    "--no-zygote",
]


class OauthBrowserError(RuntimeError):
    pass


def _code_from_url(url: str) -> str | None:
    if not url.startswith(APP_SCHEME_PREFIX):
        return None
    query = urlsplit(url).query
    return parse_qs(query).get("code", [None])[0]


async def fetch_oauth_code(oauth_url: str, email: str, password: str,
                           timeout_s: float = 60.0) -> str:
    """Return the OAuth authorization code for the given credentials."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as err:  # pragma: no cover
        raise OauthBrowserError("playwright is not installed") from err

    code_future: asyncio.Future[str] = asyncio.get_running_loop().create_future()

    def _on_request_failed(request) -> None:
        code = _code_from_url(request.url)
        if code and not code_future.done():
            code_future.set_result(code)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)
        try:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            page = await context.new_page()
            page.on("requestfailed", _on_request_failed)

            ms = int(timeout_s * 1000)
            _LOGGER.debug("Opening OAuth page")
            await page.goto(oauth_url, wait_until="domcontentloaded", timeout=ms)
            await page.wait_for_selector(SEL_EMAIL, timeout=ms)
            await page.fill(SEL_EMAIL, email)
            await page.fill(SEL_PASSWORD, password)
            await page.click(SEL_SUBMIT)
            _LOGGER.debug("Credentials submitted, waiting for consent form")
            await page.wait_for_selector(SEL_AUTHORIZE, timeout=ms)
            await page.click(SEL_AUTHORIZE)
            _LOGGER.debug("Consent submitted, waiting for app redirect")
            try:
                return await asyncio.wait_for(code_future, timeout=timeout_s)
            except asyncio.TimeoutError as err:
                raise OauthBrowserError("No authorization code captured (timeout)") from err
        finally:
            await browser.close()
