"""把一组图拼成一张大图，方便一次看完（开发用，不是交付内容）。

用法：python contact_sheet.py 模块名 输出.png [函数名前缀...]
"""
import importlib
import sys

import pymupdf
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Group, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import mm


def sheet(mod, out, prefixes=("art_", "fig_"), cols=2, names=None, dpi=150):
    m = importlib.import_module(mod)
    names = names or sorted(n for n in dir(m) if n.startswith(tuple(prefixes)))
    ds = [(n, getattr(m, n)()) for n in names]
    cw = max(d.width for _, d in ds) + 6 * mm
    rows = [ds[i:i + cols] for i in range(0, len(ds), cols)]
    rh = [max(d.height for _, d in r) + 8 * mm for r in rows]
    big = Drawing(cw * cols, sum(rh))
    big.add(Rect(0, 0, big.width, big.height, fillColor=colors.white, strokeColor=None))
    y = big.height
    for r, h in zip(rows, rh):
        y -= h
        for c, (n, d) in enumerate(r):
            g = Group(*d.contents)
            g.translate(c * cw + 3 * mm, y + 3 * mm)
            big.add(g)
            big.add(Rect(c * cw + 3 * mm, y + 3 * mm, d.width, d.height, fillColor=None,
                         strokeColor=colors.HexColor("#dddddd"), strokeWidth=0.3))
            big.add(String(c * cw + 3 * mm, y + h - 4 * mm, n, fontName="Helvetica", fontSize=7,
                           fillColor=colors.red))
    doc = pymupdf.open("pdf", renderPDF.drawToString(big))
    doc[0].get_pixmap(dpi=dpi).save(out)
    return names


if __name__ == "__main__":
    print(sheet(sys.argv[1], sys.argv[2], names=sys.argv[3:] or None))
