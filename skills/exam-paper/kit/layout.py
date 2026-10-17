"""试卷排版基础设施（A4 两栏中文试卷）。

几条硬规矩（违反了学生会直接跳过这道题）：
- 整页两栏，和学校发的单元测试卷一样（不是把作答框切两半）；
- 作答区只用横线，不要方框；
- 正文宋体：黑体 simhei 没有 ² ³ ½ 的字形，会印成方块；
- 分式画真分数线、根号盖住整个被开方式，不许用 ÷ 和 ^（÷ 有歧义）；
- 涉及图形的题必须配图。
"""

import hashlib
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether,
                                NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

# ReportLab 的 CJK 断行器（paragraph.cjkFragSplit）对内联 <img> 生成的空文字片段
# 直接调 ord('')，必崩。把该模块的 ord 换成能吃空串的版本，空片段当全角字符处理，
# 这样图片会被当成一个不可拆的整体参与断行。不打这个补丁就没法在中文段落里内联分式。
from reportlab.platypus import paragraph as _rl_paragraph

_rl_paragraph.ord = lambda x: ord(x) if x else 0x3000

import os

# 输出目录：环境变量 EXAM_PAPER_OUT，不设就是当前目录下的 outputs/
OUT = Path(os.environ.get("EXAM_PAPER_OUT") or (Path.cwd() / "outputs"))
OUT.mkdir(parents=True, exist_ok=True)


def _pick(candidates, what):
    for path, idx in candidates:
        if Path(path).exists():
            return path, idx
    raise SystemExit(f"找不到可用的{what}，请在候选列表里补一个路径。")


# 字体：默认用 Windows 自带的宋体/黑体；别的系统用环境变量 EXAM_PAPER_FONT_BODY / EXAM_PAPER_FONT_HEAD 指到
# TrueType 轮廓的中文字体文件（.ttf/.ttc；ReportLab 不支持 CFF 轮廓的 OTF，比如 Noto CJK 的 .otf）。
_env = lambda k: [(os.environ[k], 0)] if os.environ.get(k) else []
_BODY = _pick(_env("EXAM_PAPER_FONT_BODY") + [(r"C:\Windows\Fonts\simsun.ttc", 0), (r"C:\Windows\Fonts\simhei.ttf", 0)],
              "正文中文字体")
_HEAD = _pick(_env("EXAM_PAPER_FONT_HEAD") + [(r"C:\Windows\Fonts\simhei.ttf", 0), (r"C:\Windows\Fonts\simsun.ttc", 0)],
              "标题中文字体")
pdfmetrics.registerFont(TTFont("CN", _BODY[0], subfontIndex=_BODY[1]))
pdfmetrics.registerFont(TTFont("CNB", _HEAD[0], subfontIndex=_HEAD[1]))

# ---------- 配色 ----------
INK = colors.HexColor("#1a1d23")
MUTED = colors.HexColor("#767e8b")
RULE = colors.HexColor("#c6ccd4")          # 作答横线
HAIR = colors.HexColor("#dde1e6")          # 栏间线、网格
DEFAULT_ACCENT = "#33475b"                 # 每科换一个色，卷子之间一眼能分开

# ---------- 页面几何：整页两栏 ----------
PW, PH = A4
MX, TOP, BOTTOM = 14 * mm, 12 * mm, 13 * mm
GUT = 8 * mm
COLW = (PW - 2 * MX - GUT) / 2             # 每栏约 84mm
FULLW = PW - 2 * MX
HEADER_H = 27 * mm
LINE_GAP = 7 * mm                          # 作答横线行距，写中文舒服的高度

base = getSampleStyleSheet()
TITLE = ParagraphStyle("T", parent=base["Title"], fontName="CNB", fontSize=17.5, leading=23,
                       alignment=TA_CENTER, textColor=INK, spaceAfter=2)
SUB = ParagraphStyle("S", parent=base["Normal"], fontName="CN", fontSize=8.4, leading=12,
                     alignment=TA_CENTER, textColor=MUTED, spaceAfter=5)
# wordWrap=CJK：否则中文句子里唯一的半角空格（如题号后面那个）会成为唯一断点，
# 出现题号独占一行的情况。
BODY = ParagraphStyle("B", parent=base["BodyText"], fontName="CN", fontSize=9.3, leading=15,
                      textColor=INK, spaceAfter=2, wordWrap="CJK")
Q = ParagraphStyle("Q", parent=BODY, spaceBefore=4, spaceAfter=2)
OPT = ParagraphStyle("O", parent=BODY, fontSize=9.1, leading=14, spaceAfter=0)
FILL = ParagraphStyle("F", parent=BODY, spaceBefore=4, spaceAfter=13)
SMALL = ParagraphStyle("SM", parent=BODY, fontSize=8, leading=11.8, textColor=MUTED)
ANS = ParagraphStyle("A", parent=BODY, fontSize=8.5, leading=14.4, spaceAfter=4)
PASSAGE = ParagraphStyle("P", parent=BODY, fontSize=9.2, leading=16, firstLineIndent=18, spaceAfter=3)
NOTE = ParagraphStyle("N", parent=BODY, fontSize=8.6, leading=13, textColor=colors.HexColor("#3d4653"),
                      leftIndent=7, spaceBefore=1, spaceAfter=4)


# ---------- 文本 ----------
def _esc(text):
    t = escape(text).replace("\n", "<br/>")
    for tag in ("sub", "super", "b", "u"):
        t = t.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    if "@@" in t:
        t = _BADGE.sub(lambda m: _badge(m.group(1), m.group(2), m.group(3)), t)
    return t


# 二次元皮肤（anime.py）用的题号徽章和选项字母圈：源码里写占位符，这里换成内联小图。
# 和分式一样走「ReportLab 画 → PyMuPDF 栅格化 → <img>」，缓存在 _frac/。
_BADGE = re.compile(r"@@([QO]):([0-9A-Za-z]+):([0-9a-fA-F]{6})@@")


def _badge(kind, label, color, size=9.3):
    import pymupdf
    from reportlab.graphics.shapes import Circle as _Circle
    key = hashlib.md5(f"badge|{kind}|{label}|{color}|{size}".encode("utf-8")).hexdigest()[:16]
    FRACDIR.mkdir(parents=True, exist_ok=True)
    path = FRACDIR / f"b_{key}.png"
    col = colors.HexColor("#" + color)
    fs = size * (0.84 if kind == "Q" else 0.80)
    if kind == "Q":
        h = size * 1.40
        w = max(h, pdfmetrics.stringWidth(label, "CNB", fs) + size * 0.90)
        d = Drawing(w, h)
        d.add(Rect(0, 0, w, h, rx=h * 0.34, ry=h * 0.34, fillColor=col, strokeColor=None))
        d.add(String(w / 2, (h - fs * 0.70) / 2, label, fontName="CNB", fontSize=fs,
                     fillColor=colors.white, textAnchor="middle"))
    else:
        h = w = size * 1.30
        d = Drawing(w, h)
        d.add(_Circle(w / 2, h / 2, h / 2 - 0.6, fillColor=colors.white, strokeColor=col, strokeWidth=0.9))
        d.add(String(w / 2, (h - fs * 0.70) / 2, label, fontName="CNB", fontSize=fs,
                     fillColor=col, textAnchor="middle"))
    if not path.exists():
        doc = pymupdf.open("pdf", renderPDF.drawToString(d))
        doc[0].get_pixmap(dpi=600, alpha=True).save(path)
        doc.close()
    return (f'<img src="{path.as_posix()}" width="{w:.2f}" height="{h:.2f}" '
            f'valign="{size * 0.36 - h / 2:.2f}"/>')


# 「除号和 ^ 我根本看不懂，分式会出现很多歧义」。
# 题干里的公式走 mathline()，但答案是流动段落，Paragraph 塞不进 Drawing，
# 只能把分式渲染成小 PNG 再用 <img> 内联。下面这套东西把正文里的 A÷B
# 自动认出来换成真分数线，答案不用逐条改写。
FRACDIR = Path(os.environ.get("EXAM_PAPER_CACHE") or (Path.home() / ".cache" / "exam-paper-kit")) / "frac"
_ATOM = set("0123456789abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ.√πθαβγδ²³·ΩΔ")    # Ω、Δ：物理卷 6V÷15Ω、Q÷Δt


def _group_left(t, i):
    """t[i] 是右括号，返回配对左括号的下标；配不上返回 -1。"""
    depth = 0
    while i >= 0:
        if t[i] in ")）":
            depth += 1
        elif t[i] in "(（":
            depth -= 1
            if depth == 0:
                return i
        i -= 1
    return -1


def _group_right(t, i):
    """t[i] 是左括号，返回配对右括号的下标；配不上返回 -1。"""
    depth, n = 0, len(t)
    while i < n:
        if t[i] in "(（":
            depth += 1
        elif t[i] in ")）":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _left_operand(t, i):
    """从 ÷ 往左抓一个操作数，返回起始下标。遇到 + - × = ，。等就停。"""
    j = i
    while j > 0:
        c = t[j - 1]
        if c in ")）":
            k = _group_left(t, j - 1)
            if k < 0:
                break
            j = k
        elif c in _ATOM:
            j -= 1
        else:
            break
    return j


def _scan_right(t, i):
    """从下标 i 开始抓一个操作数（括号组或一串原子字符），返回结束下标（不含）。"""
    j, n = i, len(t)
    while j < n:
        c = t[j]
        if c in "(（":
            k = _group_right(t, j)
            return j if k < 0 else k + 1
        if c in _ATOM:
            j += 1
        else:
            break
    return j


def _right_operand(t, i):
    """从 ÷ 往右抓一个操作数。"""
    return _scan_right(t, i + 1)


def _unwrap(s):
    """去掉最外层括号：(2S-m) → 2S-m。"""
    s = s.strip()
    while len(s) > 1 and s[0] in "(（" and _group_right(s, 0) == len(s) - 1:
        s = s[1:-1].strip()
    return s


def _parse(expr):
    """把一段不含 ÷ 的表达式解析成 mathline 的 token 列表，√ 变成真根号。"""
    out, buf, i, n = [], "", 0, len(expr)
    while i < n:
        if expr[i] == "√":
            if buf:
                out.append(("t", buf))
                buf = ""
            j = _scan_right(expr, i + 1)
            out.append(("r", _unwrap(expr[i + 1:j])))
            i = j
        else:
            buf += expr[i]
            i += 1
    if buf:
        out.append(("t", buf))
    return out


def _math_img(tokens, size):
    """把一小段公式渲染成图，返回能内联进 Paragraph 的 <img> 标签。

    renderPM 在这台机器上没有后端（rlPyCairo 和 _renderPM 都没装），
    所以走 ReportLab 出矢量 PDF、再交给 PyMuPDF 光栅化，不引新依赖。
    """
    import pymupdf
    d = mathline(tokens, size=size, align="LEFT", pad=0.15 * mm)
    key = hashlib.md5(f"{tokens}|{size:.2f}".encode("utf-8")).hexdigest()[:16]
    FRACDIR.mkdir(parents=True, exist_ok=True)
    path = FRACDIR / f"{key}.png"
    if not path.exists():
        doc = pymupdf.open("pdf", renderPDF.drawToString(d))
        doc[0].get_pixmap(dpi=600, alpha=True).save(path)
        doc.close()
    # 图里的文字基线在离图底 size*0.85 处，让它和正文基线对齐
    return (f'<img src="{path.as_posix()}" width="{d.width:.2f}" '
            f'height="{d.height:.2f}" valign="{-size * 0.85:.2f}"/>')


def _sites(text):
    """找出正文里所有该换成公式图的片段，返回 [(起, 止, tokens), ...]。

    先定 ÷ 的地盘（它的操作数可能含 √），剩下的 √ 再单独处理，
    免得把某个分式分子里的根号提前吃掉。
    """
    spans = []
    i = text.find("÷")
    while i >= 0:
        lo, hi = _left_operand(text, i), _right_operand(text, i)
        num, den = text[lo:i], text[i + 1:hi]
        # hi 后面紧跟 <sub>/<super> 说明右操作数被下标截断了（P÷P<sub>y</sub>），这种别动。
        # 只看 "<" 会把 "2÷3<m<1" 这种不等式也拦下来（2026-09-19 教材里发现的）。
        if (num and den and "<" not in num + den and ">" not in num + den
                and not text.startswith(("<sub>", "<super>"), hi)):
            spans.append((lo, hi, [("f", _parse(_unwrap(num)), _parse(_unwrap(den)))]))
            i = text.find("÷", hi)
        else:
            i = text.find("÷", i + 1)
    taken = {k for lo, hi, _ in spans for k in range(lo, hi)}
    i = text.find("√")
    while i >= 0:
        j = _scan_right(text, i + 1)
        rad = text[i + 1:j]
        if i not in taken and rad and "<" not in rad and ">" not in rad:
            spans.append((i, j, [("r", _unwrap(rad))]))
            i = text.find("√", j)
        else:
            i = text.find("√", i + 1)
    return sorted(spans)


FRAC_ISSUES = []


def _lint_fracs(text, sites):
    """两种会静默排错的情况，发现就记下来并打到 stderr：
    ① ÷ 没被认成分式（操作数里带 <super>/<sub>，或者挨着汉字），印出来就是一个光秃秃的 ÷；
    ② 左操作数被标签截断（1.5×10<super>7</super>J÷0.5kg 会被排成 J 分之…）。
    这类式子要改写：先写符号式 q=Q÷m，再说「代入…得…」，别让带上标的数直接做除法。"""
    import sys
    covered = set()
    for lo, hi, _ in sites:
        covered.update(range(lo, hi))
        if text[:lo].endswith(("</super>", "</sub>")):      # 只认标签，ac>1÷2 里的大于号不算
            FRAC_ISSUES.append(("左操作数被标签截断", text))
            print("!! 分式左边被 <super>/<sub> 截断:", text[max(0, lo - 30):hi + 10], file=sys.stderr)
    for i, ch in enumerate(text):
        if ch == "÷" and i not in covered:
            FRAC_ISSUES.append(("÷ 没变成分式", text))
            print("!! ÷ 没变成分式:", text[max(0, i - 30):i + 20], file=sys.stderr)


def _markup(text, size=None):
    """转义正文但保留 <sub>/<super>/<b>；顺手把 A÷B 和 √X 换成真的分式与根号。

    宋体没有下标字形，x₁ 只能靠 <sub> 标记合成；
    宋体的 √ 又是个全角字形，√13 排出来是「√ 13」而且横杠盖不住——所以只能画图。
    操作数里带标记（<super> 之类）的不动，那种得手工改写。
    """
    if size is None or ("÷" not in text and "√" not in text):
        return _esc(text)
    fs = size * 0.76
    out, cur = [], 0
    sites = _sites(text)
    _lint_fracs(text, sites)
    for lo, hi, tokens in sites:
        out.append(_esc(text[cur:lo]))
        out.append(_math_img(tokens, fs))
        cur = hi
    out.append(_esc(text[cur:]))
    return "".join(out)


def p(text, style=BODY):
    return Paragraph(_markup(text, getattr(style, "fontSize", None)), style)


# ---------- 真分式 / 真根号 ----------
# 表达式写成 token 列表，交给 mathline() 画成一行公式：
#   ("t", "文字")            普通文字
#   ("f", 分子, 分母)         真分数线；分子分母可以是字符串，也可以是嵌套的 token 列表
#   ("r", 被开方式)           根号，横杠盖住整个被开方式；同样可以嵌套
def _w(t, size):
    return pdfmetrics.stringWidth(t, "CN", size)


def _seq_w(seq, size):
    if isinstance(seq, str):
        return _w(seq, size)
    return sum(_tok_w(t, size) for t in seq)


def _tok_w(tok, size):
    if tok[0] == "t":
        return _w(tok[1], size)
    if tok[0] == "f":
        fs = size * 0.86
        return max(_seq_w(tok[1], fs), _seq_w(tok[2], fs)) + size * 0.44
    if tok[0] == "r":
        return size * 0.62 + _seq_w(tok[1], size) + size * 0.22
    if tok[0] == "s":                      # ("s", 主体, 下标)：教材公式里的 x₁ 这类
        return _w(tok[1], size) + _w(tok[2], size * 0.7)
    raise ValueError(tok)


def _draw_seq(d, seq, x, yb, size):
    if isinstance(seq, str):
        d.add(String(x, yb, seq, fontName="CN", fontSize=size, fillColor=INK))
        return
    for tok in seq:
        _draw_tok(d, tok, x, yb, size)
        x += _tok_w(tok, size)


def _draw_tok(d, tok, x, yb, size):
    tw = _tok_w(tok, size)
    if tok[0] == "t":
        d.add(String(x, yb, tok[1], fontName="CN", fontSize=size, fillColor=INK))
    elif tok[0] == "f":
        fs = size * 0.86
        bar = yb + size * 0.30
        d.add(Line(x + size * 0.10, bar, x + tw - size * 0.10, bar,
                   strokeColor=INK, strokeWidth=0.6))
        for seq, dy in ((tok[1], size * 0.16), (tok[2], -size * 0.86)):
            sx = x + (tw - _seq_w(seq, fs)) / 2
            _draw_seq(d, seq, sx, bar + dy, fs)
    elif tok[0] == "r":
        iw = _seq_w(tok[1], size)
        top = yb + size * 0.78
        d.add(PolyLine([x + size * 0.04, yb + size * 0.30,
                        x + size * 0.20, yb + size * 0.14,
                        x + size * 0.42, top,
                        x + size * 0.62 + iw + size * 0.16, top],
                       strokeColor=INK, strokeWidth=0.7))
        _draw_seq(d, tok[1], x + size * 0.62, yb, size)
    elif tok[0] == "s":
        d.add(String(x, yb, tok[1], fontName="CN", fontSize=size, fillColor=INK))
        d.add(String(x + _w(tok[1], size), yb - size * 0.22, tok[2], fontName="CN",
                     fontSize=size * 0.7, fillColor=INK))


def mathline(tokens, size=10.5, align="CENTER", pad=1.2 * mm):
    """把 token 列表画成一行公式。分式和根号都是真画出来的，不是拼字符。"""
    w = sum(_tok_w(t, size) for t in tokens)
    above, below = size * 1.15, size * 0.85
    d = Drawing(w + 2 * pad, above + below)
    d.hAlign = align
    x = pad
    for tok in tokens:
        _draw_tok(d, tok, x, below, size)
        x += _tok_w(tok, size)
    return d


# ---------- 作答区：只有横线，没有框 ----------
def ruled(lines=4, label=None, width=None):
    w = COLW if width is None else width
    head = 4.4 * mm if label else 0
    h = head + LINE_GAP * lines
    d = Drawing(w, h)
    if label:
        d.add(String(0, h - 3.1 * mm, label, fontName="CN", fontSize=6.6, fillColor=MUTED))
    y = h - head - LINE_GAP + 1.8 * mm
    for _ in range(lines):
        d.add(Line(0, y, w, y, strokeColor=RULE, strokeWidth=0.35))
        y -= LINE_GAP
    return d


# ---------- 图 ----------
def dim(d, x0, y0, x1, y1, text):
    """尺寸线：两端短垂线 + 中点标注。"""
    d.add(Line(x0, y0, x1, y1, strokeColor=INK, strokeWidth=0.4))
    if y0 == y1:
        for x in (x0, x1):
            d.add(Line(x, y0 - 1 * mm, x, y0 + 1 * mm, strokeColor=INK, strokeWidth=0.4))
        d.add(String((x0 + x1) / 2, y0 + 1.4 * mm, text, fontName="CN", fontSize=6.5,
                     fillColor=INK, textAnchor="middle"))
    else:
        for y in (y0, y1):
            d.add(Line(x0 - 1 * mm, y, x0 + 1 * mm, y, strokeColor=INK, strokeWidth=0.4))
        d.add(String(x0 - 1.8 * mm, (y0 + y1) / 2 - 1.1 * mm, text, fontName="CN", fontSize=6.5,
                     fillColor=INK, textAnchor="end"))


def grid(xlab="x", ylab="y", w=None, h=42 * mm, step=5 * mm):
    """带刻度的直角坐标网格，供画草图、描点。"""
    w = COLW - 4 * mm if w is None else w
    d = Drawing(w, h)
    d.hAlign = "CENTER"
    ox, oy = round(w / 2 / step) * step, round(h / 2 / step) * step
    x = step
    while x < w:
        d.add(Line(x, 0, x, h, strokeColor=HAIR, strokeWidth=0.25))
        x += step
    y = step
    while y < h:
        d.add(Line(0, y, w, y, strokeColor=HAIR, strokeWidth=0.25))
        y += step
    d.add(Line(0, oy, w, oy, strokeColor=INK, strokeWidth=0.6))
    d.add(Line(ox, 0, ox, h, strokeColor=INK, strokeWidth=0.6))
    for i in range(1, int(ox / step)):
        d.add(String(ox - i * step, oy - 3.4 * mm, str(-i), fontName="CN", fontSize=5.5,
                     fillColor=INK, textAnchor="middle"))
    for i in range(1, int((w - ox) / step)):
        d.add(String(ox + i * step, oy - 3.4 * mm, str(i), fontName="CN", fontSize=5.5,
                     fillColor=INK, textAnchor="middle"))
    for i in range(1, int(oy / step)):
        d.add(String(ox - 1.4 * mm, oy - i * step - 0.8 * mm, str(-i), fontName="CN", fontSize=5.5,
                     fillColor=INK, textAnchor="end"))
    for i in range(1, int((h - oy) / step)):
        d.add(String(ox - 1.4 * mm, oy + i * step - 0.8 * mm, str(i), fontName="CN", fontSize=5.5,
                     fillColor=INK, textAnchor="end"))
    d.add(String(w - 2.5 * mm, oy + 1.4 * mm, xlab, fontName="CN", fontSize=6.5, fillColor=INK))
    d.add(String(ox + 1.4 * mm, h - 3.5 * mm, ylab, fontName="CN", fontSize=6.5, fillColor=INK))
    d.add(String(ox - 1.4 * mm, oy - 3.4 * mm, "O", fontName="CN", fontSize=6, fillColor=INK,
                 textAnchor="end"))
    return d


# ---------- 题型 ----------
# 章节标题不能自己待在栏底。Table 的 keepWithNext 在这里不生效，CondPageBreak 也只能
# 保证"下面还剩多少空间"，挡不住后面跟一个更高的 KeepTogether。所以改成：先把标题放进
# story，再由紧随其后的 qblock / choice_q 把它取回来，和第一道题绑成一个整体。
_pending = []


def _take_pending(story):
    """若 story 末尾正是刚加的章节标题，取回它，交给调用方一起 KeepTogether。"""
    out = []
    if _pending and _pending[0][0] is story and story and story[-1] is _pending[0][1]:
        out = [story.pop()]
    _pending.clear()
    return out


def section(story, text, accent=DEFAULT_ACCENT):
    """章节标题：左侧一个小色块 + 标题文字，下面一条细线。"""
    c = colors.HexColor(accent)
    bar = Drawing(3.2, 11)
    bar.add(Rect(0, 0, 3.2, 11, fillColor=c, strokeColor=None))
    lab = Paragraph(_markup(text), ParagraphStyle("Sec", parent=BODY, fontName="CNB", fontSize=11.5,
                                                  leading=14, textColor=c, spaceAfter=0))
    t = Table([[bar, lab]], colWidths=[6, COLW - 6])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (0, 0), (0, 0), 4),
        ("LEFTPADDING", (1, 0), (1, 0), 0), ("RIGHTPADDING", (1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor(accent + "44")),
    ]))
    story.append(t)
    _pending.clear()
    _pending.append((story, t))


def choice_q(story, text, options, per_row=2, fig=None):
    """选择题。选项必须用表格排，不能用空格——ReportLab 会把连续空白（含全角空格）压成一个。"""
    parts = _take_pending(story) + [p(text, Q)]
    if fig is not None:
        parts += [fig, Spacer(1, 1 * mm)]
    rows = [options[i:i + per_row] for i in range(0, len(options), per_row)]
    rows = [r + [""] * (per_row - len(r)) for r in rows]
    t = Table([[p(o, OPT) for o in r] for r in rows], colWidths=[COLW / per_row] * per_row)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    parts.append(t)
    story.append(KeepTogether(parts))


_PTS = re.compile(r"[（(](\d+)\s*分[)）]")


class Gap(Flowable):
    """作答留白。高度全放在 spaceBefore 里，因为 ReportLab 在栏首会丢掉 spaceBefore，
    所以留白落到栏首时自动消失——否则末题的留白会溢出成一整页纯白。
    不要设 _ZEROSIZE：那会让 Frame 把 spaceBefore 换成上一个流的 spaceAfter，留白就没了。"""

    def __init__(self, h):
        Flowable.__init__(self)
        self.width = 0
        self.height = 0
        self.spaceBefore = h

    def wrap(self, aW, aH):
        return 0, 0

    def draw(self):
        pass


def _answer_space(text, lines):
    """作答留白高度。要删的是作答区的**边界线**，
    不是作答区本身——所以留白照留，只是不画横线也不画框。
    没显式给 lines 就按题干里的分值折算，分值越高留得越多。"""
    if lines:
        return lines * LINE_GAP
    m = _PTS.search(text)
    if not m:
        return 0
    return min(int(m.group(1)) * 3.5 * mm, 96 * mm)


def qblock(story, text, lines=0, label=None, figs=(), maths=(), note=None, keep=0):
    """解答题：题干 →（提示）→（公式）→（配图）→ 空白作答区。

    只有题干（和提示）绑在一起，图和留白自由流动。图放大后每张 60mm 左右，
    和题干绑定会让跳栏浪费翻倍，所以图单独走。
    以前是题干＋全部图＋前 3 行留白一起 KeepTogether，图放大以后三张图加题干
    装不进一栏，整题跳到下一栏，前一栏空一大片（2026-09-16 第一次排北京卷就是这样）。
    留白拆成 4 行一块（Gap 靠 spaceBefore 在栏首自动塌掉），别改回整块 KeepTogether。

    figs 里可以混放 Drawing、Table 或它们的列表（BIG 模式下 figrow 返回列表）；
    裸 Drawing 会按 BIG 规则放大。
    """
    from reportlab.graphics.shapes import Drawing as _Drawing
    import geometry as _geo
    parts = _take_pending(story) + [p(text, Q)]
    if note:
        parts.append(p(note, NOTE))
    for m in maths:
        parts += [m, Spacer(1, 1 * mm)]
    flat = []
    for fg in figs:
        for one in (fg if isinstance(fg, (list, tuple)) else [fg]):
            if _geo.BIG_FIGS and isinstance(one, _Drawing):
                one = _geo.big_scaled(one)
            flat.append(one)
    gap = _answer_space(text, lines)
    if flat:
        story.append(KeepTogether(parts))
        for fg in flat:
            story += [fg, Spacer(1, 1 * mm)]
        rest = gap
    else:
        head = min(gap, 3 * LINE_GAP)
        if head:
            parts.append(Spacer(1, head))
        story.append(KeepTogether(parts))
        rest = gap - head
    while rest > 0:
        chunk = min(rest, 4 * LINE_GAP)
        story.append(Gap(chunk))
        rest -= chunk
    story.append(Gap(4.5 * mm))


def page_break(story):
    """答案另起一页。先把末题后面的留白扔掉：留白挤不进当前栏就会自己开一页，
    到了页首又整个塌掉，结果是一整页纯白。答案页前面一律用这个，不要直接 PageBreak()。"""
    while story and isinstance(story[-1], (Gap, Spacer)):
        story.pop()
    story.append(PageBreak())


# ---------- 文档 ----------
def _decor(canvas, doc, label, accent):
    canvas.saveState()
    canvas.setStrokeColor(HAIR)
    canvas.setLineWidth(0.4)
    xm = MX + COLW + GUT / 2
    canvas.line(xm, BOTTOM + 2 * mm, xm, PH - TOP - 2 * mm)
    canvas.setStrokeColor(colors.HexColor(accent))
    canvas.setLineWidth(0.9)
    canvas.line(MX, 9.6 * mm, MX + 13 * mm, 9.6 * mm)
    canvas.setFont("CN", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(MX + 15 * mm, 9 * mm, label)
    canvas.drawRightString(PW - MX, 9 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def make_doc(path, label, accent=DEFAULT_ACCENT):
    """首页顶部留一条通栏放标题，其余都是两栏。"""
    d = BaseDocTemplate(str(path), pagesize=A4, leftMargin=MX, rightMargin=MX,
                        topMargin=TOP, bottomMargin=BOTTOM, title=label, author="")
    colh = PH - TOP - BOTTOM
    on = lambda c, x: _decor(c, x, label, accent)
    f = dict(leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    first = PageTemplate(id="first", onPage=on, frames=[
        Frame(MX, PH - TOP - HEADER_H, FULLW, HEADER_H, id="head", **f),
        Frame(MX, BOTTOM, COLW, colh - HEADER_H, id="l", **f),
        Frame(MX + COLW + GUT, BOTTOM, COLW, colh - HEADER_H, id="r", **f),
    ])
    later = PageTemplate(id="later", onPage=on, frames=[
        Frame(MX, BOTTOM, COLW, colh, id="l", **f),
        Frame(MX + COLW + GUT, BOTTOM, COLW, colh, id="r", **f),
    ])
    d.addPageTemplates([first, later])
    return d


def header(story, title, subtitle, score, minutes, accent=DEFAULT_ACCENT):
    story.append(p(title, TITLE))
    story.append(p(subtitle, SUB))
    t = Table([[p("姓名", SMALL), "", p("班级", SMALL), "", p(f"时间 {minutes} 分钟", SMALL),
                p(f"满分 {score} 分", SMALL)]],
              colWidths=[FULLW * 0.06, FULLW * 0.26, FULLW * 0.06, FULLW * 0.22,
                         FULLW * 0.20, FULLW * 0.20])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBELOW", (1, 0), (1, 0), 0.5, RULE),
        ("LINEBELOW", (3, 0), (3, 0), 0.5, RULE),
        ("LINEABOVE", (0, 0), (-1, -1), 1.1, colors.HexColor(accent)),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(NextPageTemplate("later"))


def _selfcheck():
    """转义和公式宽度是这里仅有的两处会静默出错的逻辑。"""
    assert _markup("k<1") == "k&lt;1"
    assert _markup("a&b") == "a&amp;b"
    assert _markup("x<sub>1</sub>²") == "x<sub>1</sub>²"
    assert _tok_w(("t", "x="), 10) > 0
    assert _tok_w(("f", "1", "2"), 10) > _w("1", 8.6)
    assert _tok_w(("r", "17"), 10) > _w("17", 10)
    assert ruled(3).height == 3 * LINE_GAP          # 无标签时不留标签行高
    assert _answer_space("求 AE 的长。（26分）", 0) == 26 * 3.5 * mm
    assert _answer_space("填空。", 0) == 0
    assert _answer_space("（99分）", 0) == 96 * mm       # 封顶，别把一栏撑爆
    assert Gap(20).wrap(100, 100) == (0, 0)             # 留白高度只走 spaceBefore
    assert Gap(20).spaceBefore == 20
    assert not getattr(Gap(20), "_ZEROSIZE", False)      # 设了它 Frame 会吃掉留白
