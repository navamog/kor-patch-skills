---
name: gba-fe-korean-patch
description: >-
  Battle-tested pipeline for Korean (한글) fan-translation patches of GBA Fire
  Emblem ROM hacks (FE8U/FE7 engine — Vision Quest, Sacred Trilogy, Souls of the
  Forest and similar), covering the text table and its control tokens,
  glyph-bank and THUMB renderer hooks, build-time guards that stop broken lines
  from shipping, subagent translation waves with independent verification,
  fixed-width UI layout limits, and LZ77 title-logo graphics. Use this whenever
  the user is building or continuing a GBA FE 한글패치 — dumping or reinserting
  script, debugging garbled or missing dialogue, deciding what to leave in
  English, redrawing title or logo sprites, or packaging an xdelta release. Also
  use it when a GBA text patch shows symptoms this skill explains — dialogue
  that skips ahead, a literal token like [8022] printed on screen, labels
  overlapping their values, names clipped in a column, or logo tiles with
  correct shapes but wrong colours.
---

# GBA Fire Emblem 한글패치

This is the accumulated, verified-in-emulator know-how from shipping a full FE8U
romhack translation. It complements the general `create-kr-patch` methodology:
that one tells you *what judgments to make*, this one tells you *what this engine
actually does and where it bites*.

Read `references/` files when you reach the matching stage — each is short and
self-contained.

| Stage | File |
|---|---|
| Text table, control tokens, encoder, build guards | `references/text-pipeline.md` |
| Translation waves, verification, terminology | `references/waves-and-verification.md` |
| Fixed-width UI, fonts, what to leave in English | `references/ui-layout.md` |
| Title logo / sprite graphics, LZ77 | `references/graphics.md` |

## The one thing that matters most

**Every claim about the patch must come from the running game, not from your
tooling.** This project's worst bugs all passed the tooling and failed on
screen:

- 42 pages of the opening scene were missing for weeks; the build reported
  success because that one string bypassed the guard.
- 452 strings rendered a literal `[8022]` because the encoder and the guard
  shared a regex that couldn't see the token — so both agreed it was fine.
- A logo rewrite produced correct tiles in ROM and garbage in VRAM.

When you finish a stage, boot the ROM and look. When a symptom appears, prefer a
**control experiment** over reasoning: change one thing to a known-good value and
see whether the symptom survives. That is what separated "my art is wrong" from
"my encoder is wrong" in a case where both were plausible and the ROM data
looked perfect.

## Working order

1. **Establish the text population.** Dump the table, tokenize control codes,
   and record the id ranges. Confirm you dumped everything — see the coverage
   trap in `references/text-pipeline.md`.
2. **Build the renderer** (glyph bank + hooks) and get one Korean string on
   screen before translating anything at scale.
3. **Add guards before the first wave**, not after. A guard that rejects a
   broken line is worth more than any amount of later auditing, and retrofitting
   guards means re-verifying everything already written.
4. **Translate in waves**, verifying each output yourself.
5. **Decide what stays English** — this is a real design decision, not a
   failure. See `references/ui-layout.md`.
6. **Graphics last**, since they sit outside the text pipeline entirely.
7. **Package with hashes computed from the actual build**, so the README can't
   drift from what ships.

## Measurement discipline

Progress numbers lie in specific, recurring ways. Three rules that were each
learned by shipping a wrong number:

**Measure against the whole population, not the part you happen to be
iterating on.** A chunk-based progress script reported "0 remaining" while 254
system-space strings had never been handed to anyone — including menu commands
the player sees constantly. Keep a coverage check that walks the entire dump.

**Resolve overwrite order the way the build does.** When later files supersede
earlier ones for the same id, per-file counts keep reporting problems that a
later file already fixed. Compute the effective mapping first, then judge.

**Make the build print the numbers every time.** A metric you have to remember
to run is a metric you will forget to run. Coverage, guard rejections, and any
"kept English on purpose" count belong in the build's own output.

## When something looks wrong on screen

Work from the pixels backwards, and check each hop rather than guessing:

1. Is the string even reaching the ROM? Read the record back out of the built
   ROM at its table pointer and decode it.
2. Is the ROM data reaching VRAM intact? Dump VRAM and compare.
3. Is it a palette or an animation phase? Capture several frames — a title logo
   mid-fade looks exactly like corruption.
4. Is the thing you're looking at even text? Menus, prompts and logos are often
   pre-rendered graphics or tile-renderer output, and no amount of translation
   work will touch them.

Rendering paths differ inside one game. Dialogue, menus, the map HUD, chapter
headers and battle name plates can each take a different route, and a fix that
works in one may not apply to another.
