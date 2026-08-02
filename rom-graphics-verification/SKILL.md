---
name: rom-graphics-verification
description: >-
  How to change compressed tile graphics in a retro console ROM (GBA/SNES/GB and
  similar tile-and-map hardware) without repeatedly shipping broken screens —
  and how to verify the change actually landed. Covers the compression traps
  that corrupt only on hardware, the difference between the map stored in a
  data block and the map the game builds at runtime, telling artwork apart from
  lettering by palette, and the control experiments that isolate cause in one
  run instead of ten. Use this when editing a title screen, logo, menu plate or
  any pre-rendered graphic in a ROM — especially when the ROM data reads back
  correct but the screen is wrong, when an edit damages parts of the picture it
  never touched, when text appears at a fixed position no matter where it is
  placed, or when shapes come out right and colours come out wrong. Also use it
  before writing a "verify my edit" check, because a check built on the same
  assumptions as the edit cannot catch the edit being wrong.
---

# Changing compressed graphics in a ROM without breaking the screen

`references/case-study.md` walks the twelve-build failure this came from, in
the order the mistakes were made — read it when a symptom has survived several
fixes and you want to see how that state is reached.

This is the accumulated cost of one title-screen edit that took roughly a dozen
broken builds. Every failure below produced tooling that reported success.

Text has a pipeline you can reason about. Graphics do not: a picture is tiles,
a map, a palette and a compressor, and **any one of the four can be wrong while
the other three look perfect.** So the discipline is different — isolate which
of the four is lying before touching art.

## The one rule

**Never verify an edit with a model built from the same assumptions as the
edit.** A checker that reads the map the way your writer writes it will confirm
any consistent mistake. In the case that motivated this skill, an offline check
reported "0 pixels changed outside the intended box" for a build that visibly
punched black holes across the screen — because both the writer and the checker
used the map stored in the data block, and the hardware used a different one.

Verification has to come from a source the edit did not choose: the running
game's VRAM, a screenshot, or the game's own untouched data.

## Order of work

1. **Read the layout out of the running game, not out of the file.** Registers
   for each layer (char base, screen base, bpp, size), the map from VRAM, OAM
   for sprites, palette from palette RAM. Write down what you found.
2. **Find the compressed source** by taking a distinctive run of bytes from
   VRAM and scanning the ROM for a compressed block that decodes to contain it.
3. **Run the null control** (below) before editing anything.
4. Edit, rebuild, and **look at the screen**.
5. Only then refine the art.

## Control experiments that isolate cause in one run

These are cheap and they collapse whole branches of the search. Prefer them to
reasoning about pixels.

**The null control — re-encode the original, change nothing.** Decompress the
block, recompress it with your compressor, patch it back in, boot.

- Screen correct → your compressor is fine. The bug is in your edit or your
  layout model. This single run retires the most expensive suspect.
- Screen broken → your compressor is at fault. Stop looking at your art.

**The identity edit — change one pixel to a colour you cannot miss.** If it
appears somewhere other than where you put it, your map model is wrong, and its
actual position tells you the real mapping.

**The one-entry revert.** Wondering whether a surface is even on the path you
think? Put one known value through it and look. Settling "which renderer draws
this panel" cost one build; the static trace that was planned instead would
have cost hours.

## Compression: the trap that only shows on hardware

GBA's `LZ77UnCompVram` writes output in 16-bit halfwords, so a back-reference of
**displacement 1** reads a byte that has not been flushed yet.

- The symptom is **correct shapes, wrong colours**, or stripes of repeated
  colour where a run should be.
- Your own decoder round-trips it perfectly, so every check you own says the
  data is fine.
- The game's original blocks never contain disp=1. A naive greedy encoder emits
  hundreds.

Enforce `disp >= 2` and keep the comment explaining why, or someone will
optimise it away. Assert the constraint on the emitted stream — round-tripping
through your own decoder does **not** test it.

Related: recompressed blocks that grow no longer fit. Check the size, and
either relocate and repoint (find the pointer first — usually there is exactly
one) or simplify the art. Never truncate.

## The map you edit may not be the map the game uses

A data block often carries a map alongside its tiles, and the game may ignore
it and build its own. Symptoms:

- Moving your text in the map does not move it on screen.
- The text appears at one fixed position regardless of what you write.
- Editing "unused" tiles damages parts of the picture you never touched.

Read the map from VRAM and compare it against the map in the block. If the
VRAM map is **linear** (`0, 1, 2, 3 …`), the screen is a full-screen bitmap of
unique tiles and `tile = row * screen_cols + col`; every tile is on screen
exactly once, so in-place edits are safe and local. If the block's map is
deduplicated, its "free" tiles are not free at all — they are the same handful
of plain tiles reused dozens of times, and painting on one repaints all of
them.

Two more traps in the same family:

- **A row's stride is the map's width, not your strip's.** Deriving stride from
  the width of the region you are editing writes each row into a different part
  of the picture.
- **Layers share the character area.** A second background layer at a different
  bit depth indexes the same bytes, so a tile "free" according to one layer's
  map may be live in the other's. Check every layer's map, in bytes, not tiles.

## Separating lettering from artwork

To replace baked-in text you must know which pixels are text. Guessing by
position fails wherever art crosses the text.

**Use the palette.** Lettering usually has its own ramp, disjoint from the
scenery's. Prove it before relying on it: pick a region that contains only
scenery and confirm it uses none of the letter indices. In the case here, the
lettering was warm (r > b) and the sword and plate were not — and the
scenery-only band contained zero warm pixels, which made the classification
safe.

Then lift the letters out and fill each hole from the nearest non-letter pixel.
This preserves the art the letters sat on, which no amount of reconstructing
from neighbouring rows will do.

**Check the real extent first.** Text spans whatever rows it spans, not the
rows you assumed; cleaning two rows of a three-row word leaves an edge behind
that reads as a stray line under your replacement.

## Rendering the replacement

Legibility, palette ramps and fitting text to a slot belong to
**`rom-art-and-fonts`** — read that one for the pixels. Two notes that only
come up once you are replacing baked-in lettering:

- **Borrow texture, not colour.** To reproduce a mottled metallic look, take the
  original's *deviation from its row mean* and apply it to your own gradient.
  Sampling its absolute colours picks up its outline pixels too and the result
  goes muddy.
- **A drop shadow made of a second copy of the letters works for Latin and
  fails for Hangul**, which has open counters the copy shows through. Look at
  what the game itself does before inventing something.

## Measuring position from a screenshot

Scanning for "bright pixels" to locate your text picks up highlights in the
artwork and gives a number that is confidently wrong. Three moves in the wrong
direction came from one such reading. Measure from the tiles and the map, or
crop tightly and look.

## Build order

A graphics stage that edits the built ROM must run **before** whatever writes
the final ROM, or the main build silently reverts it and you simply get the old
picture back. Put the stage in the pipeline with a staleness check rather than
running it by hand.
