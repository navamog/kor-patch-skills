# -*- coding: utf-8 -*-
"""Redraw the FIRE EMBLEM wordmark as 파이어 엠블렘, plus a KOR by NaVaMo credit.

The logo is not in the buildfiles -- it is vanilla FE8 art, an LZ77 stream at
ROM 0xAAC5AC that expands to 8192 bytes: 256 4bpp tiles laid out 32 across,
i.e. a 256x64 sheet. Found by decompressing every LZ77 stream in the clean ROM
and matching against the tiles the title screen had in sprite VRAM.

The letters are filled with a per-row gradient -- each scanline of the wordmark
has its own palette index -- and outlined. This script samples that ramp from
the original so the Korean is shaded identically, then re-emits the sheet.

Outputs logo.kr.png (for eyeballing) and logo.kr.dmp (LZ77, ready to insert).

Run from repo root:  python TMGC_Buildfiles/KoreanPatch/gen_logo.py
"""
import collections
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
CLEAN = os.path.join(ROOT, 'FE8_clean.gba')
OUT_PNG = os.path.join(HERE, 'logo.kr.png')
OUT_REF = os.path.join(HERE, 'logo.orig.png')

LOGO_ROM = 0xAAC5AC
W, H = 256, 64

TITLE = '파이어 엠블렘'
CREDIT = 'KOR by NaVaMo'
TITLE_FONT = r"C:\Windows\Fonts\malgunbd.ttf"    # heavy, holds up at logo size
CREDIT_FONT = r"C:\Windows\Fonts\malgunbd.ttf"

BAND_TOP, BAND_BOT = 2, 30      # the wordmark's rows
OUTLINE = 8                      # dark edge index used by the original
TRANSPARENT = 0


def unlz(d, i):
    size = d[i + 1] | (d[i + 2] << 8) | (d[i + 3] << 16)
    out = bytearray()
    p = i + 4
    while len(out) < size:
        f = d[p]; p += 1
        for b in range(8):
            if len(out) >= size:
                break
            if f & (0x80 >> b):
                hi, lo = d[p], d[p + 1]; p += 2
                ln = (hi >> 4) + 3
                disp = ((hi & 0x0F) << 8 | lo) + 1
                st = len(out) - disp
                for k in range(ln):
                    out.append(out[st + k])
            else:
                out.append(d[p]); p += 1
    return bytes(out)


def tiles_to_px(tiles):
    px = [[0] * W for _ in range(H)]
    for t in range(W * H // 64):
        tx, ty = (t % (W // 8)) * 8, (t // (W // 8)) * 8
        for y in range(8):
            for x in range(0, 8, 2):
                b = tiles[t * 32 + y * 4 + x // 2]
                px[ty + y][tx + x] = b & 0x0F
                px[ty + y][tx + x + 1] = b >> 4
    return px


def px_to_tiles(px):
    out = bytearray()
    for t in range(W * H // 64):
        tx, ty = (t % (W // 8)) * 8, (t // (W // 8)) * 8
        for y in range(8):
            for x in range(0, 8, 2):
                out.append((px[ty + y][tx + x] & 0x0F) | ((px[ty + y][tx + x + 1] & 0x0F) << 4))
    return bytes(out)


def main():
    rom = open(CLEAN, 'rb').read()
    px = tiles_to_px(unlz(rom, LOGO_ROM))

    # per-row fill colour of the original wordmark
    ramp = {}
    for y in range(BAND_TOP, BAND_BOT):
        c = collections.Counter(px[y][x] for x in range(8, 224))
        c.pop(TRANSPARENT, None)
        ramp[y] = c.most_common(1)[0][0] if c else TRANSPARENT
    print('sampled gradient:', ' '.join('%X' % ramp[y] for y in sorted(ramp)))

    # keep a reference render of the untouched sheet
    ref = Image.new('P', (W, H))
    ref.putpalette([(i * 17) % 256 for i in range(768)])
    for y in range(H):
        for x in range(W):
            ref.putpixel((x, y), px[y][x])
    ref.save(OUT_REF)

    # The sheet holds the wordmark twice: the gold one on top and, below it, a
    # flat copy of the same shape that the title screen sweeps its gleam across.
    # Both have to become Korean or the gleam traces the old letters.
    SHINE = 10
    # Clear the whole sheet except the TM mark. Stopping at y=60 the first time
    # left a 198px bar on row 60 that showed up on screen as a dark rule under
    # the wordmark.
    for y in range(0, H):
        for x in range(0, 232):
            px[y][x] = TRANSPARENT

    def stamp(text, font_path, size, cy, x_center, fill_ramp, outline=True, flat=None):
        f = ImageFont.truetype(font_path, size)
        bb = f.getbbox(text)
        tmp = Image.new('L', (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), 0)
        ImageDraw.Draw(tmp).text((4 - bb[0], 4 - bb[1]), text, fill=255, font=f)
        tmp = tmp.crop(tmp.getbbox())
        ox = x_center - tmp.width // 2
        oy = cy - tmp.height // 2
        m = [[tmp.getpixel((x, y)) >= 128 for x in range(tmp.width)] for y in range(tmp.height)]
        if outline:
            for y in range(tmp.height):
                for x in range(tmp.width):
                    if not m[y][x]:
                        continue
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            X, Y = ox + x + dx, oy + y + dy
                            if 0 <= X < W and 0 <= Y < H:
                                px[Y][X] = OUTLINE
        for y in range(tmp.height):
            for x in range(tmp.width):
                if not m[y][x]:
                    continue
                X, Y = ox + x, oy + y
                if 0 <= X < W and 0 <= Y < H:
                    px[Y][X] = flat if flat is not None else fill_ramp.get(Y, OUTLINE)

    # keep the wordmark inside the sheet: shrink until it fits with a margin
    for size in range(30, 15, -1):
        f = ImageFont.truetype(TITLE_FONT, size)
        bb = f.getbbox(TITLE)
        if bb[2] - bb[0] + 4 <= 214:
            break
    print('title size %d -> %dpx wide' % (size, bb[2] - bb[0]))
    stamp(TITLE, TITLE_FONT, size, 16, 116, ramp)                      # gold
    stamp(TITLE, TITLE_FONT, size, 44, 116, ramp, outline=False, flat=SHINE)

    # Png2Dmp derives indices from the palette, so every entry must be a
    # distinct colour. An all-black palette collapses the whole sheet to index 0
    # and the logo vanishes -- which is exactly what happened the first time.
    DISTINCT = []
    for i in range(16):
        DISTINCT += [i * 16 + 8, (i * 37) % 256, (i * 91) % 256]
    out = Image.new('P', (W, H))
    out.putpalette(DISTINCT + [0] * (768 - len(DISTINCT)))
    for y in range(H):
        for x in range(W):
            out.putpixel((x, y), px[y][x])
    out.save(OUT_PNG)
    print('wrote', os.path.basename(OUT_PNG))

    raw = px_to_tiles(px)
    open(os.path.join(HERE, 'logo.kr.bin'), 'wb').write(raw)
    png2dmp = os.path.join(ROOT, 'EventAssembler', 'Tools', 'Png2Dmp.exe')
    dmp = os.path.join(HERE, 'logo.kr.dmp')
    subprocess.run([png2dmp, OUT_PNG, '--lz77', '-o', dmp], check=True)
    n = os.path.getsize(dmp)
    ORIG_SLOT = 2351          # the vanilla stream at 0xAAC5AC is this long
    print('wrote logo.kr.dmp (%d bytes, slot %d, fits: %s)' % (n, ORIG_SLOT, n <= ORIG_SLOT))
    if n > ORIG_SLOT:
        raise SystemExit('ERROR: compressed logo does not fit the original slot')
    # round-trip: what we ship must decompress back to the pixels we drew
    back = unlz(open(dmp, 'rb').read(), 0)
    if back != raw:
        bad = next((i for i, (a, b) in enumerate(zip(back, raw)) if a != b), -1)
        raise SystemExit('ERROR: round-trip mismatch at byte %d (%d vs %d bytes)'
                         % (bad, len(back), len(raw)))
    print('round-trip OK: %d bytes decompress back to the drawn sheet' % len(back))


if __name__ == '__main__':
    main()
