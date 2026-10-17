"""<卷名> 的配图。复制成 <名字>_figs.py，和出卷脚本放同一个目录。

规矩（图画错了，学生会照着错图想半天）：
- 点的坐标全由题干条件算出来，不手摆；*_points() 返回的就是图里画的那组点，verify 拿它验答案，audit() 拿它核图。
- 练习题的图不画答案点（临界位置、最优位置、所求的点都不画）。
- 几何大题一般三张图：图1 给第(1)问，图2 给第(2)问，再加一张备用图（spare，可以单独流到下一栏）。
- 图要够大能画辅助线：Fig 默认 76×58mm 画布，Card 会再按栏宽放大（最多 1.1 倍）。
- 画完用 kit/contact_sheet.py 拼一张总览图看一遍；audit() 要在 verify 里调一次。
"""

import os
import sys

# 示例直接用仓库里的 kit/（设了环境变量 EXAM_PAPER_KIT 就用它）
sys.path.insert(0, os.environ.get("EXAM_PAPER_KIT")
                or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "exam-paper", "kit"))

from math import sqrt  # noqa: E402

import geometry as G  # noqa: E402
from figkit import Fig, Plot, _ang, dirv, mid  # noqa: E402   Fig：自然坐标自动缩放；Plot：没有网格的坐标系
from geometry import dist, rot  # noqa: E402

R3 = sqrt(3)


# ---------------------------------------------------------------- 第2题：旋转
def q2_points():
    """△ABC 绕 C 顺时针转 40° 得 △DEC，∠ACB=30°。"""
    C = (0.0, 0.0)
    A = dirv(110, 3.0)
    B = dirv(80, 2.2)                    # ∠ACB = 110°-80° = 30°
    D, E = rot(A, C, -40), rot(B, C, -40)
    return {"A": A, "B": B, "C": C, "D": D, "E": E}


def fig_q2():
    P = q2_points()
    f = Fig([P[k] for k in "ABCDE"], w=56, hmax=46)
    f.poly([P["A"], P["B"], P["C"]], fill=None, width=0.9)
    f.poly([P["D"], P["E"], P["C"]], fill=None, width=0.9)
    f.mark([(P["A"], "A", -1.4, 0.4, "end"), (P["B"], "B", 1.2, 0.6, "start"), (P["C"], "C", 0, -3.6, "middle"),
            (P["D"], "D", 1.4, 0.4, "start"), (P["E"], "E", 1.4, -1.2, "start")])
    return f.d


# ---------------------------------------------------------------- 第6题：抛物线
def fig_b6():
    p = Plot(-2.2, 4.2, -4.4, 3.4, w=60, hmax=56, xticks=(-1, 3), yticks=(-3,))
    p.curve(lambda x: x * x - 2 * x - 3, -1.8, 3.8)
    return p.d


# ---------------------------------------------------------------- 审计
def audit():
    """按题干条件核图，失败就 AssertionError（audit_figs 会报出来）。"""
    P = q2_points()
    assert abs(_ang(P["A"], P["C"], P["B"]) - 30) < 1e-6, "第2题 ∠ACB≠30°"
    assert abs(_ang(P["A"], P["C"], P["D"]) - 40) < 1e-6 and abs(dist(P["C"], P["A"]) - dist(P["C"], P["D"])) < 1e-9, "第2题 旋转不对"
    v1, v2 = P["A"], P["D"]
    assert v1[0] * v2[1] - v1[1] * v2[0] < 0, "第2题 题干说顺时针"
