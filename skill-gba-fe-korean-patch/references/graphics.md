# Title logo and sprite graphics

The title logo is not text. It is OBJ sprite tiles, LZ77-compressed in ROM, and
nothing in the text pipeline touches it.

## Find the real structure from the running game

Guessing the layout wastes time; the console already knows it. With the title
screen up:

1. Dump VRAM, OAM and palette RAM.
2. Reconstruct each BG layer from its control register (char base, screen base,
   bpp) — this usually reveals the backdrop, not the logo.
3. Reconstruct the OBJ layer from OAM. That is where the logo lives.
4. Read each logo sprite's x, y, size, first tile index and palette number
   straight out of OAM. That gives you the canvas dimensions and the tile grid.

In the observed ROM: the main logo is OBJ palette 2 at screen (4,48), 232x32px,
with a second set of sprites 5px lower holding a flat black silhouette — that
offset pair is what produces the drop shadow. The subtitle banner is palette 3 at
(16,85), 208x32px. OBJ tile indices advance by 32 per row (2D mapping), so a tile
index maps to `row*32 + col` in the sheet.

## Find the compressed source

Take a distinctive tile from VRAM and scan the ROM for an LZ77 block (header byte
0x10) whose decompressed output contains it. Decompress, render the block as a
tile sheet, and confirm visually before editing anything.

## Match the game's own colour ramp

Read the indices the original art uses rather than inventing a palette. The logo
used index 1 for the outline, 7/5/3 as a bright-to-gold face ramp, and 13/14 for
the red-brown underside; the shadow layer used a single flat index. Reusing those
indices means the game's own palette animation continues to work on your art.

For a banner or ribbon, rewrite only the flat text strip and leave the folds
alone — detect the writable run by which columns use only the flat colours.

## The LZ77 trap: never emit displacement 1

**This is the single most expensive bug in this domain.** GBA's
`LZ77UnCompVram` writes its output in 16-bit halfwords, so a back-reference of
displacement 1 reads a byte that has not been flushed to VRAM yet.

The symptom is distinctive and misleading: **shapes come out correct, colours
come out wrong.** It looks like a palette problem or an art problem, and the ROM
data reads back perfectly, so every check you run says the data is fine.

The game's own blocks obey the rule — the observed logo block has a minimum
displacement of exactly 2 and no disp=1 anywhere. A naive greedy encoder emitted
140 of them.

Enforce `disp >= 2` in the compressor and keep a comment explaining why, because
the constraint looks arbitrary and someone will "optimise" it away.

**How to diagnose it if you hit it anyway:** re-encode the *unmodified original
data* and patch that in. If the display still breaks, the encoder is at fault,
not your art. That control experiment settles in one run what hours of pixel
comparison will not.

## Fitting the result back

Re-encoded blocks are often smaller than the originals, so they drop in place
with no repointing. Check before writing, and zero only the remainder of the
original block's footprint — never spill past it.

If a rewritten block would be larger, do not truncate; repoint or simplify the
art.

## Build order

A post-build graphics patch edits the built ROM directly, so the main build will
wipe it if run afterwards. The order is: build → graphics patch → make patch →
package. Write that down where the next person will see it, because the failure
is silent — you simply get the old logo back.

## Adding a credit line

You cannot add new sprites without touching code, so work with the sprites that
already exist. A credit line usually means rewriting an existing row's tiles.

Check the row's real height first: a one-tile row is 8px, and Korean does not
render legibly at that size (see `ui-layout.md`). Measure the existing text's
extent — if it already spans most of the row, redraw the whole row in a narrower
face to make room rather than trying to append into a margin that isn't there.
