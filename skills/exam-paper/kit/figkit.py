"""画图工具：Fig（自然坐标自动缩放到画布）、Plot（没有网格的坐标系）、grid（网格坐标系）、角度/圆/弧的小函数、hrow（几张小图拼一行）。

规矩：点的坐标由题干条件算出来，不手摆；*_points() 返回图里画的那组点，验算和审计都用它；练习题的图不画答案点。
"""

from math import acos, atan2, cos, degrees, hypot, pi, radians, sin, sqrt

from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Polygon, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import mm

import geometry as G
from geometry import FAINT, FILLC, Coord, dist, foot, inter, lerp, rot
from layout import INK

R3, R2 = sqrt(3), sqrt(2)
SHADE = colors.HexColor("#d9dde3")


class Fig(G.Fig):
    """留边 5mm：图卡会把整张画布放大，留边也跟着放大。"""

    def __init__(self, pts, w=76, hmax=58, pad=5):
        super().__init__(pts, w, hmax, pad)


def mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def dirv(deg, L=1.0):
    return (L * cos(radians(deg)), L * sin(radians(deg)))


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def arcpts(c, r, a0, a1, n=48):
    return [(c[0] + r * cos(radians(a0 + (a1 - a0) * i / n)), c[1] + r * sin(radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def _ang(a, v, b):
    d1 = degrees(atan2(a[1] - v[1], a[0] - v[0]))
    d2 = degrees(atan2(b[1] - v[1], b[0] - v[0]))
    t = abs(d1 - d2) % 360
    return min(t, 360 - t)


def circle_line(c, r, p, q):
    """直线 pq 与圆 (c, r) 的交点（按从 p 到 q 的参数排序）。"""
    dx, dy = q[0] - p[0], q[1] - p[1]
    fx, fy = p[0] - c[0], p[1] - c[1]
    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    cc = fx * fx + fy * fy - r * r
    disc = b * b - 4 * a * cc
    if disc < 0:
        return []
    s = sqrt(disc)
    return [(p[0] + t * dx, p[1] + t * dy) for t in sorted(((-b - s) / (2 * a), (-b + s) / (2 * a)))]


# ---------------------------------------------------------------- 没有网格的坐标系（中考函数题的样子）
class Plot:
    """x、y 轴带箭头，没有网格；只在 ticks 给出的位置标数。坐标单位自动换算成 mm。"""

    def __init__(self, xmin, xmax, ymin, ymax, w=72, hmax=60, xticks=(), yticks=(), step=None):
        self.step = step or min((w - 12) / (xmax - xmin), (hmax - 12) / (ymax - ymin))
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.ox = 6 + (-xmin) * self.step
        self.oy = 6 + (-ymin) * self.step
        W = (xmax - xmin) * self.step + 12
        H = (ymax - ymin) * self.step + 12
        self.d = G.fig(W, H)
        x0, x1 = self.T((xmin, 0))[0], self.T((xmax, 0))[0]
        y0, y1 = self.T((0, ymin))[1], self.T((0, ymax))[1]
        G.seg(self.d, (x0, self.oy), (x1 + 2.5, self.oy), width=0.75)
        G.seg(self.d, (self.ox, y0), (self.ox, y1 + 2.5), width=0.75)
        G.poly(self.d, [(x1 + 4, self.oy), (x1 + 1.6, self.oy + 0.9), (x1 + 1.6, self.oy - 0.9)], fill=INK, width=0.4)
        G.poly(self.d, [(self.ox, y1 + 4), (self.ox - 0.9, y1 + 1.6), (self.ox + 0.9, y1 + 1.6)], fill=INK, width=0.4)
        G.lbl(self.d, (x1 + 3.2, self.oy - 3.4), "x", size=7.6, anchor="middle")
        G.lbl(self.d, (self.ox + 2.2, y1 + 2.2), "y", size=7.6, anchor="start")
        G.lbl(self.d, (self.ox - 1.4, self.oy - 3.4), "O", size=7.2, anchor="end")
        for v in xticks:
            x = self.T((v, 0))[0]
            G.seg(self.d, (x, self.oy), (x, self.oy + 1.1), width=0.6)
            G.lbl(self.d, (x, self.oy - 3.4), _num(v), size=6.6)
        for v in yticks:
            y = self.T((0, v))[1]
            G.seg(self.d, (self.ox, y), (self.ox + 1.1, y), width=0.6)
            G.lbl(self.d, (self.ox - 1.4, y - 1.0), _num(v), size=6.6, anchor="end")

    def T(self, p):
        return (self.ox + p[0] * self.step, self.oy + p[1] * self.step)

    def inside(self, p):
        return (self.xmin - 1e-9 <= p[0] <= self.xmax + 1e-9 and self.ymin - 1e-9 <= p[1] <= self.ymax + 1e-9)

    def seg(self, a, b, **kw):
        G.seg(self.d, self.T(a), self.T(b), **kw)

    def dseg(self, a, b):
        G.seg(self.d, self.T(a), self.T(b), dash=(2.2, 1.8), color=FAINT, width=0.75)

    def poly(self, pts, fill=None, **kw):
        G.poly(self.d, [self.T(p) for p in pts], fill=fill, **kw)

    def pt(self, p, text, dx=1.4, dy=1.2, anchor="start", size=7.6):
        G.dot(self.d, self.T(p), r=0.85)
        if text:
            G.lbl(self.d, self.T(p), text, dx, dy, size=size, anchor=anchor)

    def lbl(self, p, text, dx=0, dy=0, anchor="middle", size=7.6):
        G.lbl(self.d, self.T(p), text, dx, dy, size=size, anchor=anchor)

    def circle(self, c, r, width=0.8):
        cx, cy = self.T(c)
        self.d.add(Circle(cx * mm, cy * mm, r * self.step * mm, fillColor=None, strokeColor=INK, strokeWidth=width))

    def curve(self, fn, x0=None, x1=None, n=160, width=0.9, dash=None):
        Coord.curve(self, fn, x0, x1, n=n, width=width, dash=dash)

    def line(self, k, b, width=0.8, dash=None):
        Coord.line(self, k, b, width=width, dash=dash)

    def vline(self, x):
        G.seg(self.d, self.T((x, self.ymin)), self.T((x, self.ymax)), dash=(2.2, 1.8), color=FAINT, width=0.75)


def _num(v):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:g}"


def grid(xmin, xmax, ymin, ymax, w=72, hmax=62, labels=True):
    """网格坐标系（一格一个单位，新定义题常用）。"""
    step = min((w - 14) / (xmax - xmin), (hmax - 14) / (ymax - ymin), 8.5)
    return Coord(xmin, xmax, ymin, ymax, w=w, step=step, hmax=hmax, labels=labels)


def blank_circle_grid(xmin, xmax, ymin, ymax, r=1, center=(0, 0), w=72, hmax=62):
    c = grid(xmin, xmax, ymin, ymax, w=w, hmax=hmax)
    c.circle(center, r)
    return c



# ---------------------------------------------------------------- 弧、圆、标签
def arc(f, c, r, a0, a1, width=0.8, dash=None, n=64):
    flat = []
    for q in arcpts(c, r, a0, a1, n):
        x, y = f.T(q)
        flat += [x * mm, y * mm]
    kw = dict(strokeColor=INK, strokeWidth=width)
    if dash:
        kw["strokeDashArray"] = dash
    f.d.add(PolyLine(flat, **kw))


def box(c, r):
    """圆的包围点（给 Fig 定画布用）。"""
    return [(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)]


def out(c, p, k=3.0):
    """标签往「圆心→点」的方向推出去 k mm（dy 额外下移 1.2mm，字的基线在下面）。"""
    a = atan2(p[1] - c[1], p[0] - c[0])
    return k * cos(a), k * sin(a) - 1.2


def label_out(f, c, p, text, k=3.0, size=8.2):
    dx, dy = out(c, p, k)
    f.lbl(p, text, dx, dy, size=size)
    f.dot(p)


def line_x(p, q, y):
    """直线 pq 上纵坐标为 y 的点。"""
    t = (y - p[1]) / (q[1] - p[1])
    return (p[0] + t * (q[0] - p[0]), y)



# ---------------------------------------------------------------- 小图拼一行
def hrow(items, gap=5):
    """几张小图横着排成一张，每张下面写图注（「图1」……）；竖直方向居中。"""
    capH = 5 * mm
    W = sum(d.width for d, _ in items) + gap * mm * (len(items) - 1)
    H = max(d.height for d, _ in items) + capH
    out = Drawing(W, H)
    x = 0
    for d, cap in items:
        g = Group(*d.contents)
        g.translate(x, capH + (H - capH - d.height) / 2)
        out.add(g)
        if cap:
            out.add(String(x + d.width / 2, 1.0 * mm, cap, fontName="CN", fontSize=7.6,
                           textAnchor="middle", fillColor=INK))
        x += d.width + gap * mm
    return out
