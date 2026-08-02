# Reading the real geometry off the original

Every number you guess here costs an iteration. The console has all of them.

## Sprite art: get the canvas from OAM

With the screen you want displayed, dump OAM and decode it. Each entry gives x,
y, shape/size, first tile index and palette number, which together hand you the
canvas dimensions and the tile grid for free.

A title screen decoded this way:

| sprites | what | position | palette | tiles |
|---|---|---|---|---|
| 1-5 | main logo | (4,48) 232x32 | 2 | 0-28 |
| 22-26 | drop shadow | (4,53) same shape | 2 | 128-156 |
| 18-21 | subtitle banner | (16,85) 208x32 | 3 | 416-440 |
| 6-13 | credit row | (4,148) 232x8 | 1 | 384-412 |

Two readings fall straight out of that table: the shadow is the *same art* 5px
lower in a flat colour (so edit both from one mask), and the credit row is 8px
tall (so it cannot carry Hangul — see `rendering.md`).

OBJ tile indices advance by 32 per row in 2D mapping, so index → `row*32 + col`.

## Find the compressed source by literal search

Compressed blocks store literals verbatim between flag bytes, so a distinctive
6-byte run from a VRAM tile usually survives contiguously in ROM. Search for
that first; it is far cheaper than decompressing candidates.

If it does not hit, scan for block headers with a plausible size field and
decompress each, checking for the tile. Filtering on `size % 32 == 0` and a sane
range cut 8M offsets to ~6.5K candidates in one case.

A static scan for *runs of pointers whose targets are one struct apart* also
finds glyph/tile tables you did not know existed:

```python
# >= 24 consecutive u32 ROM pointers spaced exactly one struct apart
```

## Read the ink colours, do not name them

"The dark one" and "not the background" are not colour choices. Decode the
palette to RGB and pick by luminance.

Choosing the subtitle ink as "any index that is not the fill" picked #F8E898
against a #F0D880 fill — a luminance difference of 14, i.e. an invisible
subtitle. The actual lettering index was #100818.

## Measure the writable band, and note what the original left unused

Histogram the indices per row inside the shape, away from the edges. The flat
field is where one index dominates.

Doing that on a ribbon showed the cream field ran y=3..18 — **16px** — while the
original English lettering occupied only y=7..15, nine pixels of it. The working
assumption had been 12px. Taking the band back to 15px was the single largest
legibility gain available, and it was free.

The original art using only part of its own field is common: English caps need
less height than the box provides. Do not treat the original text's extent as
the limit.

## Fixed-width UI slots: the English word is not the box

This trap is worth stating twice because it bit two separate waves of work.

If a per-entry width budget varies *by entry* — `Ellerie` 42px, `Oriana` 37px,
`Krynia` 39px — it is the width of the English word, not the width of the slot.
Names were reverted to English for "not fitting" a budget that was never the
box.

Measure a sibling label that already renders correctly, or read the box from the
running game. Eleven neighbours rendering at 24px is proof the column is at
least 24px; one English word's width proves nothing.

## Fitting the result back

Re-encoded blocks are usually smaller and drop in place with no repointing.
Check before writing, zero only the remainder of the original footprint, and
never spill past it. If a block would grow, repoint or simplify — do not
truncate. Make the packer exit with an error rather than overrun.
