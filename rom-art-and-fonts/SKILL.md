---
name: rom-art-and-fonts
description: Drawing text and art into retro console ROMs so it is actually legible on screen — rasterising fonts at tiny sizes, spending an existing indexed palette as an anti-aliasing ramp, measuring the writable box off the original art instead of guessing it, and the debugging discipline that keeps a long romhack from going in circles. ALWAYS consult this when asked to make a Korean patch for any game ("한글패치 해줘", "한글화", "KR patch", "ROM 번역", fan translation), because every such project has to render glyphs into someone else's fixed-size UI, and the same handful of mistakes cost days each time. Also use when redrawing a title logo, banner, menu plate or credit line; when small text looks like mush, is cut off, or renders as tofu boxes; when text will not fit a fixed-width slot; or when a symptom has survived several fixes and the debugging itself has stalled. Owns the pixels; the per-console skills (gba-fe-korean-patch, snes-korean-patch, retro-rom-korean-patch, create-kr-patch) own the text pipeline, and rom-graphics-verification owns compression and edit verification.
---

# Drawing into a ROM: art, fonts, and not going in circles

Two failure modes dominate this work, and neither is about art skill.

**Wrong-surface failures.** You guess the size of the box, the colour of the
ink, or the height of the band, and everything downstream is wasted. The console
already knows all three — read them off the original rather than inferring them.

**Instrument failures.** The debugger, the encoder, or your own preview lies to
you, and you spend hours reasoning correctly from false premises. Most long
detours in a romhack are this.

Read `references/` when you hit the matching stage.

| Stage | File |
|---|---|
| Making small text legible: rasterising, palette ramps, thresholds | `references/rendering.md` |
| Reading the real geometry and colours off the original art | `references/measuring.md` |
| Debugging discipline: instruments, feasibility, inference vs fact | `references/verification.md` |

## The single highest-value technique

**Spend the palette you already have as an anti-aliasing ramp.**

Indexed art usually carries a shading ramp — 8 to 10 steps of one hue. If you
render text to 1 bit and pick one ink colour, every stroke thinner than a pixel
either rounds to solid or disappears. That is what "mush" is.

Map the font's own grayscale coverage onto that existing ramp instead. A
half-covered pixel becomes a mid-tone rather than a coin flip, and the same
pixel count reads as far higher resolution. On a 15px ribbon this was the
difference between an illegible subtitle and clean serif Hanja.

It does **not** generalise downward. At 7px, Latin stems are already exactly one
pixel: there is no sub-pixel detail for a mid-tone to represent, and
anti-aliasing only smears them. A pixel font at its native size wins there.
The technique buys resolution only where detail exists below the pixel grid.

## Working order

1. **Read the surface from the running game** — OAM/VRAM/palette RAM for a
   sprite logo, the original glyph rows for a font. Never infer geometry.
2. **Measure the writable area and the ink indices** off the original art.
3. **Generate, preview as an image, and look** — before touching the ROM.
4. **Patch, then verify on the console**, not in the preview.
5. **Package with hashes computed by applying the shipped patch**, not from the
   build you happened to have.

## Before iterating on a workaround, do the arithmetic

When a fix fails, the reflex is to try a variant. Compute whether the approach
can work at all first — it is usually five minutes and it is decisive.

A worked example that cost four attempts before anyone did the sum: a text box
sized itself by character count at ~4.6px per character, and the Korean needed
~90px more than it was getting. Padding with spaces looked like the fix. But a
space *draws* ~4px while *buying* ~4.6px — a net gain of 0.6px each. Closing a
90px gap needs ~150 spaces, which would themselves draw ~600px on a 240px
screen. The approach was arithmetically impossible from the first attempt.

Worse, the padding was itself producing the symptom it was meant to cure:
removing it entirely made the box correct. **When a workaround makes things
stranger, suspect the workaround before the engine.**

## Mark inference as inference

Long sessions accumulate documentation, and a plausible inference written down
as a fact will be believed later — by you, and by anyone else reading it.

In one session three separate "facts" recorded in a lookup table turned out to
be unverified inferences, each of which then had to be un-taught. If you write a
conclusion you have not measured, say so in the same sentence, and say what
would settle it.
