## A trail byte that looks like a lead byte

If your two-byte encoding is `lead = LEAD0 + s/N`, `trail = TRAIL0 + s%N`, check
whether any trail value can reach LEAD0. With `LEAD0 = 0xC0`, `TRAIL0 = 0x40`,
`N = 192` the trail spans 0x40-0xFF, so **449 of 1345 shipped syllables carried a
trail byte >= 0xC0** — including the most common ones.

The main render loop tracks pair state and handles this fine. A *secondary* pass
does not: a help-window formatter re-scanned the string, took a trail byte for a
fresh lead, and resynced a few glyphs later. On screen a line read as
`부덧겹x관의 이름` where the ROM held a byte-perfect `부대 지휘관의 이름` — string,
pointer, glyph chains and bitmaps all verified correct, so every check upstream
of the pixels passed.

The robust fix is a compact custom encoding. You only ship the syllables you
actually use (~1300), so assign them sequential codes with the trail confined
below LEAD0 — 128 trails x 64 leads is 8192 slots, far more than needed. Then no
byte in a trail position can be mistaken for a lead by any pass you have not
found yet.

Suspect this whenever corruption is **localised and self-correcting**: a run of
wrong glyphs that snaps back to correct text is a desync, not a bad glyph. Note
also that the ASCII path indexes `glyphTable[char]` while the two-byte path
indexes `glyphTable[trail - TRAIL0]`, so the two index spaces overlap — a
syllable whose trail is 0x98 lands on the slot ASCII uses for `X`, which is
worth remembering when a stray `X` appears in Korean text.

# Line width: the bug that hides as a translation problem

FE8 draws each line into a fixed-width buffer and **does not wrap**. A line wider
than its buffer is not clipped at the margin — it is **dropped entirely**, or it
spills into neighbouring tiles and garbles a few glyphs before recovering.

This is worth stating plainly because the symptoms all look like something else:

| What you see | What it actually is |
|---|---|
| A text box opens, waits for A, and shows nothing | that line is over budget |
| Dialogue "skips" scenes | several consecutive lines over budget |
| A syllable turns to garbage mid-line, then text resumes | slightly over budget |
| Garbage looks like it clusters on certain syllables (은/가/와/지) | coincidence — those are just common |

A translator reading the source sees perfectly good Korean. The ROM data is
byte-correct. Only the pixels are wrong.

## Derive the budget from the original, per surface

The English script was authored to fit, so **the widest original line is the
budget** — no guessing, no measuring boxes by eye. Take it from the pre-
translation commit.

Each surface has its own budget, and they differ a lot. Measured on one FE8U
hack:

| Surface | Budget |
|---|---|
| Dialogue box | 213 px |
| Guide / journal body | 182 px |
| Guide section labels (left menu) | 46 px |
| Preparations info panel (narrow font) | ~125 px — about 10 Hangul |
| Stat-screen label column | 20 px — one syllable, not two |

Do not reuse the dialogue budget everywhere. The guide panel is narrower, and
checking it against 213px reports zero problems while the right-hand side is
visibly cut off in game.

## Read the ASCII advances from the BUILT rom, not the clean one

This one silently defeated the whole check for every `^`-marked entry.

Entries marked `^` render through a **narrow font** that the hack installs into
glyph slots 0x81-0xBC. Those slots are **empty in the clean ROM**, so a checker
reading advances from the clean ROM finds nothing and falls back to a default —
8px, when the real narrow advance is **4-5px**.

Every consequence points the wrong way:

- The budget, derived from English lines that are almost all ASCII, comes out
  roughly **2x too generous** (a 29-character line measured 222px; it is 109px).
- Korean is 12px per syllable either way, so it is measured correctly.
- Over-wide Korean is therefore compared against a doubled budget and **passes**.

The tell is a screen that garbles while the checker reports zero. When that
happens, do not re-reason about the encoding — the bytes will be fine. Print the
advances the checker is actually using and confirm they are non-null.

Read the font from the **built** ROM. Everything the hack installs — narrow
glyphs, extra glyph banks, a repointed font table — exists only there.

And apply `narrowText()`'s own mapping when measuring a `^` entry: spaces become
a 2px glyph, letters become their narrow slots. Measuring `^` text with ordinary
ASCII advances is the same mistake in a smaller form.

## Measure display lines, not source lines

A break code can sit **mid-line**: `이름/이름:[N]4/8/22[N]` is two rows on screen.
Measuring the raw source line sums both and overstates the width, which makes the
tool demand cuts that aren't needed.

Split on `[N]` / `[NL]` / `[2NL]` first, then measure each segment. Strip bracket
codes before summing — they draw nothing.

Widths: pull ASCII advances from the real font in the clean ROM (glyph struct
`+5` is the advance), and use the generator's uniform Hangul advance (12px
dialogue / 11px menu in this project). Do not approximate.

## Fixing an over-wide line

**Tighten the wording in place. Do not move words to the next line** — that line
then goes over instead, and the problem walks down the entry.

Hold the bracket codes fixed: same count, same order, same positions. Only the
prose between them changes.

```
이 거래를 받아들이고 우리에게 협조한다면,   234px → blank box
이 거래를 받아들여 협조한다면,             renders
```

Aim under the budget, not at it — a 205px target against a 213px budget absorbs
the odd mis-measurement.

## Overflow that isn't a text box

The same budget logic governs UI that is not dialogue:

- **Menu labels have a tile allocation sized for the English.** A section label
  59px against a 46px budget did not merely clip — it smeared black blocks over
  the *other* entries in the list, and the damage moved as you paged. Shortening
  the labels fixed all of them.
- **Values drawn after their label get pushed.** In a stat box where the number
  follows the label rather than being right-aligned, a wider Korean label shoves
  the number into the next column. Korean at 11px/syllable is wider than a
  3-character narrow-font English abbreviation, so even two syllables can be too
  wide. One syllable (공 명 필 회 사) is narrower than the English was and the
  columns line up again — a reasonable alternative to keeping the labels English.

## Keep it in the build

Make the checker print its numbers on every build and gate on zero. Width damage
is invisible to entry/token guards, so nothing else will catch it.
