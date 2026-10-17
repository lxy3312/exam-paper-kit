"""<卷名> 的答案验算。复制成 verify_<名字>.py，跑完打印「全部通过」才能交付。

原则：
- 每个数值答案都要算一遍；取值范围一律扫描（frange 密扫），端点单独判断取不取等号。
- 几何量用配图模块 *_points() 里的同一组点算，图和答案就对上了；多换几组参数（α 取 50°/60°/72°……）验结论和参数无关。
- 选择题：每个选项都要能判断对错（对的给理由，错的给反例），最后把答案串和 build 模块的答案页比一遍。
- 有官方答案的，程序复核一致再写「官方答案」；自己解的，答案页上写清楚。
"""

import os
import sys

# 示例直接用仓库里的 kit/（设了环境变量 EXAM_PAPER_KIT 就用它）
sys.path.insert(0, os.environ.get("EXAM_PAPER_KIT")
                or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "exam-paper", "kit"))

from math import sqrt  # noqa: E402

import demo_figs as M  # noqa: E402
from figkit import _ang  # noqa: E402
from geometry import dist  # noqa: E402

OK = []


def ok(cond, msg):
    assert cond, msg
    OK.append(msg)


def close(a, b, eps=1e-6):
    return abs(a - b) < eps


def frange(a, b, n):
    return [a + (b - a) * i / n for i in range(n + 1)]


def choice():
    ans = {}
    # 示例选1：Δ=16-4k=0
    ks = [k for k in frange(-20, 20, 40000) if abs(16 - 4 * k) < 1e-9]
    ok(len(ks) == 1 and close(ks[0], 4), "示例选1 k=4")
    ans["示例选1"] = "B"
    P = M.q2_points()
    ok(close(_ang(P["B"], P["C"], P["D"]), 10), "示例选2 ∠BCD=10°")
    ans["示例选2"] = "A"
    return ans


def fills():
    # 取值范围扫描：两个交点 ⇔ Δ>0
    good = [m for m in frange(-5, 5, 10000) if 4 - 4 * m > 0]
    ok(max(good) < 1 and close(max(good), 1, 2e-3), "示例填1 m<1")


def figs():
    M.audit()                            # 配图按题干条件核一遍
    ok(True, "配图审计")


def big():
    for k in (-3, 0, 2, 5.5):
        d = (k + 2) ** 2 - 8 * k
        ok(d >= -1e-12 and close(d, (k - 2) ** 2), "示例解1 Δ=(k-2)²")
    roots = sorted(x for x in (-1, 3) if close(x * x - 2 * x - 3, 0))
    ok(roots == [-1, 3], "示例解2 A、B")
    ok(close(4 * 3 / 2, 6), "示例解2 面积6")


if __name__ == "__main__":
    a = choice()
    import build_demo as B
    letters = "".join(a[q[0]] for q in B.SINGLE)
    ok(all(B.ANSWER[q][0] == a[q] for q in a), "选择题答案和答案页一致")
    fills()
    figs()
    big()
    print(f"选择题答案 {letters}；{len(OK)} 项全部通过")
