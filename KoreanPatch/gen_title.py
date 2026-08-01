# -*- coding: utf-8 -*-
"""Redraw the title-screen subtitle banner in Korean.

Graphics/newGame Title.png (256x40, 16-colour) holds the scroll banner with
"The Morrow's Golden Country", the copyright line and "Press START". Inside
the banner the fill is palette index 2 and the text is index 15 and nothing
else, so the English can be cleared exactly and Korean drawn in its place.

The .dmp the installer includes is LZ77-compressed by Png2Dmp; running that
tool on the untouched PNG reproduces the shipped .dmp byte-for-byte, so
regenerating it here is safe.

Run from the repo root:  python TMGC_Buildfiles/KoreanPatch/gen_title.py
"""
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GFX = os.path.join(ROOT, 'Graphics')
PNG = os.path.join(GFX, 'newGame Title.png')
DMP = os.path.join(GFX, 'newGame Title.dmp')
ORIG = os.path.join(os.path.dirname(__file__), 'newGame Title.orig.png')
PNG2DMP = os.path.join(ROOT, 'EventAssembler', 'Tools', 'Png2Dmp.exe')

TEXT = '모로우의 황금향'
FONT = r"C:\Windows\Fonts\HANBatangB.ttf"   # bold serif; the regular weight read thin
CREDIT_FONT = r"C:\Windows\Fonts\malgunbd.ttf"
SIZE = 17
TRACKING = 0
WORD_SPACE = 4

FILL, INK = 2, 15
# flat interior of the scroll; the curls and edges sit outside this
BOX = (30, 11, 182, 27)          # x0, y0, x1, y1  (exclusive ends)
CENTER = (103, 18)               # where the text is centred


def render(text, font, size, tracking, word_space):
    f = ImageFont.truetype(font, size)
    parts = []
    for ch in text:
        if ch == ' ':
            parts.append((None, word_space))
        else:
            bb = f.getbbox(ch)
            parts.append((ch, bb[2] - bb[0]))
    total = sum(w for _, w in parts) + tracking * (len(parts) - 1)
    img = Image.new('L', (total + size * 2, size * 2), 0)
    d = ImageDraw.Draw(img)
    x = 0
    for ch, w in parts:
        if ch:
            bb = f.getbbox(ch)
            d.text((x - bb[0], 0), ch, fill=255, font=f)
        x += w + tracking
    return img.crop(img.getbbox())


def main():
    if not os.path.exists(ORIG):
        shutil.copy(PNG, ORIG)          # keep the English original
        print('saved original ->', os.path.basename(ORIG))

    im = Image.open(ORIG)
    px = im.load()

    x0, y0, x1, y1 = BOX
    cleared = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            if px[x, y] == INK:
                px[x, y] = FILL
                cleared += 1
    print('cleared %d english pixels' % cleared)

    glyphs = render(TEXT, FONT, SIZE, TRACKING, WORD_SPACE)
    ox = CENTER[0] - glyphs.width // 2
    oy = CENTER[1] - glyphs.height // 2
    if ox < x0 or ox + glyphs.width > x1:
        sys.exit('ERROR: text %dpx does not fit the banner (%d..%d)'
                 % (glyphs.width, x0, x1))

    drawn = 0
    for yy in range(glyphs.height):
        for xx in range(glyphs.width):
            if glyphs.getpixel((xx, yy)) >= 128:
                X, Y = ox + xx, oy + yy
                if x0 <= X < x1 and y0 <= Y < y1:
                    px[X, Y] = INK
                    drawn += 1
    print('drew %r  %dx%d at (%d,%d), %d pixels' %
          (TEXT, glyphs.width, glyphs.height, ox, oy, drawn))

    # "KOR by NaVaMo" on the copyright row, which is the one strip of this
    # sheet that is definitely drawn on screen -- below the banner the sprite
    # stops short and clips anything put there.
    BRIGHT = 1
    cred = render('KOR by NaVaMo', CREDIT_FONT, 8, 0, 2)
    cx, cy = 160, 0        # rows 0-7 are empty from x=159 on; the
                           # copyright sits at 72..158 and Press START
                           # does not start until y=9
    if cx + cred.width > im.width:
        sys.exit('ERROR: credit runs off the sheet')
    # drop shadow first, then the bright fill -- a full outline swallowed the
    # letters at this size
    for dx, dy in ((1, 0), (0, 1), (1, 1)):
        for yy in range(cred.height):
            for xx in range(cred.width):
                if cred.getpixel((xx, yy)) >= 128:
                    X, Y = cx + xx + dx, cy + yy + dy
                    if 0 <= X < im.width and 0 <= Y < im.height:
                        px[X, Y] = INK
    for yy in range(cred.height):
        for xx in range(cred.width):
            if cred.getpixel((xx, yy)) >= 128:
                px[cx + xx, cy + yy] = BRIGHT
    print('credit %dx%d at (%d,%d)' % (cred.width, cred.height, cx, cy))

    im.save(PNG)
    subprocess.run([PNG2DMP, PNG, '--lz77', '-o', DMP], check=True)
    print('regenerated', os.path.basename(DMP), os.path.getsize(DMP), 'bytes')


if __name__ == '__main__':
    main()
