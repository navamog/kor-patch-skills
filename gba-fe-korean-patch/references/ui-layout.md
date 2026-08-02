# Fixed-width UI, fonts, and what to leave in English

The engine's windows were laid out for a narrow variable-width ASCII font.
Korean syllables are roughly twice as wide as a 2-4 character English
abbreviation, so a faithful translation of every label produces overlap and
clipping — not a rendering bug, a layout budget problem.

## Leave short stat labels in English

`Atk` `Hit` `Crit` `Avo` `Rng` `Wt` `Mt` `Exp` `Str` `Mag` `Skill` `Spd` `Luck`
`Def` `Res` `Con` `Aid` `Mov` and friends sit in columns sized for 2-4 ASCII
characters. `사거리` overran the equipment panel; `경험치` overran the adjacent
column in the unit list. These read fine in English to any FE player, and
because the original text renders through the game's own font they also look
consistent with the rest of the UI.

Wider fields — `이름`, `클래스`, `최대`, `정렬:` — have room and should stay
Korean.

Implement this as an override file containing the English source text verbatim.
The build then encodes ASCII and the original renderer draws it.

**But do not infer the column width from the English word.** `Luck` is 16px and
`Move` 20px; that is the width of the word, not of the box. On the same screen
`기술` `속도` `수비` `마방` `체격` `마력` all render at 24px without clipping, so
the column is at least 24px and two-syllable Korean fits everywhere on it.

Two labels were reverted to English on that bad inference, which left a screen
with ten Korean labels and two English ones — worse than either choice made
consistently. Measure a **sibling label that already renders correctly** before
concluding a Korean label does not fit, and check the actual screen: eleven
neighbours at 24px is proof, one English word's width is not.

Consistency across a screen matters more than any single label. Decide the
policy for the whole column, not per entry.

**The alternative is one-syllable Korean.** A single Hangul glyph is *narrower*
than the 3-character narrow-font English it replaces, so 공 명 필 회 사 for
Atk/Hit/Crit/Avo/Rng fits where 공격/명중 does not — another project shipped
that and the columns line up. Choose per project: English reads more familiar to
an FE player, one-syllable Korean reads more consistent inside a fully
translated UI. What never works is the natural two-syllable word, which is wider
than the English and shoves the value into the next column. See the overflow
section of `line-width.md`.

## Drawing the Hangul glyph: outline, not shadow

Glyphs are 2bpp — four palette slots, no sub-pixel, no alpha. The ROM's own Latin
uses only 0 (transparent), 2 and 3. **Index 1 is unused and is not a spare
"half-strength" colour**: read palette RAM with a text window up and you find
whatever that window happens to use it for (purple, in one case). There is no way
to draw an edge lighter than one whole pixel.

**The colours of 2 and 3 are assigned per window.** The same glyph is white on a
blue status panel and black on a parchment dialogue box. Any rule of the form
"index 2 is the light one" is therefore wrong on some surface, and you find out
only on the screen you did not check. Three attempts failed that way here.

What works is a **full outline**: body in one index, a 1px rim of the other on all
eight neighbours. However the window resolves the palette, body and rim contrast,
so the text is legible everywhere and per-surface tuning stops.

Two traps in building that rim, both of which shipped visible defects:

**Ring the counters too.** Hangul counters — the holes in ㅇ ㅁ ㅂ ㅎ — are 2-3px
at 12px. Flood-filling from the border to protect them as "interior" leaves the
window background showing through them, and a blue hole punched in a white letter
reads as corruption, not as a counter. Fill them with the rim colour instead; the
syllable then reads as light strokes on a dark ground.

**Do not copy the Latin's asymmetric edge.** FE's Latin draws each stroke as the
pair (3, 2) — stroke plus one companion pixel. Reproducing that for Hangul gives a
directional shadow that closes counters on one side and haloes on the other.

If someone shows a screenshot of another project doing what you just called
impossible, believe the screenshot and re-read your own code. "12px is too small
for an outline" was wrong here; the algorithm was filling the counters.

## Rendering a pixel font at all

Pixel fonts must be rasterised on their own design grid. PIL's 1-bit mode drops
sub-pixel features — the tick on a vowel vanishes and the syllable becomes a
different letter. Render at an integer multiple (8x) and box-downsample at 50%
coverage.

Size matters more than the width budget suggests: below about 10 rows Hangul stops
resolving into 초성/중성/종성. An 8-row face was illegible on screen while fitting
its width budget comfortably.

## Class names: get the id list from the engine

Class names are scattered across the text banks and cannot be identified
reliably by pattern — "next entry looks like a description" collides with
character names and item names.

Read them from the class data table instead (0x0807110 in the observed ROM,
84-byte entries, ~119 slots; the name id is the first halfword). That is the
exact population the engine can display.

Bound the walk. Past the end of the table the same field yields item names
(Silver Blade, Javelin, Fire) which must **not** be reverted to English. Filter
to the class-name id block plus the hack's own additions, and stop when ids leave
that range.

## Glyph metrics

Advance width per glyph is what fills a column, and it is worth measuring rather
than assuming:

- Rendered at 12px with a 2px advance pad, a 4-syllable name came to 47px
  against a ~43px name column and lost its last syllable.
- Tightening the pad to 1px gave 43px — still marginal, and 3 of 4 test names
  clipped.
- Dropping to 11px with a 1px pad gave 38-39px and fit comfortably.

Reducing the pad to 0 would have kept 12px glyphs but made syllables touch, which
reads worse than the 1px size difference. When a column is tight, shrinking the
glyph beats removing the gap.

Names of 5+ syllables can still clip. Say so in the release notes rather than
pretending otherwise.

## Small text

Korean needs about 10px of height before syllables stop being mush. Below that,
neither Gulim nor Batang survives — verified on screen, not in preview, because
a preview at 4x zoom looks fine when the real thing is illegible.

So an 8px credit strip cannot carry `한글화`; use Latin there. This is a real
constraint of the medium, not a shortcut — check it on the actual display before
promising Korean in a small fixed-height area.

## Choosing a display face

For logo and title work a serif (명조) face carries the weight that matches FE's
ornate lettering; a plain sans bold looks thin beside it. Bold matters more than
family at small sizes — regular-weight serif strokes disappear below ~12px.

Resist stretching text to fill a canvas. Filling the full width squashed
syllables flat and read badly; capping the stretch (~1.2x) or leaving natural
proportions with margins looks far better.
