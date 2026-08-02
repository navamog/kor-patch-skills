# Title logo and sprite graphics

The title logo is not text. It is OBJ sprite tiles, LZ77-compressed in ROM, and
nothing in the text pipeline touches it.

> Rendering the *lettering* — rasterising at tiny sizes, using the palette's own
> ramp as anti-aliasing, measuring the writable band off the original — lives in
> **rom-art-and-fonts**. This file covers locating and refitting the blocks.
>
> One consequence worth repeating here: anti-aliased art compresses worse.
> Adding a palette ramp took a logo block from 1852 to 2268 bytes of a 2351-byte
> budget. Check the fit, and make the packer error out rather than overrun.

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

A credit fits comfortably in a quiet corner of the **background**, which is a
different job from the sprite logo — see the next section before starting, and
`rom-graphics-verification` for the structural traps in general.

## The background is not the logo, and its map is not in the block

The title backdrop is BG, LZ77-compressed, and it behaves nothing like the OBJ
logo. Three facts, each of which cost a broken build when assumed instead of
read:

**The map the game uses is not the map inside the block.** The observed block
carries a *deduplicated* map, and the game builds its own **linear** one in VRAM
(`0, 1, 2, 3 …`), so the screen is a 30x20 grid of unique tiles and
`tile = row * 30 + col`. Consequences:

- Writing map entries into the block does nothing — the text stays wherever its
  tile lands under the linear map, no matter which column you ask for. Tile 39
  is row 1, column 9, i.e. x=72, and it appeared at x=72 every single time.
- "Find a free tile and repoint" is the wrong plan twice over: the map you would
  search is the wrong one, and under the linear map there are no free tiles at
  all — every tile is on screen exactly once.
- The right plan is the simple one: compute the tiles from `row * 30 + col`,
  read them, composite onto them, write them back, and **never touch the map**.

**Read the map from VRAM to find out which case you are in.** Linear means
in-place edits are safe and local. Deduplicated means the plain corner tiles are
reused 11 to 38 times and painting one repaints all of them.

**BG index 0 is not transparent when nothing is behind it.** Blanking the
non-glyph pixels of a BG strip cut a black band across the artwork.

## Replacing baked-in lettering (the subtitle band)

The subtitle strip holds the plate, the sword crossing it, and the lettering in
the same pixels; there is no clean copy underneath. Reconstructing it from the
rows above and below produced stripes, and blanking it produced a black band.

What works is separating by colour. The lettering has its own ramp: in the
observed art every **warm** index (r > b) is lettering, and the scenery-only
band (x >= 200) contains **zero** warm pixels — check that before relying on it.
Lift the warm pixels and fill each hole from the nearest non-warm pixel; the
plate and the sword survive intact.

Measure how far the lettering really extends first. It spanned screen rows
10..12, and cleaning only rows 10..11 left its bottom edge behind as a red line
under the Korean.

## Before blaming your art, run the null control

Re-encode the **unmodified** block with your compressor and patch that in. If
the screen is still wrong, the compressor is at fault; if it is perfect, the
compressor is exonerated and the remaining suspects are your art and your map
model. One run, and it retires the most expensive branch of the search. In this
project it is what finally separated "my encoder is broken" from "my map model
is wrong" after roughly a dozen builds spent on the wrong one.

Corollary: **a check built from the same model as the edit proves nothing.** An
offline verifier reported "0 pixels changed outside the intended box" for a
build that visibly punched black holes across the screen, because both the
writer and the checker read the block's map and the hardware used another.
