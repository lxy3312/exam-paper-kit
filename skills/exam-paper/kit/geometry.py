"""几何作图工具。所有坐标单位都是 mm，原点在图的左下角。

几何题没有图等于白出——学生看不到图会整题跳过。
"""

from math import atan2, cos, degrees, hypot, radians, sin

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, PolyLine, String
from reportlab.lib import colors
from reportlab.lib.units import mm

from reportlab.lib.styles import ParagraphStyle

from layout import INK

FAINT = colors.HexColor("#9aa2ad")
FILLC = colors.HexColor("#eef2f6")


def fig(w, h):
    d = Drawing(w * mm, h * mm)
    d.hAlign = "CENTER"
    return d


def _u(p):
    return p[0] * mm, p[1] * mm


def seg(d, a, b, color=INK, width=0.8, dash=None):
    ln = Line(*_u(a), *_u(b), strokeColor=color, strokeWidth=width)
    if dash:
        ln.strokeDashArray = dash
    d.add(ln)


def poly(d, pts, fill=None, color=INK, width=0.9):
    flat = []
    for q in pts:
        flat += list(_u(q))
    d.add(Polygon(flat, fillColor=fill, strokeColor=color, strokeWidth=width))


def lbl(d, p, text, dx=0, dy=0, size=7.5, anchor="middle", color=INK):
    """点的标签。支持 "B<sub>1</sub>" 这种下标写法——String 不认 markup，
    这里手动把下标画小一号、往下挪半格（2026-09-18 之前坐标图里的 P<sub>1</sub> 一直是原样印出来的）。"""
    from reportlab.pdfbase import pdfmetrics
    x, y = _u(p)
    x, y = x + dx * mm, y + dy * mm
    if "<sub>" in text:
        base, rest = text.split("<sub>", 1)
        sub = rest.split("</sub>", 1)[0]
        wb = pdfmetrics.stringWidth(base, "CN", size)
        ws = pdfmetrics.stringWidth(sub, "CN", size * 0.72)
        total = wb + ws
        x0 = x - total / 2 if anchor == "middle" else (x - total if anchor == "end" else x)
        d.add(String(x0, y, base, fontName="CN", fontSize=size, fillColor=color, textAnchor="start"))
        d.add(String(x0 + wb, y - size * 0.25, sub, fontName="CN", fontSize=size * 0.72,
                     fillColor=color, textAnchor="start"))
        return
    d.add(String(x, y, text, fontName="CN", fontSize=size, fillColor=color, textAnchor=anchor))


def dot(d, p, r=0.8):
    d.add(Circle(*_u(p), r, fillColor=INK, strokeColor=None))


def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = hypot(dx, dy) or 1
    return dx / L, dy / L


def right_angle(d, v, a, b, s=2.2):
    """在顶点 v 处画直角小方块，两边分别指向 a 和 b。"""
    u1, u2 = _unit(v, a), _unit(v, b)
    p1 = (v[0] + u1[0] * s, v[1] + u1[1] * s)
    p2 = (v[0] + u2[0] * s, v[1] + u2[1] * s)
    p3 = (p1[0] + u2[0] * s, p1[1] + u2[1] * s)
    seg(d, p1, p3, width=0.55)
    seg(d, p2, p3, width=0.55)


def tick(d, a, b, n=1, s=1.4, gap=1.1):
    """等长记号：在线段中点画 n 条垂直短线。"""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ux, uy = _unit(a, b)
    nx, ny = -uy, ux
    start = -(n - 1) * gap / 2
    for i in range(n):
        c = (mx + ux * (start + i * gap), my + uy * (start + i * gap))
        seg(d, (c[0] - nx * s, c[1] - ny * s), (c[0] + nx * s, c[1] + ny * s), width=0.7)


def arc(d, center, r, a0, a1, width=0.55, color=INK):
    """角弧，a0/a1 为角度。"""
    pts = []
    steps = max(8, int(abs(a1 - a0) / 5))
    for i in range(steps + 1):
        t = radians(a0 + (a1 - a0) * i / steps)
        pts += [(center[0] + r * cos(t)) * mm, (center[1] + r * sin(t)) * mm]
    d.add(PolyLine(pts, strokeColor=color, strokeWidth=width))


def angle_mark(d, v, a, b, r=4.5, text=None, tr=6.5):
    """在 v 处标出 ∠avb 的弧，并可写上角度值。"""
    a0 = degrees(atan2(a[1] - v[1], a[0] - v[0]))
    a1 = degrees(atan2(b[1] - v[1], b[0] - v[0]))
    if a1 - a0 > 180:
        a1 -= 360
    if a0 - a1 > 180:
        a0 -= 360
    arc(d, v, r, a0, a1)
    if text:
        t = radians((a0 + a1) / 2)
        lbl(d, (v[0] + tr * cos(t), v[1] + tr * sin(t)), text, size=6.6)


def rot(p, c, deg):
    """把点 p 绕点 c 旋转 deg 度（逆时针为正）。"""
    t = radians(deg)
    dx, dy = p[0] - c[0], p[1] - c[1]
    return (c[0] + dx * cos(t) - dy * sin(t), c[1] + dx * sin(t) + dy * cos(t))


def reflect(p, a, b):
    """把点 p 关于直线 ab 作对称。"""
    ux, uy = _unit(a, b)
    dx, dy = p[0] - a[0], p[1] - a[1]
    t = dx * ux + dy * uy
    fx, fy = a[0] + ux * t, a[1] + uy * t
    return (2 * fx - p[0], 2 * fy - p[1])


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def axes(d, ox, oy, xmax, ymax, xmin=0, ymin=0, step=6, labels=True):
    """直角坐标系，带刻度。ox/oy 为原点在图上的 mm 位置，step 为一个单位的 mm 长度。"""
    from math import ceil, floor
    x0, x1 = ox + xmin * step, ox + xmax * step
    y0, y1 = oy + ymin * step, oy + ymax * step
    xi = range(ceil(xmin - 1e-9), floor(xmax + 1e-9) + 1)     # 边界可以是小数（教材的坐标图）
    yi = range(ceil(ymin - 1e-9), floor(ymax + 1e-9) + 1)
    for i in xi:
        seg(d, (ox + i * step, y0), (ox + i * step, y1), color=colors.HexColor("#e3e7ec"), width=0.25)
    for j in yi:
        seg(d, (x0, oy + j * step), (x1, oy + j * step), color=colors.HexColor("#e3e7ec"), width=0.25)
    seg(d, (x0, oy), (x1 + 2, oy), width=0.7)
    seg(d, (ox, y0), (ox, y1 + 2), width=0.7)
    lbl(d, (x1 + 3, oy - 1), "x", size=6.8, anchor="start")
    lbl(d, (ox + 1.5, y1 + 2), "y", size=6.8, anchor="start")
    lbl(d, (ox - 1.5, oy - 3.4), "O", size=6.5, anchor="end")
    if labels:
        for i in xi:
            if i:
                lbl(d, (ox + i * step, oy - 3.4), str(i), size=5.6)
        for j in yi:
            if j:
                lbl(d, (ox - 1.4, oy + j * step - 0.9), str(j), size=5.6, anchor="end")

def scaled(d, s):
    """把画好的图整体缩放，便于并排放两三张。"""
    d.scale(s, s)
    d.width *= s
    d.height *= s
    return d


BIG_FIGS = True          # 图太小没法画辅助线——一行一图，撑满整栏
BIG_W = 80               # mm，每张图允许的最大宽度（栏宽约 84mm）
BIG_H = 72               # mm，每张图允许的最大高度
BIG_S_MAX = 1.8          # 旧图（52mm 画布）最多放大到这个倍数


def figrow(items, per_row=2, s=0.74):
    """并排放图并各配图注。北京中考几何题的标准做法：
    图1 给第(1)问，图2 给第(2)问，再给一张备用图画草稿。

    BIG_FIGS 打开时忽略 per_row/s：每张图独占一行，按栏宽自动放大，让他能在图上画辅助线，
    并且返回的是「一图一表」的列表（qblock 会摊平），题干只和第一张图绑在一起，
    后面的图自由流动——否则三张大图加题干装不进一栏，整题跳栏，前一栏空一大片。
    以前写好的图也一起变大，不用改调用处。"""
    from reportlab.lib.units import mm as _mm
    from reportlab.platypus import Table, TableStyle, Paragraph
    from layout import COLW, SMALL, _markup

    def _cap(text):
        return Paragraph(_markup(text), ParagraphStyle(
            "cap", parent=SMALL, alignment=1, fontSize=7.6, leading=9.6, spaceAfter=0))

    def _table(rows, ncol):
        t = Table(rows, colWidths=[COLW / ncol] * ncol)
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return t

    if BIG_FIGS:
        from reportlab.platypus import KeepTogether
        out = []
        for d, cap in items:
            # 图和图注绑死：Table 会在行间断开，图注单独跑到下一栏顶上过（2026-09-18）
            out.append(KeepTogether([_table([[big_scaled(d)], [_cap(cap)]], 1)]))
        return out
    cells = [scaled(d, s) for d, _ in items]
    caps = [_cap(c) for _, c in items]
    rows = []
    for i in range(0, len(cells), per_row):
        rows.append(cells[i:i + per_row] + [""] * (per_row - len(cells[i:i + per_row])))
        rows.append(caps[i:i + per_row] + [""] * (per_row - len(caps[i:i + per_row])))
    return _table(rows, per_row)


def big_scaled(d):
    """把一张图放大到撑满整栏（宽 ≤BIG_W，高 ≤BIG_H，最多 BIG_S_MAX 倍）。"""
    from reportlab.lib.units import mm as _mm
    sc = min(BIG_W * _mm / d.width, BIG_H * _mm / d.height, BIG_S_MAX)
    return scaled(d, sc)


# ---------- 自动适配画布：几何用自然单位算，画的时候统一缩放 ----------
def inter(p1, p2, p3, p4):
    """直线 p1p2 与直线 p3p4 的交点。"""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def foot(p, a, b):
    """点 p 在直线 ab 上的垂足。"""
    ux, uy = _unit(a, b)
    t = (p[0] - a[0]) * ux + (p[1] - a[1]) * uy
    return (a[0] + ux * t, a[1] + uy * t)


def along(a, b, L):
    """从 a 出发沿 ab 方向走 L（自然单位）到达的点。"""
    ux, uy = _unit(a, b)
    return (a[0] + ux * L, a[1] + uy * L)


def dist(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


class Fig:
    """把一组自然坐标的点缩放平移到 w×hmax mm 的画布里。

    用法：f = Fig([所有会画到的点]); f.seg(A,B); f.mark([(A,"A",dx,dy,anchor),...]); return f.d
    dx/dy 是标签相对点的偏移，单位 mm（不缩放）。"""

    def __init__(self, pts, w=76, hmax=58, pad=7):
        hmax = min(hmax, 58)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        self.s = min((w - 2 * pad) / max(x1 - x0, 1e-9), (hmax - 2 * pad) / max(y1 - y0, 1e-9))
        self.x0, self.y0, self.pad = x0, y0, pad
        self.w = (x1 - x0) * self.s + 2 * pad
        self.h = (y1 - y0) * self.s + 2 * pad
        self.d = fig(self.w, self.h)

    def T(self, p):
        return ((p[0] - self.x0) * self.s + self.pad, (p[1] - self.y0) * self.s + self.pad)

    def seg(self, a, b, **kw):
        seg(self.d, self.T(a), self.T(b), **kw)

    def dseg(self, a, b, color=None):
        seg(self.d, self.T(a), self.T(b), dash=(2.2, 1.8), color=color or FAINT, width=0.75)

    def poly(self, pts, fill=FILLC, **kw):
        poly(self.d, [self.T(p) for p in pts], fill=fill, **kw)

    def dot(self, p):
        dot(self.d, self.T(p), r=0.85)

    def lbl(self, p, text, dx=0, dy=0, anchor="middle", size=8.2):
        lbl(self.d, self.T(p), text, dx, dy, size=size, anchor=anchor)

    def mark(self, items):
        for p, t, dx, dy, an in items:
            self.lbl(p, t, dx, dy, an)
            self.dot(p)

    def ra(self, v, a, b, s=2.4):
        right_angle(self.d, self.T(v), self.T(a), self.T(b), s=s)

    def tick(self, a, b, n=1):
        tick(self.d, self.T(a), self.T(b), n, s=1.5)

    def angle(self, v, a, b, text=None, r=5.0, tr=7.6):
        angle_mark(self.d, self.T(v), self.T(a), self.T(b), r=r, text=text, tr=tr)

    def circle(self, c, r, color=INK, width=0.8):
        cx, cy = self.T(c)
        self.d.add(Circle(cx * mm, cy * mm, r * self.s * mm, fillColor=None,
                          strokeColor=color, strokeWidth=width))


class Coord:
    """带网格的直角坐标系，新定义题用。坐标单位自动换算成 mm。"""

    def __init__(self, xmin, xmax, ymin, ymax, w=76, step=None, hmax=66, labels=True):
        self.step = step or min((w - 14) / (xmax - xmin), 8.5)
        if (ymax - ymin) * self.step + 14 > hmax:      # 图太高会把整栏吃掉
            self.step = (hmax - 14) / (ymax - ymin)
        self.xmin, self.ymin, self.xmax, self.ymax = xmin, ymin, xmax, ymax
        self.ox = 7 + (-xmin) * self.step
        self.oy = 7 + (-ymin) * self.step
        self.d = fig((xmax - xmin) * self.step + 14, (ymax - ymin) * self.step + 14)
        axes(self.d, self.ox, self.oy, xmax, ymax, xmin, ymin, self.step, labels=labels)

    def T(self, p):
        return (self.ox + p[0] * self.step, self.oy + p[1] * self.step)

    def seg(self, a, b, **kw):
        seg(self.d, self.T(a), self.T(b), **kw)

    def dseg(self, a, b):
        seg(self.d, self.T(a), self.T(b), dash=(2.2, 1.8), color=FAINT, width=0.75)

    def poly(self, pts, fill=None, **kw):
        poly(self.d, [self.T(p) for p in pts], fill=fill, **kw)

    def pt(self, p, text, dx=1.6, dy=1.2, anchor="start", size=7.6):
        dot(self.d, self.T(p), r=0.85)
        lbl(self.d, self.T(p), text, dx, dy, size=size, anchor=anchor)

    def lbl(self, p, text, dx=0, dy=0, anchor="middle", size=7.6):
        lbl(self.d, self.T(p), text, dx, dy, size=size, anchor=anchor)

    def circle(self, c, r, color=INK, width=0.8, dash=None):
        cx, cy = self.T(c)
        circ = Circle(cx * mm, cy * mm, r * self.step * mm, fillColor=None,
                      strokeColor=color, strokeWidth=width)
        if dash:
            circ.strokeDashArray = dash
        self.d.add(circ)

    def line(self, k, b, color=INK, width=0.8, dash=None):
        """画直线 y=kx+b 落在网格框内的那一段。"""
        cands = []
        for x in (self.xmin, self.xmax):
            y = k * x + b
            if self.ymin - 1e-9 <= y <= self.ymax + 1e-9:
                cands.append((x, y))
        if k:
            for y in (self.ymin, self.ymax):
                x = (y - b) / k
                if self.xmin - 1e-9 <= x <= self.xmax + 1e-9:
                    cands.append((x, y))
        cands = sorted(set((round(x, 6), round(y, 6)) for x, y in cands))
        if len(cands) >= 2:
            self.seg(cands[0], cands[-1], color=color, width=width, dash=dash)

    def inside(self, p):
        return (self.xmin - 1e-9 <= p[0] <= self.xmax + 1e-9
                and self.ymin - 1e-9 <= p[1] <= self.ymax + 1e-9)

    def curve(self, fn, x0=None, x1=None, n=120, color=INK, width=0.9, dash=None):
        """画 y=fn(x) 在 [x0,x1] 上、落在网格框内的部分（教材里的抛物线）。
        越界的点不画；跨越框边的那一段用二分找到边界点接上，曲线不会戳出图外。"""
        x0 = self.xmin if x0 is None else x0
        x1 = self.xmax if x1 is None else x1
        pts = [(x0 + (x1 - x0) * i / n, fn(x0 + (x1 - x0) * i / n)) for i in range(n + 1)]
        run = []

        def flush():
            if len(run) >= 2:
                flat = []
                for q in run:
                    flat += list(_u(self.T(q)))
                ln = PolyLine(flat, strokeColor=color, strokeWidth=width)
                if dash:
                    ln.strokeDashArray = dash
                self.d.add(ln)
            run.clear()

        def edge(a, b):
            # a 在框内、b 在框外：二分逼近框边
            for _ in range(30):
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                if self.inside(m):
                    a = m
                else:
                    b = m
            return a

        for i, q in enumerate(pts):
            if self.inside(q):
                if not run and i > 0:
                    run.append(edge(q, pts[i - 1]))
                run.append(q)
            else:
                if run:
                    run.append(edge(run[-1], q))
                    flush()
        flush()

    def vline(self, x, color=None, dash=(2.2, 1.8)):
        """竖直虚线 x=常数（对称轴）。"""
        seg(self.d, self.T((x, self.ymin)), self.T((x, self.ymax)), dash=dash,
            color=color or FAINT, width=0.75)

    def hline(self, y, color=None, dash=(2.2, 1.8)):
        seg(self.d, self.T((self.xmin, y)), self.T((self.xmax, y)), dash=dash,
            color=color or FAINT, width=0.75)
