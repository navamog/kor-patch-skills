---
name: gba-fe-korean-patch
description: >-
  Battle-tested pipeline for Korean (한글) fan-translation patches of GBA Fire
  Emblem ROM hacks (FE8U/FE7 engine — Vision Quest, Sacred Trilogy, Souls of the
  Forest, The Morrow's Golden Country and similar), covering the text table and
  its control tokens, glyph-bank and THUMB renderer hooks, per-surface line
  width budgets, build-time guards that stop broken lines from shipping,
  subagent translation waves with independent verification, fixed-width UI
  layout limits, rebuilding from a hack's published buildfiles, and LZ77
  title-logo graphics. Use this whenever the user is building or continuing a
  GBA FE 한글패치 — dumping or reinserting script, debugging garbled or missing
  dialogue, deciding what to leave in English, redrawing title or logo sprites,
  or packaging an xdelta/UPS release. Also use it when a GBA text patch shows
  symptoms this skill explains — a text box that opens blank or waits with no
  text, dialogue that seems to skip scenes, a syllable that garbles mid-line and
  then recovers, a literal token like [8022] printed on screen, labels
  overlapping their values, names clipped in a column, black smears over menu
  entries, chapter titles that never appear, translated text whose black and
  white come out reversed on menus but correct in the dialogue box, background
  showing through the inside of letters, or logo tiles with correct shapes
  but wrong colours.
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
| **Line width budgets — blank boxes, garbled runs, smeared menus** | `references/line-width.md` |
| **Glyph faces — text inverted on menus, mushy, background showing inside letters** | `references/glyph-faces.md` |
| Fixed-width UI, fonts, what to leave in English | `references/ui-layout.md` |
| Hack ships its buildfiles: rebuild-from-source workflow | `references/source-rebuild.md` |
| Title logo / sprite graphics, LZ77 | `references/graphics.md` |

Two routes into this domain, and they fail differently. **Binary hacking** a
compiled ROM is `text-pipeline.md`. **Rebuilding from published buildfiles** is
`source-rebuild.md` — there the script is already in readable files, and the
hard part is discovering which text you were never handed.

`scripts/` holds working versions of the three checkers that caught the most:
line width, entry/code damage, and ids the build never overrides. Adapt the
constants at the top; see `scripts/README.md`.

Two sibling skills carry the parts that are not FE-specific: **rom-art-and-fonts**
for rasterising glyphs, palette-ramp anti-aliasing, measuring a UI box off the
original art, and the debugging discipline for a stalled symptom; and
**rom-graphics-verification** for compression traps and proving an edit landed.
Reach for the first whenever text is illegible rather than merely wrong.

## The one thing that matters most

**Every claim about the patch must come from the running game, not from your
tooling.** This project's worst bugs all passed the tooling and failed on
screen:

- 42 pages of the opening scene were missing for weeks; the build reported
  success because that one string bypassed the guard.
- 452 strings rendered a literal `[8022]` because the encoder and the guard
  shared a regex that couldn't see the token — so both agreed it was fine.
- A logo rewrite produced correct tiles in ROM and garbage in VRAM.
- 815 lines were too wide for their box, so the engine dropped them. The text
  was perfect Korean and the ROM bytes matched the source exactly; the boxes
  were simply blank on screen.
- A glyph face was redesigned four times from screenshots, each round fixing one
  surface and breaking another, because the ink colour was being inferred from
  sampled pixels. The palettes differ per window; the ROM's own glyph table said
  which index was the letter, and reading it settled in one run what four builds
  could not.

When you finish a stage, boot the ROM and look. When a symptom appears, prefer a
**control experiment** over reasoning: change one thing to a known-good value and
see whether the symptom survives. That is what separated "my art is wrong" from
"my encoder is wrong" in a case where both were plausible and the ROM data
looked perfect.

## Working order

1. **Establish the text population.** Dump the table, tokenize control codes,
   and record the id ranges. Confirm you dumped everything — see the coverage
   trap in `references/text-pipeline.md`, and if the hack ships buildfiles, the
   three ways the population hides in `references/source-rebuild.md`.
2. **Build the renderer** (glyph bank + hooks) and get one Korean string on
   screen before translating anything at scale. Count the hooks — entry points
   that walk a string one byte at a time will not render UTF-8. **Decode the
   ROM's own glyphs before drawing yours**: which 2bpp index is the letter,
   which is the shadow or outline, and whether counters are filled. The engine
   ships more than one font and they use opposite rules, so a bank drawn to the
   wrong one comes out colour-inverted on half the game. `references/glyph-faces.md`
   — this is the single largest time sink in the domain and it is a twenty-line
   script to avoid.
3. **Add guards before the first wave**, not after. A guard that rejects a
   broken line is worth more than any amount of later auditing, and retrofitting
   guards means re-verifying everything already written. **Include the width
   check** — no token or entry guard can see an over-wide line, and fixing width
   afterwards means rewriting prose you already approved.
4. **Translate in waves**, verifying each output yourself. Put the width budget
   in the dispatch prompt so agents write to it the first time.
5. **Decide what stays English** — this is a real design decision, not a
   failure. See `references/ui-layout.md`.
6. **Graphics last**, since they sit outside the text pipeline entirely.
7. **Package by applying the patch you are about to ship and hashing the
   result** — not the build you happen to have on disk. Only that proves the
   patch reproduces the ROM the README describes. Round-trip any compressor the
   same way before its output reaches the console.

A release README should carry the base-ROM hash, the patch hash and the applied
result hash, all three taken from the shipped files, plus the known-limitations
table with a *reason* per row so intentional English is not read as unfinished
work.

## Measurement discipline

Progress numbers lie in specific, recurring ways. Four rules that were each
learned by shipping a wrong number:

**Measure against the whole population, not the part you happen to be
iterating on.** A chunk-based progress script reported "0 remaining" while 254
system-space strings had never been handed to anyone — including menu commands
the player sees constantly. Keep a coverage check that walks the entire dump.

**Resolve overwrite order the way the build does.** When later files supersede
earlier ones for the same id, per-file counts keep reporting problems that a
later file already fixed. Compute the effective mapping first, then judge.

**A repair file that loses the override race still passes verification.** Once
the verifier judges the *effective* value (previous rule), a repair file whose
name sorts before the file it meant to override is silently discarded — and
reported `OK`, because the verifier checked the winning text, not the file's own.
Here `zzfix_register` lost to `zzfix_width` on `r` < `w`. Guard it: if an
override file ships none of its entries, it overrides nothing, and that is
always a bug. Note the asymmetry — a *base* file being fully superseded is
normal and must not warn, or the check drowns in false alarms.

**Never build while a translation wave is writing.** The build reads every
translation file; agents rewrite them in place. A build launched mid-wave
reported one verifier failure and nine over-wide lines, and re-running the same
command seconds later — no edit in between — gave zero and zero. The tell was
the distinct-syllable count changing between the two runs: the input moved under
the build. Had those numbers been believed, hours would have gone to nine width
bugs that never existed. Quiesce the waves, then measure.

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
