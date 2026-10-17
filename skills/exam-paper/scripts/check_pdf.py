# -*- coding: utf-8 -*-
"""交付前量 PDF：页数、每栏栏底空白、行首标点、水印，可选导出每页 PNG 和总览拼图。

用法：
  python check_pdf.py 卷子.pdf [--watermark 水印文字] [--png 目录] [--montage 目录]

- 栏底空白：每栏最后一行内容到栏底的距离（mm），算的时候排除水印字。题目部分的大空白
  （> 60mm 而且不是作答区）要么调顺序（packsim.py），要么放备用图／提示，别放着不管。
- 行首标点：行首是「，。；：？！）》」』、·”」的行，有一个就得改措辞（只能挂一个标点，「）。」连着会掉一个下去）。
- 水印：每页文字层里水印出现 3 次以上算有。
--png 导出 100dpi 的每页图（看渲染一定要真看图，别只看数字），--montage 再拼成每 4 页一张的总览。
"""
import argparse
import os
import sys

import pymupdf

MM = 72 / 25.4
LEFT_X = 14 * MM                       # layout.MX
RIGHT_X = (14 + 87 + 8) * MM           # MX + COLW + GUT
PUNCT = "，。；：？！）》」』、·”"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--watermark", default="")
    ap.add_argument("--png", default="")
    ap.add_argument("--montage", default="")
    a = ap.parse_args()
    doc = pymupdf.open(a.pdf)
    print(f"{os.path.basename(a.pdf)}：{doc.page_count} 页")
    bad, wm = [], 0
    for i, pg in enumerate(doc, 1):
        W, H = pg.rect.width, pg.rect.height
        text = pg.get_text()
        if a.watermark and text.count(a.watermark) >= 3:
            wm += 1
        skip = lambda t: a.watermark and a.watermark in t
        blocks = [b for b in pg.get_text("blocks") if not skip(b[4])]
        imgs = [b["bbox"] for b in pg.get_image_info()]
        draws = [d["rect"] for d in pg.get_drawings()]
        res = []
        for lo, hi in ((0, W / 2), (W / 2, W)):
            ys = [b[3] for b in blocks if lo <= b[0] < hi and b[3] < H - 40]
            ys += [r[3] for r in imgs if lo <= r[0] < hi and r[3] < H - 40]
            ys += [r.y1 for r in draws if lo <= r.x0 < hi and r.y1 < H - 40 and r.height < 400 and r.width < 300]
            res.append(round((H - 37 - max(ys)) / MM) if ys else -1)
        print(f"  第{i}页  左栏底空 {res[0]}mm  右栏底空 {res[1]}mm")
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(sp["text"] for sp in l["spans"]).strip()
                if not t or skip(t):
                    continue
                x0 = l["bbox"][0]
                if t[0] in PUNCT and (abs(x0 - LEFT_X) < 3 or abs(x0 - RIGHT_X) < 3):
                    bad.append((i, t[:24]))
        if a.png:
            os.makedirs(a.png, exist_ok=True)
            pg.get_pixmap(dpi=100).save(os.path.join(a.png, f"p{i}.png"))
    print("行首标点：", "无" if not bad else "")
    for i, t in bad:
        print(f"  第{i}页：{t}")
    if a.watermark:
        print(f"水印：{wm}/{doc.page_count} 页")
    if a.montage and a.png:
        from PIL import Image, ImageDraw
        ims = [Image.open(os.path.join(a.png, f"p{i}.png")).convert("RGB") for i in range(1, doc.page_count + 1)]
        w = 400
        h = int(w * ims[0].size[1] / ims[0].size[0])
        os.makedirs(a.montage, exist_ok=True)
        for k in range(0, len(ims), 4):
            grp = ims[k:k + 4]
            sheet = Image.new("RGB", (4 * (w + 8), h + 8), "#888")
            for j, im in enumerate(grp):
                im = im.resize((w, h))
                ImageDraw.Draw(im).text((8, 4), f"p{k + j + 1}", fill=(220, 0, 0))
                sheet.paste(im, (j * (w + 8), 0))
            out = os.path.join(a.montage, f"montage_{k // 4 + 1}.jpg")
            sheet.save(out, quality=85)
            print("总览：", out)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
