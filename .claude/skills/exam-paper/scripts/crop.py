# -*- coding: utf-8 -*-
"""从原卷（PDF 某页或一张图片）裁一块存成 PNG，拿去直接看图抄题。

用法：
  python crop.py 原卷.pdf 页码 x0 y0 x1 y1 输出.png [dpi]     # 坐标是整页比例 0～1，页码从 1 数，dpi 默认 200
  python crop.py 原卷.jpg - x0 y0 x1 y1 输出.png
  python crop.py 原卷.pdf 页码 0 0 1 1 输出.png 80            # 整页小图，先看题在哪儿

经验：先 80dpi 整页看位置，再 190～220dpi 裁那一道题。扫描件里的公式、根号、上下标要放大看，
汇编里 634px 的低清图不要拿来抄公式（只对答案）。读图时别一次看太多页——按题位直接裁。
"""
import sys

import pymupdf
from PIL import Image


def main():
    src, page, x0, y0, x1, y1, out = sys.argv[1:8]
    dpi = int(sys.argv[8]) if len(sys.argv) > 8 else 200
    x0, y0, x1, y1 = map(float, (x0, y0, x1, y1))
    if src.lower().endswith(".pdf"):
        d = pymupdf.open(src)
        pg = d[int(page) - 1]
        W, H = pg.rect.width, pg.rect.height
        clip = pymupdf.Rect(x0 * W, y0 * H, x1 * W, y1 * H)
        pg.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY).save(out)
    else:
        im = Image.open(src).convert("L")
        w, h = im.size
        im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))).save(out)
    print(out)


if __name__ == "__main__":
    main()
