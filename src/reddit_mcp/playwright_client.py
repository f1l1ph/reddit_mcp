from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

_stealth = Stealth()

SESSION_FILE = Path(__file__).parent.parent.parent / "session.json"


def setup_session() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        _stealth.apply_stealth_sync(ctx)
        page = ctx.new_page()
        page.goto("https://www.reddit.com/login")
        print("Log in to Reddit in the browser window, then press Enter here to save the session.")
        input()
        ctx.storage_state(path=str(SESSION_FILE))
        print(f"Session saved to {SESSION_FILE}")
        browser.close()


def get_context(playwright):
    if not SESSION_FILE.exists():
        raise RuntimeError("No session found. Run: reddit-mcp-setup")
    browser = playwright.chromium.launch(headless=False)
    ctx = browser.new_context(storage_state=str(SESSION_FILE))
    _stealth.apply_stealth_sync(ctx)
    return browser, ctx


def submit_comment(post_url: str, comment_text: str) -> dict:
    with sync_playwright() as p:
        browser, ctx = get_context(p)
        page = ctx.new_page()
        try:
            page.goto(post_url)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(3000)
            # Guard: confirm we're on a comment thread, not redirected elsewhere
            if "/comments/" not in page.url:
                page.screenshot(path=str(SESSION_FILE.parent / "debug.png"))
                raise RuntimeError(f"Page redirected away from comment thread: {page.url}")
            # Scroll to and click the comment box with placeholder "Join the conversation"
            coords = page.evaluate("""() => {
                for (const h of document.querySelectorAll('faceplate-textarea-input')) {
                    const ph = h.getAttribute('placeholder') || '';
                    if (!ph.toLowerCase().includes('conversation')) continue;
                    h.scrollIntoView({block: 'center'});
                    if (h.shadowRoot) {
                        const ta = h.shadowRoot.querySelector('textarea');
                        if (ta) {
                            const r = ta.getBoundingClientRect();
                            if (r.width > 10) return {cx: r.left + r.width/2, cy: r.top + r.height/2};
                        }
                    }
                }
                return null;
            }""")
            if not coords:
                page.screenshot(path=str(SESSION_FILE.parent / "debug.png"))
                raise RuntimeError("Could not locate comment box (faceplate-textarea-input[placeholder*='conversation'])")
            # Small pause after scroll to let layout settle
            page.wait_for_timeout(500)
            # Click to focus, press Space to expand, clear it
            page.mouse.click(coords["cx"], coords["cy"])
            page.wait_for_timeout(300)
            page.keyboard.press("Space")
            page.wait_for_timeout(1500)
            # Guard: space can trigger Reddit's create-post shortcut if we hit the wrong element
            if "/comments/" not in page.url:
                page.screenshot(path=str(SESSION_FILE.parent / "debug.png"))
                raise RuntimeError(f"Space keypress triggered navigation away from comments: {page.url}")
            page.keyboard.press("Backspace")
            # Type the comment
            page.keyboard.type(comment_text, delay=50)
            # Click the submit button (slot="submit-button")
            try:
                submit = page.locator('button[slot="submit-button"]').first
                submit.wait_for(timeout=5000)
                submit.click(force=True)
            except Exception:
                page.screenshot(path=str(SESSION_FILE.parent / "debug.png"))
                raise RuntimeError("Could not find submit button button[slot='submit-button']")
            page.wait_for_timeout(2000)
        finally:
            browser.close()
    return {"status": "posted", "post_url": post_url}


def check_session_valid() -> bool:
    import json as _json
    with sync_playwright() as p:
        browser, ctx = get_context(p)
        page = ctx.new_page()
        try:
            page.goto("https://www.reddit.com/api/me.json")
            page.wait_for_load_state("domcontentloaded")
            body = page.evaluate("() => document.body.innerText")
            data = _json.loads(body)
            return bool(data.get("data") and data["data"].get("name"))
        except Exception:
            return False
        finally:
            browser.close()
