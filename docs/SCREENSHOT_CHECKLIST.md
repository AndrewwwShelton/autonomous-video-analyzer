# Screenshot capture list — for the UID document

Everything below exists in the app right now. Capture these and the UID document has
every figure it needs.

## Setup (once)

```bash
python demo_setup.py
```
Then double-click `RUN_DEMO.bat` and open <http://localhost:8000>.

This leaves two videos in the library: `brand_review_final.mp4` (already analysed) and
`studio_review_cut.mp4` (not analysed — use it for the live "running checks" shot).

**Capture tips**
- Use **dark theme** (the default) for the main set — it is the product's identity.
- Windows: `Win + Shift + S` → window capture. Or `F12` → device toolbar for exact widths.
- Save as PNG into `docs/screens/` using the filenames below.
- Browser zoom at 100%. Hide bookmarks bar for a cleaner frame.

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
