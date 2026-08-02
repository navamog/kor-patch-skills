# Making small text legible

Everything here was learned by shipping something illegible first.

## Never rasterise by downscaling

The instinct is to draw big and shrink for quality. It is backwards at these
sizes. Drawing a serif at 52px and resampling to a 12px band turns thin strokes
into grey that then thresholds away in patches — the result reads as noise, and
no amount of changing fonts fixes it.

Rasterise at the size the art actually is, and let the font's own hinting do the
work. Search for the pixel size whose raster is your target height:

```python
best = None
for px in range(target_h, target_h * 4):
    img = draw(text, px)
    h = img.getbbox()[3] - img.getbbox()[1]
    if best is None or abs(h - target_h) < abs(best[0] - target_h):
        best = (h, img)
    if h > target_h:
        break
```

Pixel fonts (Galmuri, Misaki, etc.) are the extreme case: they have exactly one
correct size and any resampling destroys them.

## Spend the palette as an anti-aliasing ramp

See SKILL.md for why. The implementation is small:

```python
# ramp ordered darkest -> lightest, taken from the ORIGINAL art's own indices
for y, x in pixels:
    v = coverage[x, y]          # 0..255 from a grayscale raster
    if v < 24:
        continue                # leave the background alone
    step = min(len(ramp) - 1, int((255 - v) * len(ramp) / 256))
    grid[y][x] = ramp[step]
```

For art that is *already* a gradient — a logo whose rows run dark-to-bright — you
need both axes at once: the row picks the base colour, coverage decides how far
that colour falls toward the outline.

```python
chain = [7, 6, 5, 4, 3, 8, 13, 11, 14, 1]   # bright -> dark -> outline
i = chain.index(vertical_ramp[y])
step = int((255 - v) * (len(chain) - i) / 256)
grid[y][x] = chain[min(len(chain) - 1, i + step)]
```

A hard 1-bit edge laid over a vertical ramp is what produces a stair-stepped rim.

**Cost:** anti-aliased art compresses worse. One logo block went from 1852 to
2268 bytes of a 2351-byte budget when the ramp went in. Check the fit and make
the packer refuse to overrun rather than truncate.

## Outline before fill, and ring the counters

For text that must survive on an unknown background, draw a full 1px outline on
all eight neighbours, then fill. Half-outlines (right and below only) copy a
drop shadow and close counters asymmetrically.

At 12px, Hangul counters — the holes in ㅇ ㅁ ㅂ ㅎ — are 2-3px. Leaving them
open lets the window background show through, and a coloured hole punched in a
letter reads as corruption, not as a counter. Fill them with the outline colour.

## Clipping bugs hide behind `getbbox()`

Two different "the text is cut off" bugs, two different causes, and both were
invisible until the raster's bounding box was printed:

- **Ascenders clipped.** Drawing with the baseline near the top of the canvas
  pushes ascenders off the image; the crop then silently returns flat-topped
  glyphs. The tell is `bbox[1] == 0` at *every* size tried. Put the baseline
  well down the canvas.
- **Descenders overflowing.** A fixed-height row measured 8px, but the raster
  was 9px once the `y` in the string was counted. Assert the raster height
  against the row height rather than trusting the nominal font size.

When something looks cut off, print the bbox before changing the size.

## Missing glyphs, and why `getbbox()` will not find them

Many Korean faces have no Hanja; MaruBuri and Nanum Myeongjo both render 靑月 as
tofu boxes. `font.getmask(ch).getbbox()` returns a box for tofu too — the box
*is* ink — so it reports success for a missing glyph.

Compare the raster against a codepoint guaranteed to be absent:

```python
tofu = render(font_path, '')      # private use area
present = render(font_path, ch) != tofu
```

To mix scripts, draw every run into **one** image with a shared pen so the
baseline stays common, then crop once:

```python
x = 0
for text, face in runs:
    f = font(face, px)
    d.text((x, baseline), text, font=f, fill=255, anchor='ls')
    x += int(d.textlength(text, font=f))
```

Pick faces from the same family class (both serif, both gothic) or the join
shows.

## Size floors

- Hangul stops resolving into 초성/중성/종성 below about 10 rows. An 8px face
  fit its width budget comfortably and was unreadable on screen.
- An 8px credit strip cannot carry Hangul at all; use Latin there.
- Hanja need more than Hangul. A 12px band could not carry 靑月 as 1-bit art —
  but the same 12px *could* once the palette ramp was in play. Check the
  technique before declaring a size impossible.
