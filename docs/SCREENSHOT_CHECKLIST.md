# Screenshot capture list — for the UID document

**These are captured by a script. Do not shoot them by hand.**

```bash
python docs/capture_screens.py
```

That writes all thirteen into `docs/screens/` at 2× for print, and `build_deck.js`
and `main.tex` read from there. The fourteenth, the empty state, is destructive and
opt-in: `python docs/capture_screens.py --with-empty-state`, then re-seed.

The script exists because these screenshots went stale once and nobody noticed for
six weeks — they predated the three-state verdict, the reasoning banner and the
per-finding Model column. Re-shooting by hand is a fifteen-step process; re-running a
script is not, so **re-run it after any interface change**.

## Setup

```bash
pip install playwright
python demo_setup.py
python -m uvicorn backend.main:app --port 8000
```

Then run the capture in a second terminal. `demo_setup.py` leaves two videos in the
library: `brand_review_final.mp4` (analysed) and `studio_review_cut.mp4` (not
analysed — the script runs that one to catch the progress bar).

The script drives the Chrome already installed on the machine, so there is no browser
download. It first checks all six pages at all five documented widths for horizontal
overflow and prints any it finds; that check caught three real layout bugs.

Afterwards it prints a reminder to re-run `demo_setup.py`, because catching the
progress bar requires a genuine real-mode run — demo mode finishes in about two
tenths of a second, faster than the interface can paint a progress bar at all.

## What each shot should contain

The table below is the reference for what the script produces, and what to check if a
capture ever looks wrong.

---

## A. The seven screens (desktop, 1280×720 or wider)

| # | File | Screen | How to get there / what to show |
|---|---|---|---|
| 1 | `01-dashboard.png` | Dashboard | Landing page `/`. Show the 4 stat cards, Library health split bar, Recent uploads. |
| 2 | `02-content.png` | Content | `/content`. **Hover a row** so the open/re-run/delete icons are visible. |
| 3 | `03-video-detail.png` | Video Detail | Click `brand_review_final.mp4`. Show stats, timeline, player, Audio flags tab. |
| 4 | `04-analytics.png` | Analytics | `/analytics`. All six charts visible (scroll so most fit). |
| 5 | `05-reports.png` | Reports | `/reports`. Generate one CSV first so the history table isn't empty. |
| 6 | `06-settings.png` | Settings | `/settings`. Show the dictionary rows + pipeline fields. |
| 7 | `07-upload-dialog.png` | Upload dialog | Click **Create**. Show the drop zone. |

## B. States that prove the interaction design

| # | File | What to show |
|---|---|---|
| 8 | `08-progress.png` | On `/content`, click **Run checks** on `studio_review_cut.mp4` and capture the inline progress bar mid-run ("Transcribing audio", "Scanning frames…"). Be quick — it finishes in seconds. |
| 9 | `09-validation.png` | On `/settings`, type `damn` into a second dictionary row → red "Already listed on row 1", Save disabled. |
| 10 | `10-empty-state.png` | *(optional)* Delete all videos to show the Dashboard empty state, or skip — `demo_setup.py` restores the library. |

## C. Responsive (same page, three widths)

Use F12 → device toolbar. Capture the **Content** page at each width:

| # | File | Width | Expect |
|---|---|---|---|
| 11 | `11-responsive-laptop.png` | 1024 | Sidebar collapsed to icon rail, stats 2-up |
| 12 | `12-responsive-tablet.png` | 768 | Sidebar hidden; tap ☰ to show the drawer + dark scrim |
| 13 | `13-responsive-mobile.png` | 375 | Table rendered as **cards**, search hidden, Create is icon-only |

> Reload the page after changing width — the preview environment doesn't always fire
> resize events, and a reload guarantees the correct layout.

## D. Theme (one pair, to document the token system)

| # | File | What |
|---|---|---|
| 14 | `14-theme-light.png` | Dashboard with the sun/moon toggle switched to light |

---

## Why these

- **A** covers the "minimum six screen wireframes" requirement (we have seven).
- **B** covers §6 Field Validation Rules and the progress/feedback story in §9 Usability.
- **C** covers §7 Responsive Design — the document asks for Desktop/Laptop/Tablet/Mobile.
- **D** supports the §4 UI Standards colour-palette section.
