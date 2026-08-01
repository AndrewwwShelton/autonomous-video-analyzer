# Accuracy Benchmark

The SRS claims *"a precision rate greater than 85% on benchmark testing sets."*
This directory is the evidence for that claim. Without it the number is an
assertion, and it is the first thing an examiner will probe.

**The harness is finished. The labelling is not.** Labelling is slow manual work
that cannot be compressed at the end, so start it now and run it alongside M2/M3a.

---

## Quick reference

```bash
python benchmark/evaluate.py --validate     # check label files, run nothing
python benchmark/evaluate.py                # score the real engines
python benchmark/evaluate.py --mode demo    # sanity-check the harness itself
python benchmark/make_synthetic_clip.py     # regenerate the synthetic fixture
```

Runs use a throwaway database, so benchmarking never touches your real library.

---

## Layout

```
benchmark/
├── clips/      the video files            (gitignored — large)
├── labels/     one JSON per clip          (committed — this is the real work)
├── results/    timestamped run reports    (gitignored)
└── evaluate.py
```

Labels are committed and clips are not, so the ground truth survives even if the
media is moved. Keep a note of where each clip came from in its `source` field.

---

## Label format

One JSON file per clip, in `labels/`, named after the clip:

```json
{
  "clip": "creator_vlog_03.mp4",
  "source": "Creative Commons, youtube.com/watch?v=...",
  "notes": "Handheld, background music under speech from 0:40.",
  "audio": [
    { "word": "damn", "at": 12.4 },
    { "word": "hell", "at": 47.9 }
  ],
  "visual": [
    { "category": "Weapon",    "at": 63.0, "object": "kitchen knife" },
    { "category": "Substance", "at": 88.5, "object": "beer bottle" }
  ],
  "ad_spots": [
    { "start": 20.0, "end": 31.5, "type": "blank_wall" }
  ]
}
```

| Field | Meaning |
|---|---|
| `at` | when the event occurs, in seconds |
| `word` | the restricted term as actually spoken |
| `category` | exactly one of `Weapon`, `Substance`, `Graphic` |
| `object` | free text, for your own reference — not scored |
| `start` / `end` | span of a usable advertisement surface |

Run `--validate` after editing. It catches malformed files in a second, which is
much cheaper than discovering them halfway through a benchmark run.

---

## How to label a clip

1. Drop the video into `clips/`.
2. Create `labels/<same-name>.json` using the template above.
3. Watch it once for **speech**: every time a word from your dictionary is said,
   note the word and the time. Label what was *actually said*, not what you think
   the model will hear.
4. Watch again for **visuals**: note weapons, alcohol, smoking, drugs and graphic
   content, with the time each becomes visible.
5. Optionally note **ad spots** — stretches of at least 5 seconds where a clear,
   uncluttered surface stays put.
6. `python benchmark/evaluate.py --validate`

### Rules that keep the numbers meaningful

- **Label from the source, never from the tool's output.** Grading a model against
  its own predictions measures nothing. This is the single easiest way to ruin a
  benchmark, and it is invisible in the final number.
- **Label every occurrence**, including ones you expect the model to miss.
  Omitting hard cases inflates recall.
- **Only label terms that are in your dictionary.** The audio engine cannot flag a
  word it was never asked to look for; scoring it for that would measure the
  dictionary, not the engine.
- **Timing can be approximate.** Matching allows ±2 s for audio and ±1.5 s for
  visuals, because ASR boundaries drift and vision samples once per second.

---

## How scoring works

- **Audio** matches on the flagged word within ±2 s. Severity is deliberately not
  scored: it is looked up from your dictionary once a word is found, so scoring it
  would measure the config file rather than the engine.
- **Visual** matches on risk category within ±1.5 s. The raw class name is
  model-specific — penalising `knife` versus `Knife` would say nothing about
  detection quality.
- **Ad spots** match on temporal overlap (IoU ≥ 0.3), since these are stretches of
  time rather than instants.
- Each labelled event can be claimed by at most one prediction, so a model that
  repeats a flag cannot farm true positives from it.

Precision = TP / (TP + FP) · Recall = TP / (TP + FN)

---

## Two guards built into the harness

**Stubbed engines are excluded.** Any stage still running a demo stand-in is marked
`EXCLUDED (stub)` and kept out of the headline figure. A precision score computed
over a stub looks identical to a real one on a slide; the harness will not let that
happen. Today that means audio counts and vision does not, until M2 lands.

**Small samples are flagged.** Below 30 labelled events or 10 real clips, the report
prints `*** NOT YET PUBLISHABLE ***` and tells you not to quote the figure. A
precision of 100% over four events is not a result.

---

## The synthetic fixture

`make_synthetic_clip.py` builds a clip from Windows text-to-speech with ground truth
derived from measured phrase durations — independent of Whisper, so the model is not
grading itself.

It exists to **prove the harness works** and to give a clean-speech ceiling. It is
**not evidence for the accuracy claim**: text-to-speech is pristine studio diction
with no music, noise, accents, or overlapping speakers, so any figure from it is
optimistic. Real clips are what count, which is why the report counts synthetic and
real clips separately.

---

## Target

Aim for **20–30 real clips**, varied on purpose:

- clean studio speech and noisy handheld footage
- speech over background music
- different accents and speaking speeds
- clips containing **no** violations at all — these catch false positives, and a
  benchmark without them will flatter the tool
- indoor scenes with genuinely usable blank surfaces, for the ad-spot side

Aim for at least 30 labelled events overall. Roughly one clip labelled per sitting
is a realistic pace.
