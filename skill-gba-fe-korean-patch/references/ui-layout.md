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
