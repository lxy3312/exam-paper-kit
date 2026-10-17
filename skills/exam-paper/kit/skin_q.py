"""卡片皮肤下的题型零件：FitBlock（不拆的整块，放不下先缩图再换栏）、断行禁则、填空横线、选项表格。

两条硬规矩：
1. 题干和选项、题干和图绝不拆开。选择题「题干＋图＋选项」一整块；大题「题干＋要看的图」一整块，
   作答留白照常流动。只有「备用图」可以单独流到下一栏——它是草稿纸，不是题目的一部分。宁愿留空也不拆。
2. 不能嵌套 KeepTogether：合并时取出前一块的 parts 重新建一个。
"""

import re

from reportlab.lib.units import mm
from reportlab.platypus import Flowable, KeepTogether, Spacer, Table, TableStyle

import skin as A
import layout as LY
from skin import Card, opt, qnum
from layout import COLW, FILL, Q, p, qblock

# 小问另起一段，不用 <br/>：题干正好写满一行时 <br/> 会再空出一整行
SUBQ = Q.clone("subq", spaceBefore=0, spaceAfter=0)

TAG = "小剧场"

# 行首禁则：ReportLab 的 CJK 断行只拦半角标点和「、。」，全角的「，；：？！」照样会跑到行首
# 。把它们加进「不能出现在行首」的表，宁可挂在行尾。
# 两条路径都要补：多片段段落走 paragraph.cjkFragSplit，单片段（纯文字）走 textsplit.wordSplit。
from reportlab.lib import textsplit as _rlt
from reportlab.platypus import paragraph as _rlp
_MORE = "，；：？！）》〉」』…—"


class _CannotStart(str):
    """内联公式图在断行器里是个空字符串，而 '' in 任何字符串 都是 True，
    于是公式图永远被当成「不能放行首」的标点挂在行尾，后面的「，。」反倒被挤到下一行行首。
    空串一律不算。"""

    def __contains__(self, ch):
        return bool(ch) and str.__contains__(self, ch)


def enable_kinsoku():
    """打开上面两条断行补丁。build() 里调用，不在 import 时打——build_all 一个进程里跑所有卷子，
    import 时就打的话，同一进程里别的卷子断行也会跟着变。"""
    for _m in (_rlp, _rlt):
        if not isinstance(_m.ALL_CANNOT_START, _CannotStart):
            _m.ALL_CANNOT_START = _CannotStart(_m.ALL_CANNOT_START + _MORE)


def blanks(text):
    """填空横线：全角「＿」中间会被断行拆开（一半在行尾一半在下一行），换成半角下划线，
    一串半角字符 ReportLab 当成一个词，不会拆。"""
    return re.sub("＿+", lambda m: "_" * (2 * len(m.group())), text)


def _num(stem):
    """「12. 题干」或「38.（出处）题干」→ ("12", "题干")。"""
    m = re.match(r"(\d+)\.\s?(.*)", stem, re.S)
    return m.group(1), m.group(2)


def _plain_len(s):
    """选项的大致显示宽度（去掉标记，分式按分子分母里长的那个算）。"""
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"@@[^@]+@@ ?", "", s)
    w = 0
    for part in re.split(r"(\S+÷\S+)", s):
        if "÷" in part:
            a, b = part.split("÷", 1)
            w += max(len(a), len(b)) + 1
        else:
            w += sum(2 if ord(ch) > 0x2E80 or ch in "×÷≤≥≠±°∠△⊙√π" else 1 for ch in part)   # 宋体里这些是全角宽
    return w


class FitBlock(Flowable):
    """一整块（题干＋图卡＋选项……），永远不拆开。栏里剩的地方差一点点放不下时，先把块里的图卡
    一起缩小（最多缩到 MIN_K），还放不下才整块挪到下一栏。
    以前用 KeepTogether，差 1cm 也整块跳栏，栏底空七八厘米。
    图不能缩太狠：图太小就没法在上面画辅助线。"""

    MIN_K = 0.78

    def __init__(self, parts, bindable=False):
        Flowable.__init__(self)
        self.parts = list(parts)
        self.cards = [x for x in self.parts if isinstance(x, Card)]
        self._bindable = bindable

    def _measure(self, aW, k):
        for c in self.cards:
            c.k = k
        rows, total = [], 0
        for i, f in enumerate(self.parts):
            _, h = f.wrap(aW, 10 ** 6)
            sb = f.getSpaceBefore() if i else 0
            sa = f.getSpaceAfter() if i < len(self.parts) - 1 else 0
            rows.append((f, h, sb, sa))
            total += sb + h + sa
        return rows, total

    def wrap(self, aW, aH):
        self.w = aW
        k = 1.0
        rows, h = self._measure(aW, k)
        while h > aH and self.cards and k > self.MIN_K + 1e-9:
            k = max(self.MIN_K, k - 0.04)
            rows, h = self._measure(aW, k)
        if h > aH and self.cards:           # 缩到底也放不下：恢复原大，整块去下一栏
            rows, h = self._measure(aW, 1.0)
        self.rows, self.h = rows, h
        return aW, h

    def split(self, aW, aH):
        return []

    def getSpaceBefore(self):
        return self.parts[0].getSpaceBefore() if self.parts else 0

    def draw(self):
        y = self.h
        for f, h, sb, sa in self.rows:
            y -= sb + h
            f.drawOn(self.canv, 0, y)
            y -= sa


def _opt_table(o2, per_row):
    rows = [o2[i:i + per_row] for i in range(0, len(o2), per_row)]
    rows = [r + [""] * (per_row - len(r)) for r in rows]
    t = Table([[p(o, LY.OPT) for o in r] for r in rows], colWidths=[COLW / per_row] * per_row)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                           ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def cq(s, stem, opts, color, fig=None, per_row=None, maxh=42 * mm):
    """选择题：题号徽章、选项字母圈、配图卡片，题干＋图＋选项一整块。
    选项短就一行排四个或两个（数学选项大多是一个式子，一行一个太浪费）。"""
    n, rest = _num(stem)
    o2 = [opt(o[0], color) + o[3:] for o in opts]
    if per_row is None:
        L = max(_plain_len(o[3:]) for o in opts)
        per_row = 4 if L <= 8 else (2 if L <= 22 else 1)
    parts = LY._take_pending(s) + [p(qnum(n, color) + blanks(rest), Q)]
    if fig:
        parts.append(Card(fig(), f"第{n}题", color, maxh=maxh, smax=1.1))
    parts.append(_opt_table(o2, per_row))
    s.append(FitBlock(parts))


def fill(s, stem, color, fig=None, maxh=46 * mm):
    """填空题。带图时题干用 Q 样式：FILL 的 13pt 段后距会落在题干和图卡之间，每道白多 4mm。"""
    n, rest = _num(stem)
    parts = LY._take_pending(s) + [p(qnum(n, color) + blanks(rest), Q if fig else FILL)]
    if fig:
        parts.append(Card(fig(), f"第{n}题", color, maxh=maxh, smax=1.1))
    s.append(FitBlock(parts))


def answer_gap(s, stem, lines):
    """作答留白，和 layout.qblock 的规则一样：按分值或行数折算，拆成 4 行一块，栏首自动塌掉。"""
    rest = LY._answer_space(stem, lines)
    while rest > 0:
        chunk = min(rest, 4 * LY.LINE_GAP)
        s.append(LY.Gap(chunk))
        rest -= chunk
    s.append(LY.Gap(4.5 * mm))


def qb(s, stem, lines=0, color=A.PINK, figs=(), spare=(), maxh=54 * mm, spare_maxh=46 * mm):
    """大题：题号徽章；figs 是 [(生成图的函数, 图注), ...]，和题干绑在一起；
    spare 是备用图，单独流动（可以落到下一栏）。
    作答留白的头 3 行也放进这一块：FitBlock 缩图挤进栏底时，留白不能全流到下一栏顶上塌掉。"""
    n = None
    stem = blanks(stem)
    if stem[:1].isdigit():
        n, rest = _num(stem)
        stem = qnum(n, color) + rest
    first, *more = stem.split("\n")
    paras = [p(first, Q)] + [p(t, SUBQ) for t in more]
    cards = [Card(f(), cap, color, maxh=maxh, smax=1.1) for f, cap in figs]
    gap = LY._answer_space(stem, lines)
    head = min(gap, 3 * LY.LINE_GAP)
    s.append(FitBlock(LY._take_pending(s) + paras + cards + [Spacer(1, 1 * mm + head)]))
    for f, cap in spare:
        s.append(Card(f(), cap, color, maxh=spare_maxh, smax=1.0))
    rest = gap - head
    while rest > 0:
        chunk = min(rest, 4 * LY.LINE_GAP)
        s.append(LY.Gap(chunk))
        rest -= chunk
    s.append(LY.Gap(4.5 * mm))


def intro(s, stem, color, extra=(), figs=(), maxh=58 * mm):
    """总题干（不留作答区），和要看的图绑在一起，并接住章节头；后面的小问可以再绑上来。"""
    n, rest = _num(stem)
    cards = [Card(f(), cap, color, maxh=maxh, smax=1.1) for f, cap in figs]
    s.append(FitBlock(LY._take_pending(s) + [p(qnum(n, color) + rest, Q)] + list(extra) + cards, bindable=True))
    return n


def bind_prev(s, flowables):
    """把一组内容和前面刚登记的总题干绑成一块（总题干不许一个人落在栏底）。"""
    if s and getattr(s[-1], "_bindable", False):
        s.append(FitBlock(list(s.pop().parts) + list(flowables)))
    else:
        s.append(FitBlock(list(flowables)))


def sub(s, text, lines, first=False):
    """小问。first=True 时和前面的总题干绑在一起（题干后面至少跟着第一问）。"""
    if first:
        head = min(LY._answer_space(text, lines), 2 * LY.LINE_GAP)
        bind_prev(s, [p(text, Q), Spacer(1, head)])
        rest = LY._answer_space(text, lines) - head
        while rest > 0:
            chunk = min(rest, 4 * LY.LINE_GAP)
            s.append(LY.Gap(chunk))
            rest -= chunk
        s.append(LY.Gap(3 * mm))
    else:
        qblock(s, text, lines)


def spare_card(s, fig, cap, color, maxh=48 * mm):
    s.append(Card(fig(), cap, color, maxh=maxh, smax=1.0))
