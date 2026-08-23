"""Build the report's Images/ folder at a size LaTeX can actually compile.

    python docs/FinalReport/make_images.py

Sources are the 2x originals in docs/diagrams/out and docs/screens. Those are
right for the screen and for the slide deck, and wrong for the report: at
2880 px wide, placed at 0.95\\textwidth, they carry about 500 dpi. Nothing is
printed at 500 dpi, and the whole set came to 118 megapixels, which pdfLaTeX
could not decode and embed inside Overleaf's free-tier compile budget. The
build timed out rather than failed, which is a confusing way to find this out.

The text block here is A4 minus a 1.5in left and 1in right margin, so 5.77in.
A figure at 0.95\\textwidth is 5.48in, and MAX_W of 1600 px gives it just under
300 dpi -- the usual target for print, and about a third of the pixel data.

Re-run this after re-capturing screenshots or regenerating diagrams.
"""
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "Images"

SOURCES = [ROOT / "docs" / "diagrams" / "out", ROOT / "docs" / "screens"]
LOGOS = ROOT / "docs" / "InitialDraft" / "Images"

MAX_W = 1600          # ~300 dpi at 0.95\textwidth on A4 with these margins
MAX_W_FAST = 1100     # ~200 dpi, for iterating when a compile budget is tight


def main():
    max_w = MAX_W_FAST if "--fast" in sys.argv else MAX_W
    OUT.mkdir(parents=True, exist_ok=True)

    # Flattened like everything else. These were being copied through
    # untouched and were the last two files carrying an alpha channel.
    for logo in ("CU_logo.png", "CU_logo_blue.png"):
        if not (LOGOS / logo).exists():
            continue
        im = Image.open(LOGOS / logo).convert("RGBA")
        flat = Image.new("RGB", im.size, (255, 255, 255))
        flat.paste(im, mask=im.split()[-1])
        if flat.width > 900:                      # placed at 4cm, never larger
            flat = flat.resize((900, round(flat.height * 900 / flat.width)),
                               Image.LANCZOS)
        flat.save(OUT / logo, "PNG", optimize=True)

    before = after = 0
    written = 0
    for src_dir in SOURCES:
        for src in sorted(src_dir.glob("*.png")):
            im = Image.open(src)
            w, h = im.size
            before += w * h

            # Flatten alpha onto white. Every diagram came out of matplotlib as
            # RGBA over an opaque white background, so the channel carried no
            # information -- but pdfTeX cannot ignore it: an alpha channel makes
            # it decode the image and build a separate soft mask.
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                flat = Image.new("RGB", im.size, (255, 255, 255))
                flat.paste(im, mask=im.split()[-1])
                im = flat
            else:
                im = im.convert("RGB")

            if w > max_w:
                im = im.resize((max_w, round(h * max_w / w)), Image.LANCZOS)
            after += im.size[0] * im.size[1]

            # Screenshots (numbered files) go out as JPEG: pdfTeX copies a
            # DCTDecode stream into the PDF verbatim, without decoding it at
            # all, which is the single largest saving available here. Diagrams
            # stay PNG -- they are line art, and JPEG rings around thin text.
            if src.stem[0].isdigit():
                im.save(OUT / f"{src.stem}.jpg", "JPEG", quality=88,
                        optimize=True, progressive=False)
                (OUT / src.name).unlink(missing_ok=True)
            else:
                im.save(OUT / src.name, "PNG", optimize=True)
            written += 1

    files = list(OUT.glob("*.png")) + list(OUT.glob("*.jpg"))
    total_mb = sum(p.stat().st_size for p in files) / 1048576
    alpha = [p.name for p in OUT.glob("*.png")
             if Image.open(p).mode in ("RGBA", "LA", "P")]
    print(f"wrote {written} images to {OUT}")
    print(f"  raster {before / 1e6:.0f} MP -> {after / 1e6:.0f} MP "
          f"({100 * (1 - after / before):.0f}% less)")
    print(f"  on disk {total_mb:.1f} MB   max width {max_w} px")
    print(f"  {len(list(OUT.glob('*.jpg')))} JPEG, "
          f"{len(list(OUT.glob('*.png')))} PNG, {len(alpha)} still with alpha")


if __name__ == "__main__":
    main()
