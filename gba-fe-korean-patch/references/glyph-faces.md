# Drawing the glyphs: read the ROM's font before you draw yours

This file exists because a full working day was spent guessing what a legible
glyph looks like on this engine, when the answer was sitting in the ROM and took
twenty lines of Python to read. Do that first. Everything else here follows from
it.

## Step one, always: decode the ROM's own glyphs

The engine's font is a table of `Glyph { u32 next, u8 sjisByte, u8 width,
u16 pad, u32 bitmap[16] }` — the same 0x48-byte layout a Korean bank uses, 2bpp,
one u32 per row, two bits per pixel from the low end. The table's address is in
the live font object; see "finding the tables" below. Print a few Latin glyphs
as characters and the design rules are immediately visible:

```python
p = struct.unpack_from("<I", rom, TABLE + 4*ord('o'))[0]
off = p & 0x1FFFFFF
for y in range(16):
    row = struct.unpack_from("<I", rom, off + 8 + 4*y)[0]
    print("".join(".123"[(row >> (2*x)) & 3] for x in range(16)))
```

Read off that dump: which index is the letter, which is the shadow or outline,
whether the outline surrounds the glyph or trails it, and whether enclosed
counters are filled or left transparent. Those four facts are the entire design.
Guessing any of them costs a build-and-verify cycle each.

## FE8U ships two fonts and they use opposite rules

This is the trap that burned the most time. There is not one font. In the
observed ROM:

| | glyph table | letter | second index | where |
|---|---|---|---|---|
| **UI / menu face** | `0x0858C7EC` | index **2** | index **3**, outline on all 8 neighbours, **counters filled** | unit list, status screen, map HUD, action menu, battle forecast, item/weapon boxes |
| **Dialogue face** | `0x0858F6F4` | index **3** | index **2**, shadow down-and-right only, **no outline** | dialogue box, Help window, confirm prompts — the parchment windows |

```
UI face 'o'            dialogue face 'o'
  ..33                   .332
 .3223                  32232
323323                  32.32
323323                  32.32
 .3223                  32232
  ..33                   .332
```

The two are colour-inverted with respect to each other, and **each window's
palette is authored for whichever font draws into it**. So a Korean bank built
to the dialogue rule renders correctly in the dialogue box and comes out with
its black and white exchanged on every menu: the letter takes the outline
colour and the shadow takes the letter colour. That is exactly what "the UI
font is inverted" looks like, and no amount of tweaking one bank fixes it.

## Do not pick the index by sampling screen colours

The reflex is to screenshot a surface, read the pixel values, and conclude
"index 3 is the dark one here." It is true, per surface, and useless: the
palettes differ per window, so index 3 samples as black in the dialogue box and
as white on the map HUD. Sampling produces a different answer on each screen and
sends you swapping the pair back and forth, breaking whichever surface you are
not currently looking at. Measured luminances from one such round trip:

```
                  parchment dialogue box     blue panel / menu / HUD
  index 1         189  (ground is ~200)      127  (ground is ~118)
  index 2         141                        248
  index 3           8                          8
```

Index 1 is the ground colour on both — it is not an ink anywhere, which is worth
knowing because it looks like a free third tone and is not.

The ROM's glyph dump settles in one shot what sampling cannot settle at all.

## Two banks, selected by the active glyph table

Since the two faces disagree, ship two banks and let the hook choose. The
discriminator is free: the engine has already loaded the glyph table pointer for
the surface it is drawing.

Find the tables from the running game — pause on any text and read the font
pointer (`0x02028E70` here), dereference it, and read `+4`:

```
font object  = [0x02028E70]        # 0x030000F0 for dialogue, 0x02028E58 for UI
glyph table  = [font + 4]          # 0x0858F6F4 vs 0x0858C7EC
draw routine = [font + 8]
```

Then branch inside the character→glyph lookup, six instructions:

```asm
    ldr r1, kl_bank          ; dialogue bank
    ldr r2, kl_font          ; 0x02028E70
    ldr r2, [r2]
    ldr r2, [r2, #4]         ; active glyph table
    ldr r3, kl_uitab         ; 0x0858C7EC
    cmp r2, r3
    bne kl_bankok
    ldr r1, kl_uibank
kl_bankok:
    adds r1, r1, r0
```

Default to the dialogue bank: an unlisted window is far more likely to be prose
than a menu.

Two constraints make this safe. **Both banks must carry identical advances**, so
the width-measuring entry points (string length, character length) do not care
which bank they land in — they may be called with a stale font pointer. And
check the ROM size: a second full EUC-KR bank is ~0.6 MB, which is fine against
the 32 MB ceiling but is not free.

## Rasterise from the font's embedded bitmaps, not from its outlines

Supersampling the TrueType outline and thresholding looks like the higher
quality route and is not. A Hangul stroke at 11px is ~1.2px wide, so whenever
one straddles two output rows its coverage splits and both rows fall under the
threshold. Observed: 글 lost the top bar of its ㄱ, 한 lost its ㅇ entirely, and
every threshold that recovered them fused something else.

Korean UI fonts ship hand-hinted bitmaps at exactly these sizes, and they place
every stroke on the pixel grid. In PIL, `ImageDraw.fontmode = "1"` selects them:

```python
d = ImageDraw.Draw(img)
d.fontmode = "1"                       # embedded bitmap, not the outline
d.text((0, YOFF), ch, fill=255, font=ImageFont.truetype("gulim.ttc", 11))
```

The result is a clean pixel font with open counters and correct shapes at 11,
12 and 13px. This is the same principle as the sibling **rom-art-and-fonts**
note that a pixel font at its native size beats anti-aliasing — it just has more
force for Hangul, where a lost stroke changes the letter rather than blurring it.

## Fill the counters on an outlined face

An outline that stops at the glyph's outer contour and protects the enclosed
holes leaves the window background showing *inside* the letter, and the glyph
loses its edge against whatever is behind the window. Players describe this as
"배경색이 글자 안에 들어가 있다".

The ROM does not do that — the counter of its 'o' is outline-coloured, not
transparent. Dilate on all eight neighbours with no exemptions and match it.

Note the asymmetry with the *dialogue* face, which has no outline at all: there,
growing one on every neighbour is actively wrong. It fills the 1-2px gaps
between Hangul's parallel strokes — the bars of ㅌ ㄹ, the counters of ㅇ ㅂ ㅎ —
and turns 을 은 이 미 한 into blobs, and on any surface where the second index
is the light colour it wraps every letter in a halo that reads as grey mush.
Outline the outlined face; shadow the shadowed one.

## Keep the advance fixed when you change the face

Advance width and glyph shading are independent, and only one of them invalidates
work. Line-width budgets, column fits and the translations written against them
all depend on the advance. Changing the face while holding the advance byte
identical to the previous release means every validated line stays valid; a
1px average change means re-auditing the whole script.

Measure it before building, not after:

```
mean advance   v0.9.6 = 9.61   new = 9.61      # 슈토르히 39px vs a ~43px column
```

## Iterate offline, and change one thing

Every regression in this area came from changing size, weight, condensation and
palette indices in the same build and then judging the result on a screenshot.
Print the glyph grid as characters in the terminal — it is faster than the
emulator, it is unambiguous, and it shows exactly what the ROM dump shows, so
the two can be compared directly.

Practical note for verification: FE cutscenes skip with **Start**. Tapping A
through a 150-page opening to reach the menu you actually want to inspect wastes
minutes per iteration.
