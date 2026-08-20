"""Prove the interface renders correctly with no internet at all.

    python -m uvicorn backend.main:app --port 8000
    python docs/check_offline.py

Blocks every request that is not localhost, then walks each page and checks
that every Material Symbols element rendered as a glyph rather than as its
own ligature name.

This exists because the interface loaded its fonts from fonts.googleapis.com
while the product claimed to run entirely offline. With no network the
navigation read "dashboard video_library bar_chart" in plain text and the app
looked broken -- one presentation room without wifi away from a dead demo.

A glyph is one em wide; the name it falls back to is several em. So the test is
the ratio of rendered width to the element's OWN font size, not an absolute
width -- empty-state icons are set at 96px and a flat pixel threshold reported
them as broken when they were perfectly fine.
"""
import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
PAGES = ["/", "/content", "/video/1", "/analytics", "/reports", "/settings"]
MAX_EM = 1.6            # widest real glyph is 1em; "description" is over 4em


def main():
    failures, external = [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})

        def gate(route, request):
            if "localhost" in request.url or request.url.startswith("data:"):
                route.continue_()
            else:
                external.append(request.url)
                route.abort()

        ctx.route("**/*", gate)
        page = ctx.new_page()

        for path in PAGES:
            page.goto(f"{BASE}{path}")
            try:
                page.wait_for_selector(".card, .empty, .vtable", timeout=15000)
            except Exception:                                 # noqa: BLE001
                pass
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(1200)

            bad = page.evaluate("""(maxEm) => {
              const out = [];
              document.querySelectorAll('.material-symbols-outlined')
                .forEach(el => {
                  const w = el.getBoundingClientRect().width;
                  const em = parseFloat(getComputedStyle(el).fontSize) || 24;
                  if (w / em > maxEm) out.push({name: el.textContent.trim(),
                                                width: Math.round(w),
                                                em: Math.round(em),
                                                ratio: +(w / em).toFixed(1)});
                });
              return out;
            }""", MAX_EM)

            total = page.locator(".material-symbols-outlined").count()
            mark = "ok      " if not bad else "TEXT!   "
            print(f"  {mark} {path:<12} {total:>3} icons"
                  + (f"   -> {bad}" if bad else ""))
            for b in bad:
                failures.append(f"{path}: '{b['name']}' rendered {b['width']}px "
                                f"at {b['em']}px font ({b['ratio']} em)")

        browser.close()

    hosts = sorted({u.split("/")[2] for u in external if "//" in u})
    print(f"\n  external requests blocked: {len(external)}"
          + (f" ({', '.join(hosts)})" if hosts else " — none attempted"))

    if failures:
        print("\nFAILED — icons fell back to text:")
        for f in failures:
            print(f"  {f}")
        return 1
    print("\nAll icons rendered as glyphs with the network cut. Offline is real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
