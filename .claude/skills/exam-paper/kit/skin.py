"""卡片式试卷皮肤（黑白）：首页横幅（右边是分数印章）、关卡式章节头、图卡、题号徽章、选项字母圈、页面装饰、水印。

不含任何人物形象。硬规范不变：两栏、正文宋体、作答区留白不画线、分式真分数线。
题号徽章走 layout._esc 的占位符（@@Q:12:151515@@），见 qnum()。
"""

from pathlib import Path as _P

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import (Circle, Drawing, Ellipse, Line, Path, Polygon, PolyLine,
                                       Rect, String)
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, NextPageTemplate, PageTemplate,
                                Paragraph)
from reportlab.lib.styles import ParagraphStyle

import layout as L
from layout import BODY, COLW, FULLW, GUT, MX, PH, PW, TOP, BOTTOM, _markup

# ---------- 字体 ----------
# 标题用微软雅黑 Bold（现代、字全）；可爱的小标签用幼圆。正文仍是宋体（规范 3）。
for _name, _path in (("YH", r"C:\Windows\Fonts\msyhbd.ttc"), ("YHR", r"C:\Windows\Fonts\msyh.ttc"),
                     ("YOU", r"C:\Windows\Fonts\SIMYOU.TTF")):
    if _name not in pdfmetrics.getRegisteredFontNames():
        if _P(_path).exists():
            pdfmetrics.registerFont(TTFont(_name, _path, subfontIndex=0))
        else:                                    # 换机器时退回黑体，不至于崩
            pdfmetrics.registerFont(TTFont(_name, L._HEAD[0], subfontIndex=L._HEAD[1]))

# ---------- 配色 ----------
H = colors.HexColor
INK = H("#2b2d42")
SOFT = H("#6c6f8a")
PINK, PINK_L = "#ff7aa8", "#ffe4ee"
SKY, SKY_L = "#4fa8ec", "#e2f1fd"
MINT, MINT_L = "#3fc49a", "#dcf6ec"
LAV, LAV_L = "#8f7cf0", "#ece8fe"
LEMON, LEMON_L = "#f5b82e", "#fff3d1"
PEACH, PEACH_L = "#ff8f5e", "#ffe8dc"
STAGE_COLORS = [SKY, MINT, LEMON, LAV, PEACH, PINK]
LIGHT = {PINK: PINK_L, SKY: SKY_L, MINT: MINT_L, LAV: LAV_L, LEMON: LEMON_L, PEACH: PEACH_L}

HAIR, HAIR_D, HAIR_L = H("#6b5bd2"), H("#3d3486"), H("#a99cf4")
SKIN = H("#ffeadf")
BOLT = H("#ffd23f")

# ---------- 黑白模式 ----------
# 黑白打印。彩色那套还留着（MONO=False）。
MONO = True
if MONO:
    INK, SOFT = H("#151515"), H("#6b6b6b")
    PINK = SKY = MINT = LAV = LEMON = PEACH = "#151515"
    PINK_L = SKY_L = MINT_L = LAV_L = LEMON_L = PEACH_L = "#ececec"
    STAGE_COLORS = [PINK] * 6
    LIGHT = {PINK: PINK_L}
DECO = ("#151515", "#8c8c8c", "#c2c2c2") if MONO else (LEMON, PINK, SKY)   # 纯装饰的星光、圆点
BUBBLE_BG = "#ffffff" if MONO else None                                      # 提示气泡白底黑边


# ---------- 画在画布上的装饰 ----------
def draw_drawing(canv, d, x, y):
    renderPDF.draw(d, canv, x, y)


def _gray(col):
    """彩色 → 灰。粉彩底色按亮度变浅灰；饱和的强调色（箭头、指针、红框）压暗，免得印出来看不见。"""
    if col is None or not hasattr(col, "red"):
        return col
    r, g, b = col.red, col.green, col.blue
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if max(r, g, b) - min(r, g, b) > 0.35:
        lum = min(lum, 0.42)
    return colors.Color(lum, lum, lum, alpha=getattr(col, "alpha", 1))


def mono_drawing(d):
    """把一张图里所有形状的填充色、描边色都换成灰度（就地修改，返回同一张图）。"""
    stack = [d]
    while stack:
        g = stack.pop()
        for o in getattr(g, "contents", []):
            if hasattr(o, "contents"):
                stack.append(o)
            for attr in ("fillColor", "strokeColor"):
                if hasattr(o, attr):
                    setattr(o, attr, _gray(getattr(o, attr)))
    return d


def canv_sparkle(canv, cx, cy, r, color):
    k = r * 0.18
    p = canv.beginPath()
    p.moveTo(cx, cy + r)
    p.curveTo(cx + k, cy + k, cx + k, cy + k, cx + r, cy)
    p.curveTo(cx + k, cy - k, cx + k, cy - k, cx, cy - r)
    p.curveTo(cx - k, cy - k, cx - k, cy - k, cx - r, cy)
    p.curveTo(cx - k, cy + k, cx - k, cy + k, cx, cy + r)
    p.close()
    canv.setFillColor(H(color))
    canv.drawPath(p, stroke=0, fill=1)


def pill(canv, x, y, text, fg, bg, font="YOU", size=7.6, padx=2.6 * mm, h=None, stroke=None, anchor="start"):
    """胶囊标签，返回宽度。"""
    tw = pdfmetrics.stringWidth(text, font, size)
    h = h or size * 1.75
    w = tw + 2 * padx
    if anchor == "end":
        x -= w
    elif anchor == "middle":
        x -= w / 2
    canv.setFillColor(H(bg) if isinstance(bg, str) else bg)
    if stroke:
        canv.setStrokeColor(H(stroke))
        canv.setLineWidth(0.6)
    canv.roundRect(x, y, w, h, h / 2, stroke=1 if stroke else 0, fill=1)
    canv.setFillColor(H(fg) if isinstance(fg, str) else fg)
    canv.setFont(font, size)
    canv.drawCentredString(x + w / 2, y + (h - size * 0.72) / 2, text)
    return w


def sticker_text(canv, x, y, text, font, size, fill, outline="#ffffff", shadow=PINK, ow=None):
    """描边贴纸字：粉色投影 → 白描边 → 实心字。
    PDF 的文字渲染模式（Tr）会留在图形状态里，所以三遍都用文字对象显式设模式，
    最后一遍必须是 0（只填充），否则正文字会沿用上一遍的「只描边」。"""
    ow = ow or size * 0.11

    def run(dx, dy, mode, fillc=None, strokec=None):
        t = canv.beginText()
        t.setTextRenderMode(mode)
        t.setFont(font, size)
        t.setTextOrigin(x + dx, y + dy)
        t.textOut(text)
        canv.saveState()                 # q…Q 把 Tr 也一起还原，ReportLab 自己不会再发 0 Tr
        if fillc is not None:
            canv.setFillColor(fillc)
        if strokec is not None:
            canv.setStrokeColor(strokec)
        canv.drawText(t)
        canv.restoreState()

    canv.saveState()
    canv.setLineJoin(1)
    canv.setLineWidth(ow)
    run(size * 0.07, -size * 0.07, 2, H(shadow), H(shadow))
    run(0, 0, 1, None, H(outline))
    run(0, 0, 0, H(fill) if isinstance(fill, str) else fill)
    canv.restoreState()


# ---------- 首页横幅 ----------
class Banner(Flowable):
    def __init__(self, title, ribbon, chips, info, bubble, h=46 * mm, c1=PINK_L, c2=SKY_L, stamp="300"):
        Flowable.__init__(self)
        self.title, self.ribbon, self.chips, self.info, self.bubble = title, ribbon, chips, info, bubble
        self.h, self.c1, self.c2 = h, c1, c2
        self.stamp = stamp          # 右边印章上的分数

    def wrap(self, aW, aH):
        self.w = aW
        return aW, self.h

    def draw(self):
        from math import cos, pi, sin
        import random
        c = self.canv
        w, h = self.w, self.h
        c.saveState()
        p = c.beginPath()
        p.roundRect(0, 0, w, h, 5 * mm)
        c.clipPath(p, stroke=0, fill=0)
        c.setFillColor(colors.white)
        c.rect(0, 0, w, h, stroke=0, fill=1)
        # 渐变网点：从左往右点越来越大（网点纸效果）
        step = 2.1 * mm
        c.setFillColor(H("#d4d4d4"))
        i = 0
        x = w * 0.30
        while x < w + step:
            t = (x - w * 0.30) / (w * 0.70)
            r = 0.06 * mm + 0.52 * mm * t
            y = (i % 2) * step / 2
            while y < h + step:
                c.circle(x, y, r, stroke=0, fill=1)
                y += step
            x += step
            i += 1
        # 集中线：从右边的印章往外放射
        cx, cy = w - 21 * mm, h * 0.56
        rnd = random.Random(7)
        c.setStrokeColor(H("#b9b9b9"))
        for k in range(84):
            a = 2 * pi * k / 84 + rnd.uniform(-0.025, 0.025)
            r0 = 21 * mm + rnd.uniform(0, 7 * mm)
            c.setLineWidth(rnd.uniform(0.25, 0.85))
            c.line(cx + r0 * cos(a), cy + r0 * sin(a), cx + 140 * mm * cos(a), cy + 140 * mm * sin(a))
        c.restoreState()
        c.setStrokeColor(INK)
        c.setLineWidth(1.3)
        c.roundRect(0.65, 0.65, w - 1.3, h - 1.3, 4.8 * mm, stroke=1, fill=0)
        for (sx, sy, sr, col) in ((w * 0.53, h * 0.80, 2.4 * mm, DECO[0]), (w * 0.57, h * 0.62, 1.4 * mm, DECO[1]),
                                  (w * 0.035, h * 0.30, 1.6 * mm, DECO[1]), (w * 0.49, h * 0.22, 1.1 * mm, DECO[0])):
            canv_sparkle(c, sx, sy, sr, col)
        x0 = 7 * mm
        pill(c, x0, h - 10.2 * mm, self.ribbon, "#ffffff", INK, font="YH", size=7.2)
        sticker_text(c, x0, h - 22.5 * mm, self.title, "YH", 23, INK, shadow="#b3b3b3")
        cx = x0
        for t, _ in self.chips:
            cx += pill(c, cx, h - 30.5 * mm, t, INK, "#ffffff", size=6.8, padx=2.2 * mm, stroke="#151515") + 1.5 * mm
        y = 4.8 * mm
        cx = x0
        for t in self.info:
            cx += pill(c, cx, y, t, "#ffffff", INK, font="YH", size=7.4, h=7 * mm) + 2 * mm
        for lab, bw in (("姓名", 30 * mm), ("班级", 22 * mm)):
            c.setFont("YH", 7.6)
            c.setFillColor(INK)
            c.drawString(cx + 1 * mm, y + 2.2 * mm, lab)
            cx += 9 * mm
            c.setFillColor(colors.white)
            c.setStrokeColor(INK)
            c.setLineWidth(0.7)
            c.roundRect(cx, y, bw, 7 * mm, 3.5 * mm, stroke=1, fill=1)
            cx += bw + 3 * mm
        # 右边：分数印章
        size = h - 9 * mm
        mx = w - size - 6 * mm
        c.setFillColor(colors.white)
        c.setStrokeColor(INK)
        c.setLineWidth(1.4)
        c.circle(mx + size / 2, h / 2, size / 2, stroke=1, fill=1)
        c.setLineWidth(0.5)
        c.circle(mx + size / 2, h / 2, size / 2 - 2.2 * mm, stroke=1, fill=0)
        c.setFillColor(INK)
        c.setFont("YH", 8.5)
        c.drawCentredString(mx + size / 2, h / 2 + 7.5 * mm, "满分")
        c.setFont("YH", 26)
        c.drawCentredString(mx + size / 2, h / 2 - 4.5 * mm, self.stamp)
        c.setFont("YOU", 7.5)
        c.drawCentredString(mx + size / 2, h / 2 - 11 * mm, self.bubble or "加油！")


# ---------- 提示气泡 ----------
TIP = ParagraphStyle("tip", parent=BODY, fontSize=8.3, leading=12.4, textColor=INK, spaceAfter=0,
                     spaceBefore=0)


def _bubble(c, x, y, w, h, bg, edge, tail_left=True, tail_y=None):
    c.setFillColor(H(bg))
    c.setStrokeColor(H(edge))
    c.setLineWidth(0.7)
    c.roundRect(x, y, w, h, 3.0 * mm, stroke=1, fill=1)
    ty = tail_y if tail_y is not None else y + h - 4.6 * mm
    p = c.beginPath()
    if tail_left:
        p.moveTo(x + 0.3, ty + 1.5 * mm)
        p.lineTo(x - 2.4 * mm, ty)
        p.lineTo(x + 0.3, ty - 1.3 * mm)
    else:
        p.moveTo(x + w - 0.3, ty + 1.5 * mm)
        p.lineTo(x + w + 2.4 * mm, ty)
        p.lineTo(x + w - 0.3, ty - 1.3 * mm)
    c.drawPath(p, stroke=1, fill=1)
    c.setStrokeColor(H(bg))
    c.setLineWidth(1.5)
    xx = x + 0.45 if tail_left else x + w - 0.45
    c.line(xx, ty + 1.3 * mm, xx, ty - 1.1 * mm)


# ---------- 关卡章节头 ----------
class Stage(Flowable):
    """STAGE 01 + 标题 + 分值胶囊，下面可以挂一个提示（body）。
    必须是单个 Flowable，才能交给 layout 的 _pending 机制和后面第一题绑在一起
    （嵌套 KeepTogether 会整块跳页）。"""

    def __init__(self, no, title, sub, color, body=None, boss=False, top="STAGE"):
        Flowable.__init__(self)
        self.no, self.title, self.sub, self.color = no, title, sub, color
        self.body, self.boss, self.top = body, boss, ("BOSS" if boss else top)

    def wrap(self, aW, aH):
        self.w = aW
        self.head_h = 15 * mm
        self.body_h = 0
        if self.body is not None:
            _, self.body_h = self.body.wrap(aW, aH)
        return aW, self.head_h + self.body_h + 2 * mm

    def draw(self):
        c = self.canv
        w = self.w
        y0 = self.body_h + 2 * mm
        col = self.color
        bs = 12.5 * mm
        c.saveState()
        if self.boss:
            p = c.beginPath()
            p.roundRect(0, y0 + 1.2 * mm, bs, bs, 3.2 * mm)
            c.clipPath(p, stroke=0, fill=0)
            c.linearGradient(0, y0, bs, y0 + bs, (H("#151515"), H("#6b6b6b")), extend=True)
        else:
            c.setFillColor(H(col))
            c.roundRect(0, y0 + 1.2 * mm, bs, bs, 3.2 * mm, stroke=0, fill=1)
        c.restoreState()
        c.setFillColor(colors.white)
        c.setFont("YH", 5.4)
        c.drawCentredString(bs / 2, y0 + 1.2 * mm + bs - 3.6 * mm, self.top)
        c.setFont("YH", 13 if len(self.no) <= 2 else 10)
        c.drawCentredString(bs / 2, y0 + 3.4 * mm, self.no)
        canv_sparkle(c, bs - 0.4 * mm, y0 + bs + 0.6 * mm, 1.5 * mm, DECO[1])
        c.setFillColor(INK)
        c.setFont("YH", 12.6)
        c.drawString(bs + 3 * mm, y0 + 7.6 * mm, self.title)
        tw = pdfmetrics.stringWidth(self.title, "YH", 12.6)
        pill(c, bs + 3 * mm, y0 + 1.6 * mm, self.sub, col if not self.boss else PINK,
             LIGHT.get(col, PINK_L) if not self.boss else PINK_L, size=7.2)
        for i, cc in enumerate(DECO):
            c.setFillColor(H(cc))
            c.circle(w - 13 * mm + i * 3.2 * mm, y0 + 9.2 * mm, 0.9 * mm, stroke=0, fill=1)
        canv_sparkle(c, w - 2.4 * mm, y0 + 8.8 * mm, 2.0 * mm, col if not self.boss else PINK)
        c.setStrokeColor(H(col if not self.boss else LAV))
        c.setLineWidth(1.3)
        c.setLineCap(1)
        c.setDash([0.1, 3.0])
        c.line(bs + 3 * mm + tw + 3 * mm, y0 + 9.2 * mm, w - 15 * mm, y0 + 9.2 * mm)
        c.setDash([])
        if self.body is not None:
            self.body.drawOn(c, 0, 0)


# ---------- 图卡 ----------
class Card(Flowable):
    """把一张图放进浅色圆角卡片，左上角挂题号小标签。不是 KeepTogether（避免嵌套），高度固定。"""

    def __init__(self, d, label, color=SKY, maxh=70 * mm, smax=1.15):
        Flowable.__init__(self)
        if MONO:
            mono_drawing(d)
        self.d, self.label, self.color, self.maxh, self.smax = d, label, color, maxh, smax
        self.k = 1.0                # 缩放系数：skin_q.FitBlock 在栏底差一点放不下时把图缩小一点

    def wrap(self, aW, aH):
        self.w = aW
        self.pad = 2.6 * mm
        self.tag = 4.6 * mm
        self.s = min((aW - 2 * self.pad) / self.d.width, self.maxh / self.d.height, self.smax) * self.k
        self.h = self.d.height * self.s + 2 * self.pad + self.tag
        return aW, self.h + 2 * mm

    def draw(self):
        c = self.canv
        y = 1 * mm
        c.setFillColor(colors.white)        # 电路图的元件靠白底盖导线，卡片必须是纯白，否则露白块
        c.setStrokeColor(H(self.color))
        c.setLineWidth(0.55)
        c.setDash([2.2, 1.6])
        c.roundRect(0, y, self.w, self.h, 3.6 * mm, stroke=1, fill=1)
        c.setDash([])
        pill(c, 2.4 * mm, y + self.h - 5.6 * mm, self.label, "#ffffff", self.color, size=6.6)
        canv_sparkle(c, self.w - 3.2 * mm, y + self.h - 3.2 * mm, 1.3 * mm, DECO[1])
        dw = self.d.width * self.s
        c.saveState()
        c.translate((self.w - dw) / 2, y + self.pad)
        c.scale(self.s, self.s)
        renderPDF.draw(self.d, c, 0, 0)
        c.restoreState()


# ---------- 题号徽章 / 选项字母 ----------
def qnum(n, color=PINK):
    """题干开头的题号徽章占位符，由 layout._esc 换成内联小图。"""
    return f"@@Q:{n}:{color.lstrip('#')}@@ "


def opt(letter, color=SKY):
    return f"@@O:{letter}:{color.lstrip('#')}@@ "


# ---------- 页面 ----------
HEADER_H = 50 * mm


def _decor(canv, doc, label, accent):
    canv.saveState()
    if getattr(getattr(doc, "pageTemplate", None), "id", "") == "full":     # 通栏整页：只画页脚
        _footer(canv, doc, label, accent)
        canv.restoreState()
        return
    # 栏间圆点线 + 中间一颗星
    xm = MX + COLW + GUT / 2
    top = PH - TOP - (HEADER_H if doc.page == 1 else 0) - 3 * mm
    canv.setStrokeColor(H("#bdbdbd"))
    canv.setLineWidth(1.25)
    canv.setLineCap(1)
    canv.setDash([0.1, 3.4])
    canv.line(xm, BOTTOM + 2 * mm, xm, top)
    canv.setDash([])
    canv_sparkle(canv, xm, (BOTTOM + top) / 2, 1.8 * mm, DECO[1])
    # 右上角星光
    if doc.page > 1:
        for (dx, dy, r, col) in ((-6, -5.5, 2.0, DECO[0]), (-11.5, -4.0, 1.2, DECO[1]), (-2.5, -9.5, 1.0, DECO[2])):
            canv_sparkle(canv, PW - MX + dx * mm + 4 * mm, PH + dy * mm, r * mm, col)
    _footer(canv, doc, label, accent)
    canv.restoreState()


def _footer(canv, doc, label, accent):
    # 页脚：左边星光＋卷名，右边页码胶囊
    canv_sparkle(canv, MX + 4 * mm, 7.4 * mm, 2.4 * mm, DECO[0])
    canv.setFont("YOU", 7)
    canv.setFillColor(SOFT)
    canv.drawString(MX + 10 * mm, 5.6 * mm, label)
    pill(canv, PW - MX, 4.4 * mm, f"P.{doc.page:02d}", "#ffffff", accent, font="YH", size=7.2,
         anchor="end")


def _watermark(canv, doc, text):
    """斜着平铺的一层很淡的文字，画在内容上面（onPageEnd），图卡上也有。
    5.5% 的黑叠在黑字上还是黑字，叠在白纸上是很浅的灰，不影响看题。"""
    canv.saveState()
    canv.setFillColor(colors.black)
    canv.setFillAlpha(0.055)
    canv.setFont("YH", 19)
    dx, dy = 74 * mm, 34 * mm
    for row in range(-1, int(PH / dy) + 2):
        for col in range(-1, int(PW / dx) + 2):
            x = col * dx + (row % 2) * dx / 2
            y = row * dy
            canv.saveState()
            canv.translate(x, y)
            canv.rotate(28)
            canv.drawString(0, 0, text)
            canv.restoreState()
    canv.restoreState()


def make_doc(path, label, accent=PINK, watermark=None):
    """watermark：水印文字（斜着平铺在每页上面），页脚也会印一行。"""
    d = BaseDocTemplate(str(path), pagesize=(PW, PH), leftMargin=MX, rightMargin=MX,
                        topMargin=TOP, bottomMargin=BOTTOM, title=label, author=watermark or "")
    colh = PH - TOP - BOTTOM
    foot = f"{label}　·　{watermark}" if watermark else label
    on = lambda c, x: _decor(c, x, foot, accent)
    end = (lambda c, x: _watermark(c, x, watermark)) if watermark else (lambda c, x: None)
    f = dict(leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    first = PageTemplate(id="first", onPage=on, onPageEnd=end, frames=[
        Frame(MX, PH - TOP - HEADER_H, FULLW, HEADER_H, id="head", **f),
        Frame(MX, BOTTOM, COLW, colh - HEADER_H, id="l", **f),
        Frame(MX + COLW + GUT, BOTTOM, COLW, colh - HEADER_H, id="r", **f),
    ])
    later = PageTemplate(id="later", onPage=on, onPageEnd=end, frames=[
        Frame(MX, BOTTOM, COLW, colh, id="l", **f),
        Frame(MX + COLW + GUT, BOTTOM, COLW, colh, id="r", **f),
    ])
    # 通栏整页（需要整页大图时用）
    full = PageTemplate(id="full", onPage=on, onPageEnd=end, frames=[Frame(MX, BOTTOM, FULLW, colh, id="full", **f)])
    d.addPageTemplates([first, later, full])
    return d


def header(story, banner):
    story.append(banner)
    story.append(NextPageTemplate("later"))


COL_H = PH - TOP - BOTTOM          # 非首页一栏的高度


def stage(story, *a, need=40 * mm, **k):
    """关卡头。不走 _pending 和第一题绑定（再绑上一道带图的题，装不下就整块跳栏，栏底空一大片）。
    前面放一个 CondPageBreak（ReportLab 里它其实是「按栏」换）：剩余空间放不下
    关卡头再加 need 这么多内容，就先换栏，这样关卡头不会孤零零待在栏底。"""
    body = k.pop("body", None)
    t = Stage(*a, **k)
    _, h = t.wrap(COLW, 2000)
    if body is not None:
        t.body = body
        _, h = t.wrap(COLW, 2000)
    story.append(CondPageBreak(h + need))
    story.append(t)
    L._pending.clear()
    return t
