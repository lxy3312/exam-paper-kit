# -*- coding: utf-8 -*-
"""模拟两栏排版，找栏底空白最少的题目顺序（只在每个关卡内部调，分值不同的题不互换位置）。

用法：
  python packsim.py 你的目录/build_xxx.py [--fix id1,id2] [--keep-section 4] [--beam 300]

要求出卷模块用 paper_kit：每道题由 P.emit() 放（前面带 Mark），关卡头由 P.section() 放，
build() 第一次调 P.build_doc() 出的是试卷。脚本把 build_doc 换成「只截 story 不出 PDF」，再按 Mark 切块。

输出：当前顺序和最优顺序各占几栏、每栏栏底空多少 mm，以及一条可以直接跑的 reorder.py 命令。
模拟是粗的（不精确处理缩图、分栏细节），结果拿去真排一遍再用 check_pdf.py 量。
"""
import argparse
import importlib.util
import sys

from pathlib import Path as _Path

KIT = _Path(__file__).resolve().parents[1] / "kit"          # 本 skill 自带的排版引擎
sys.path.insert(0, str(KIT))

from reportlab.lib.units import mm  # noqa: E402

import skin as A  # noqa: E402
import layout as LY  # noqa: E402
import paper_kit as P  # noqa: E402
import skin_q as K  # noqa: E402

W = LY.COLW
CAP1 = (A.COL_H - A.HEADER_H) / mm
CAP = A.COL_H / mm


def items_of(flows):
    out = []
    for f in flows:
        n = type(f).__name__
        if n in ("Mark", "NextPageTemplate", "Banner"):
            continue
        if n == "Gap":
            out.append(("gap", f.spaceBefore / mm, 0, 0))
        elif n == "CondPageBreak":
            out.append(("cond", f.height / mm, 0, 0))
        elif n == "FitBlock":
            h = f._measure(W, 1.0)[1]
            hmin = f._measure(W, K.FitBlock.MIN_K)[1] if f.cards else h
            f._measure(W, 1.0)
            out.append(("block", h / mm, hmin / mm, f.getSpaceBefore() / mm))
        else:
            _, h = f.wrap(W, 10 ** 6)
            out.append(("block", h / mm, h / mm, f.getSpaceBefore() / mm))
    return out


class Sim:
    def __init__(self):
        self.col, self.rem, self.top, self.waste = 0, CAP1, True, []

    def copy(self):
        o = Sim()
        o.col, o.rem, o.top, o.waste = self.col, self.rem, self.top, list(self.waste)
        return o

    def newcol(self):
        self.waste.append(self.rem)
        self.col += 1
        self.rem = CAP1 if self.col < 2 else CAP
        self.top = True

    def feed(self, its):
        for k, a, b, sb in its:
            if k == "cond":
                if self.rem < a:
                    self.newcol()
            elif k == "gap":
                if self.top:
                    continue
                if a > self.rem:
                    self.newcol()
                else:
                    self.rem -= a
            else:
                sb = 0 if self.top else sb
                if sb + a <= self.rem:
                    self.rem -= sb + a
                elif sb + b <= self.rem:
                    self.rem -= sb + b
                else:
                    self.newcol()
                    self.rem -= min(a, self.rem)
                self.top = False
        return self

    def pos(self):
        used = sum(CAP1 if c < 2 else CAP for c in range(self.col))
        return used + ((CAP1 if self.col < 2 else CAP) - self.rem)


def capture(path):
    sys.path.insert(0, str(_Path(path).resolve().parent))          # 出卷模块旁边的配图模块
    spec = importlib.util.spec_from_file_location("target_build", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    got = []
    orig = P.build_doc
    P.build_doc = lambda p, label, story, *a, **k: got.append(story)
    try:
        mod.build("_sim.pdf", "_sim_ans.pdf")
    finally:
        P.build_doc = orig
    return mod, got[0]


def segments(story):
    """→ head（第一个 Mark 之前）, sections=[(关卡头 items, [(qid, slot, items), ...]), ...]"""
    head, secs, cur, buf, kind = [], [], None, [], None

    def flush():
        if kind is None:
            head.extend(items_of(buf))
        elif kind[0] == "sec":
            secs.append((items_of(buf), []))
        else:
            if not secs:
                secs.append(([], []))
            secs[-1][1].append((kind[1], kind[2], items_of(buf)))

    for f in story:
        if isinstance(f, P.Mark):
            flush()
            buf = []
            kind = ("sec",) if f.kind == "sec" else ("q", f.qid, f.slot)
        else:
            buf.append(f)
    flush()
    return head, secs


def run(head, secs, orders):
    sm = Sim().feed(head)
    for (h, qs), order in zip(secs, orders):
        sm.feed(h)
        by = {q[0]: q[2] for q in qs}
        for qid in order:
            sm.feed(by[qid])
    return sm


def score(sm):
    inner = sm.waste[:-1] if len(sm.waste) > 1 else sm.waste
    return (sm.col, round(max(inner, default=0)), sum(w * w for w in sm.waste))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("module")
    ap.add_argument("--fix", default="", help="不动的题目 id，逗号分隔")
    ap.add_argument("--keep-section", default="", help="整段不动的关卡序号（从 1 数），逗号分隔")
    ap.add_argument("--beam", type=int, default=300)
    a = ap.parse_args()
    mod, story = capture(a.module)
    head, secs = segments(story)
    fixed = set(x for x in a.fix.split(",") if x)
    keep = set(int(x) - 1 for x in a.keep_section.split(",") if x)
    cur = [[q[0] for q in qs] for _, qs in secs]
    sm = run(head, secs, cur)
    print(f"当前顺序：{sm.col + 1} 栏，栏底空白(mm) {[round(w) for w in sm.waste]}，末栏剩 {round(sm.rem)}")

    beam = [(Sim().feed(head), [])]
    for si, (h, qs) in enumerate(secs):
        slots = [q[1] for q in qs]
        ids = [q[0] for q in qs]
        items = {q[0]: q[2] for q in qs}
        slot_of = {q[0]: q[1] for q in qs}
        nb = []
        for sm0, orders in beam:
            s1 = sm0.copy().feed(h)
            nb.append((s1, orders, []))
        for pos in range(len(qs)):
            exp = {}
            for s1, orders, done in nb:
                if si in keep or ids[pos] in fixed:
                    cands = [ids[pos]] if ids[pos] not in done else []
                else:
                    cands = [q for q in ids if q not in done and q not in fixed and slot_of[q] == slots[pos]]
                for q in cands:
                    s2 = s1.copy().feed(items[q])
                    d2 = done + [q]
                    key = (frozenset(d2), s2.col, round(s2.rem, 1))
                    cand = (s2, orders, d2)
                    if key not in exp or (s2.pos(), max(s2.waste, default=0)) < (exp[key][0].pos(), max(exp[key][0].waste, default=0)):
                        exp[key] = cand
            nb = sorted(exp.values(), key=lambda x: (x[0].pos(), max(x[0].waste, default=0)))[:a.beam]
        beam = [(s2, orders + [d2]) for s2, orders, d2 in nb]
    best = min(beam, key=lambda x: score(x[0]))
    cur_sm = run(head, secs, cur)
    if score(best[0]) >= score(cur_sm):
        print("当前顺序已经是模拟里最好的，不用调。")
        return
    sm, orders = best
    print(f"最优顺序：{sm.col + 1} 栏，栏底空白(mm) {[round(w) for w in sm.waste]}，末栏剩 {round(sm.rem)}")
    names = []
    for lst in ("SINGLE", "FILLS", "BIG"):
        if hasattr(mod, lst):
            names.append((lst, [q[0] for q in getattr(mod, lst)]))
    flat = [q for o in orders for q in o]
    args = []
    for lst, ids in names:
        new = [q for q in flat if q in ids]
        if len(new) == len(ids):
            args.append(f'{lst}={",".join(new)}')
    print("\n应用：")
    print(f'python "{__file__.replace("packsim.py", "reorder.py")}" "{a.module}" ' + " ".join(f'"{x}"' for x in args))


if __name__ == "__main__":
    main()
