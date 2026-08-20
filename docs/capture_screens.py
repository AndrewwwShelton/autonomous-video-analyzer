"""Capture every screenshot the UID document and the deck need.

    python demo_setup.py                 # seed the library first
    python -m uvicorn backend.main:app --port 8000
    python docs/capture_screens.py       # in a second terminal

Writes PNGs to docs/screens/ using the filenames docs/SCREENSHOT_CHECKLIST.md
lists. Re-run it after any interface change -- the screenshots went stale once
because re-shooting them was a fifteen-step manual process, and a script is the
only thing that stops that happening again.

Uses the Chrome already installed on the machine (channel="chrome"), so there is
no separate browser download. Captures at device_scale_factor=2 because these
end up on a projector and in a printed report.

Requires: pip install playwright
"""
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
OUT = Path(__file__).resolve().parent / "screens"
OUT.mkdir(parents=True, exist_ok=True)

DESKTOP = {"width": 1440, "height": 900}


def shot(page, name, full_page=False):
    page.screenshot(path=str(OUT / name), full_page=full_page)
    print(f"  {name}")


def settle(page, ms=700):
    """Wait for the network, the web fonts and the entry animations.

    The icons are a Google Fonts webfont; without waiting for document.fonts
    every icon renders as its literal ligature text ("check_circle") and the
    whole interface looks broken.
    """
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(ms)


def goto(page, path, wait_for=None):
    page.goto(f"{BASE}{path}")
    if wait_for:
        page.wait_for_selector(wait_for, timeout=15000)
    settle(page)


def new_page(browser, theme="dark", **viewport):
    vp = {**DESKTOP, **viewport}
    ctx = browser.new_context(viewport=vp, device_scale_factor=2)
    ctx.add_init_script(f"localStorage.setItem('theme', '{theme}');")
    return ctx, ctx.new_page()


# --------------------------------------------------------------- the captures

def capture_desktop(browser):
    ctx, page = new_page(browser)

    # 1 - Dashboard
    goto(page, "/", ".page-title, .card")
    shot(page, "01-dashboard.png")

    # 2 - Content, with a row hovered so the action icons show
    goto(page, "/content", ".vtable")
    page.hover(".vtable tbody tr:first-child .vcell")
    page.wait_for_timeout(400)
    shot(page, "02-content.png")

    # 3 - Video detail. Target the ANALYSED video by name: the table is newest
    # first, so the first row is the one deliberately left un-analysed and a
    # positional click lands on an empty "not analyzed yet" panel.
    page.click(".vcell__title:has-text('brand_review_final')")
    page.wait_for_url("**/video/**")
    settle(page)
    shot(page, "03-video-detail.png", full_page=True)

    # 4 - Analytics, all charts
    goto(page, "/analytics", ".card")
    page.wait_for_timeout(900)          # let the charts draw
    shot(page, "04-analytics.png", full_page=True)

    # 5 - Reports, with one generated so the history table is not empty
    goto(page, "/reports", ".card")
    try:
        page.select_option("select", index=1)
        page.click("button:has-text('Generate report')")
        page.wait_for_timeout(1500)
    except Exception as exc:                              # noqa: BLE001
        print(f"    (could not generate a report: {exc})")
    settle(page)
    shot(page, "05-reports.png", full_page=True)

    # 6 - Settings
    goto(page, "/settings", ".card")
    shot(page, "06-settings.png")

    # 7 - Upload dialog
    goto(page, "/", ".card")
    page.click(".create-btn")
    page.wait_for_timeout(600)
    shot(page, "07-upload-dialog.png")

    ctx.close()


def _get_config():
    return json.loads(urllib.request.urlopen(f"{BASE}/api/config").read())


def _put_config(cfg):
    req = urllib.request.Request(
        f"{BASE}/api/config", data=json.dumps(cfg).encode(),
        headers={"Content-Type": "application/json"}, method="PUT")
    urllib.request.urlopen(req)


def capture_progress(browser):
    """Catch the inline progress bar during a genuine analysis.

    This one has to run in real mode. A demo-mode analysis finishes in about
    two tenths of a second -- faster than the interface can paint a progress
    bar at all -- so clicking Run checks in demo mode yields a row that goes
    straight from pending to complete and no screenshot.

    Waits for a frame-scanning stage rather than the first stage that appears:
    the sample footage carries no audio track, so the earliest real stage reads
    "No audio track - skipping transcription", which is honest but a confusing
    thing to put in a document.
    """
    cfg = _get_config()
    previous_mode = cfg["analysis_mode"]
    cfg["analysis_mode"] = "real"
    _put_config(cfg)

    ctx, page = new_page(browser)
    try:
        goto(page, "/content", ".vtable")
        btn = page.locator("[aria-label*='checks on studio_review_cut']").first
        if btn.count() == 0:
            print("    (studio_review_cut.mp4 not in the library -- skipped)")
            return

        btn.click()
        page.wait_for_selector(".progress", timeout=30000)

        best = None
        for _ in range(60):
            page.wait_for_timeout(400)
            try:
                stage = page.locator(".progress__label").first.inner_text()
            except Exception:                             # noqa: BLE001
                break                                     # run finished
            best = stage
            low = stage.lower()
            if "0%" not in stage and ("fram" in low or "scan" in low
                                      or "plac" in low):
                break
        print(f"    stage: {(best or '').replace(chr(10), ' | ')}")
        shot(page, "08-progress.png")
    except Exception as exc:                              # noqa: BLE001
        print(f"    (progress bar never appeared: {exc})")
    finally:
        ctx.close()
        cfg["analysis_mode"] = previous_mode
        _put_config(cfg)
        print(f"    analysis_mode restored to '{previous_mode}'; "
              "re-run demo_setup.py to reset the library")


def capture_validation(browser):
    """Add a dictionary row, retype an existing word, capture the error."""
    ctx, page = new_page(browser)
    goto(page, "/settings", ".card")

    first = page.locator("[aria-label='Restricted word 1']")
    duplicate = first.input_value()

    page.click("button:has-text('Add')")
    page.wait_for_timeout(300)
    rows = page.locator("[aria-label^='Restricted word']")
    last = rows.nth(rows.count() - 1)
    last.fill(duplicate)
    last.blur()
    page.wait_for_timeout(400)
    last.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    shot(page, "09-validation.png")
    ctx.close()


def capture_responsive(browser):
    for name, width, height in (("11-responsive-laptop.png", 1024, 800),
                                ("12-responsive-tablet.png", 768, 900),
                                ("13-responsive-mobile.png", 375, 812)):
        ctx, page = new_page(browser, width=width, height=height)
        goto(page, "/content", ".vtable, .vtable--cards")
        if width == 768:
            # Show the drawer and its scrim -- that is the point of this width.
            try:
                page.click("[aria-label='Toggle navigation menu']")
                page.wait_for_timeout(500)
            except Exception:                             # noqa: BLE001
                pass
        shot(page, name)
        ctx.close()


def capture_light(browser):
    ctx, page = new_page(browser, theme="light")
    goto(page, "/", ".card")
    shot(page, "14-theme-light.png")
    ctx.close()


def capture_empty(browser):
    """Empty dashboard. DESTRUCTIVE -- deletes every video, so it is opt-in.

    Run demo_setup.py afterwards to put the library back.
    """
    videos = json.loads(urllib.request.urlopen(f"{BASE}/api/videos").read())
    for v in videos:
        req = urllib.request.Request(
            f"{BASE}/api/videos/{v['video_id']}", method="DELETE")
        urllib.request.urlopen(req)
    print(f"    deleted {len(videos)} video(s)")

    ctx, page = new_page(browser)
    goto(page, "/", ".card, .empty")
    shot(page, "10-empty-state.png")
    ctx.close()
    print("    library is now EMPTY -- run demo_setup.py to restore it")


def check_layout(browser):
    """Fail loudly if any page scrolls sideways at a documented width.

    Worth running before every capture: the video detail page quietly started
    overflowing by 150px at 1440, and the only reason it was noticed was that a
    full-page screenshot came out wider than the fixed header.
    """
    pages = ["/", "/content", "/video/1", "/analytics", "/reports", "/settings"]
    widths = [(1920, 1080), (1440, 900), (1024, 800), (768, 900), (375, 812)]
    bad = []
    for w, h in widths:
        ctx = browser.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        for path in pages:
            page.goto(f"{BASE}{path}")
            try:
                page.wait_for_selector(".card, .skeleton-page", timeout=10000)
            except Exception:                             # noqa: BLE001
                pass
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(400)
            r = page.evaluate("() => ({s: document.documentElement.scrollWidth,"
                              " c: document.documentElement.clientWidth})")
            if r["s"] - r["c"] > 1:
                bad.append(f"{path} at {w}px overflows by {r['s'] - r['c']}px")
        ctx.close()
    if bad:
        print("  LAYOUT PROBLEMS:")
        for b in bad:
            print(f"    {b}")
    else:
        print(f"  layout ok at {len(widths)} widths x {len(pages)} pages")
    return not bad


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        print(f"capturing to {OUT}")
        check_layout(browser)
        capture_desktop(browser)
        capture_progress(browser)
        capture_validation(browser)
        capture_responsive(browser)
        capture_light(browser)
        if "--with-empty-state" in sys.argv:
            capture_empty(browser)
        browser.close()
    print("done")


if __name__ == "__main__":
    sys.exit(main())
