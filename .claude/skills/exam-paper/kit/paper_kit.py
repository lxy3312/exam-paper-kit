"""出卷工具包：题目按 id 存、题号按位置自动给、试卷和答案各出一个 PDF。

- 每道题是 (id, fn)，fn(s, color) 往 story 里放这道题；卷面题号、图注里的「第N题」、答案页题号都按位置自动给，
  所以调顺序只要挪列表里的条目（scripts/reorder.py）。
- emit() 在每道题前面放一个零高度的 Mark，scripts/packsim.py 靠它把 story 切成一题一块来模拟排版、找最省空白的顺序。
- build_doc() 出 PDF（水印可选）。
用法见 SKILL.md 和 templates/build_template.py。
"""

import re

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, KeepTogether, Paragraph, Spacer, Table, TableStyle

import skin as A
import layout as LY
import skin_q as K
from skin import Card, qnum
from layout import ANS, INK, Q, SMALL, p

TCELL = Q.clone("kit_tcell", alignment=TA_CENTER, spaceBefore=0, spaceAfter=0, fontSize=8.8, leading=12)
STAGE_COLORS = A.STAGE_COLORS

NUM = [None]        # 当前题号（emit 设置）
ORDER = {}          # id → 卷面题号


# ---------------------------------------------------------------- 零件
class Mark(Flowable):
    """零高度标记：kind="sec" 是关卡头，kind="q" 是一道题（qid、slot）。只给 packsim 切块用，不画任何东西。"""

    def __init__(self, kind, qid=None, slot=None):
        Flowable.__init__(self)
        self.kind, self.qid, self.slot = kind, qid, slot
        self.width = self.height = 0

    def wrap(self, aW, aH):
        return 0, 0

    def draw(self):
        pass


class Note(Flowable):
    """提示气泡（没有头像）。"""

    def __init__(self, text, color=A.PINK, style=A.TIP):
        Flowable.__init__(self)
        self.color = color
        self.para = Paragraph(LY._markup(text, style.fontSize), style)

    def wrap(self, aW, aH):
        self.w = aW
        _, self.ph = self.para.wrap(aW - 7 * mm, aH)
        self.h = max(10 * mm, self.ph + 5 * mm)
        return aW, self.h + 3 * mm

    def draw(self):
        c = self.canv
        y = 1.5 * mm
        c.setFillColor(A.H(A.BUBBLE_BG or A.LIGHT.get(self.color, A.PINK_L)))
        c.setStrokeColor(A.H(self.color))
        c.setLineWidth(0.7)
        c.roundRect(0, y, self.w, self.h, 3.0 * mm, stroke=1, fill=1)
        A.canv_sparkle(c, self.w - 3.4 * mm, y + self.h - 3.4 * mm, 1.3 * mm, A.DECO[1])
        self.para.drawOn(c, 3.5 * mm, y + (self.h - self.ph) / 2)


def paras(stem):
    """题干按 \\n 分段：第一段用 Q 样式，后面的小问用 SUBQ（不用 <br/>，写满一行时会多空一行）。"""
    first, *more = stem.split("\n")
    return [p(first, Q)] + [p(t, K.SUBQ) for t in more]


def table(rows, widths):
    """题干里夹的表格（带框线）。widths 单位 mm。"""
    t = Table([[p(c, TCELL) for c in r] for r in rows], colWidths=[w * mm for w in widths])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, INK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1)]))
    return [Spacer(1, 1.2 * mm), t, Spacer(1, 1.2 * mm)]


def _head(stem, color):
    stem = K.blanks(stem)
    n, rest = K._num(stem)
    if NUM[0] is not None:
        n = str(NUM[0])
    return n, qnum(n, color) + rest


def _lab(n):
    return lambda cap: re.sub(r"^第\d+题", f"第{n}题", cap)


def _set_slot(s, slot):
    for f in reversed(s):
        if isinstance(f, Mark):
            if f.slot is None:
                f.slot = slot
            return


def _with_tab(ps, tab):
    if tab:
        at, rows, widths = tab
        ps[at + 1:at + 1] = table(rows, widths)
    return ps


# ---------------------------------------------------------------- 题型
def cq(s, stem, opts, color, fig=None, per_row=None, maxh=34 * mm, tab=None):
    """选择题：题干（结论可以用 \\n 分行）＋图＋选项，一整块不拆。per_row 不给就按选项长短自动 4/2/1。"""
    n, stem = _head(stem, color)
    o2 = [A.opt(o[0], color) + o[3:] for o in opts]
    if per_row is None:
        L = max(K._plain_len(o[3:]) for o in opts)
        per_row = 4 if L <= 8 else (2 if L <= 22 else 1)
    parts = LY._take_pending(s) + _with_tab(paras(stem), tab)
    if fig:
        parts.append(Card(fig(), f"第{n}题", color, maxh=maxh, smax=1.1))
    parts.append(K._opt_table(o2, per_row))
    s.append(K.FitBlock(parts))
    _set_slot(s, "choice")


def fill(s, stem, color, fig=None, tab=None, maxh=34 * mm):
    """填空题：题干＋图一整块。横线写「＿＿＿＿」，会换成不会被拆开的半角下划线。"""
    n, stem = _head(stem, color)
    parts = LY._take_pending(s) + _with_tab(paras(stem), tab)
    if fig:
        parts.append(Card(fig(), f"第{n}题", color, maxh=maxh, smax=1.1))
    parts.append(Spacer(1, 3 * mm))
    s.append(K.FitBlock(parts))
    _set_slot(s, "fill")


def qb(s, stem, lines, color, figs=(), spare=(), tab=None, maxh=54 * mm, spare_maxh=46 * mm, groups=None,
       after=()):
    """大题。
    figs：[(画图函数, "第N题 图1"[, 最大高度]), ...]，和题干绑在一起；spare：备用图，可以单独流到下一栏。
    lines：作答留白行数（0 就按题干里的分值折算）。头 3 行留白和题干绑在一起，剩下的拆成 4 行一块自由流动。
    groups=[(段数, [图序号]), ...]：长题按小问切块，每块带着自己要看的图，块与块之间可以换栏。
    after：题目后面接着放的东西（比如一个 Note）。"""
    n, stem = _head(stem, color)
    ps = _with_tab(paras(stem), tab)
    lab = _lab(n)
    cards = [Card(it[0](), lab(it[1]), color, maxh=it[2] if len(it) > 2 else maxh, smax=1.1) for it in figs]
    gap = LY._answer_space(stem, lines)
    head = min(gap, 3 * LY.LINE_GAP)
    if groups:
        k = 0
        for gi, (cnt, idx) in enumerate(groups):
            part = ps[k:k + cnt] + [cards[i] for i in idx]
            k += cnt
            if gi == 0:
                part = LY._take_pending(s) + part
            if gi == len(groups) - 1:
                part = part + [Spacer(1, 1 * mm + head)]
            s.append(K.FitBlock(part))
    else:
        s.append(K.FitBlock(LY._take_pending(s) + ps + cards + [Spacer(1, 1 * mm + head)]))
    for f, cap in spare:
        s.append(Card(f(), lab(cap), color, maxh=spare_maxh, smax=1.0))
    rest = gap - head
    while rest > 0:
        chunk = min(rest, 4 * LY.LINE_GAP)
        s.append(LY.Gap(chunk))
        rest -= chunk
    s.append(LY.Gap(4.5 * mm))
    m = re.search(r"（(\d+)分）", stem)
    _set_slot(s, f"{m.group(1)}分" if m else "big")


# ---------------------------------------------------------------- 卷面结构
def banner(s, title, ribbon, chips, score, minutes, bubble=""):
    """首页横幅：右边是分数印章。chips=[("第21章 一元二次方程", A.SKY), ...]。"""
    A.header(s, A.Banner(title, ribbon, chips, [f"满分 {score}", f"{minutes}分钟"], bubble, stamp=str(score)))


def section(s, no, title, sub, color, note=None, boss=False):
    """关卡头（STAGE 01 / BOSS ★），note 是挂在下面的一句提示（可选）。"""
    s.append(Mark("sec"))
    A.stage(s, no, title, sub, color, body=Note(note, color) if note else None, boss=boss)


def emit(s, questions, base, color):
    """按顺序放题：questions=[(id, fn), ...]，从 base 号开始编。"""
    for k, (qid, fn) in enumerate(questions):
        NUM[0] = base + k
        ORDER[qid] = base + k
        s.append(Mark("q", qid))
        fn(s, color)
    NUM[0] = None


def number(qid):
    return ORDER[qid]


def nums(*ids):
    """一组题目 id → 「2、6、14」（答案来源说明里用）。"""
    return "、".join(str(number(q)) for q in sorted(ids, key=number))


def key(questions, answers):
    """选择题答案串：每道答案的第一个字母，5 个一组。"""
    ks = "".join(answers[q[0]][0] for q in questions)
    return " ".join(ks[i:i + 5] for i in range(0, len(ks), 5))


def answer_story(title, sub, parts, answers, note=None, tail=None, color=A.MINT):
    """答案 story。parts=[("<b>一、单项选择题</b>（每题2分）", 题目列表), ...]，题号用卷面上的。"""
    s = []
    A.stage(s, "答", title, sub, color, top="CLEAR")
    if note:
        s.append(Note(note, A.LAV))
    first = True
    for head, qs in parts:
        rows = [head] + [f"{number(q[0])}. {answers[q[0]]}" for q in qs]
        for r in rows:
            para = p(r, ANS)
            if first:
                s.append(KeepTogether(LY._take_pending(s) + [para]))
                first = False
            else:
                s.append(para)
    if tail:
        s.append(p(tail, SMALL))
    return s


# ---------------------------------------------------------------- 出 PDF
def setup(extra_cannot_start="·"):
    """打开断行补丁：全角「，；：？！」等不放行首，公式小图不挂行尾；再多拦几个字符（默认「·」）。
    会改 ReportLab 的全局表，所以 build_all 里用它的卷子要排在老卷子后面。"""
    K.enable_kinsoku()
    from reportlab.lib import textsplit as _rlt
    from reportlab.platypus import paragraph as _rlp
    for _m in (_rlp, _rlt):
        cur = str(_m.ALL_CANNOT_START)
        add = "".join(ch for ch in extra_cannot_start if ch not in cur)
        if add:
            _m.ALL_CANNOT_START = K._CannotStart(cur + add)
    ORDER.clear()


def build_doc(path, label, story, accent=A.PINK, watermark=None, banner=True):
    """出一个 PDF。banner=False 时第一页不留横幅位（答案文件用）。"""
    doc = A.make_doc(path, label, accent, watermark=watermark)
    if not banner:
        doc._firstPageTemplateIndex = 1
    doc.build(story)
    return path
