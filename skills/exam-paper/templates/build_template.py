"""<卷名>（<日期>）。

用户原话：「……」（照抄，别改写）
范围：……（教材版本、章节；核过目录或学校进度的依据写在这里）
结构：……（满分、时间、各题型题数和分值）
题源：……（原题标出处、题干照抄；原创的注明「按北京中考结构原创」，不冒充真题）
答案在 verify_<名字>.py 里验算，配图在 <名字>_figs.audit() 里按题干条件核。

用法：复制成 build_<名字>.py，配图模板复制成 <名字>_figs.py（放同一个目录），把下面 import 的模块名改掉。
题目按 id 存：(id, lambda s, c: 题型函数(...))，id 用「学校+题号」这种好认的写法（如 "四中16"）。
卷面题号、图注里的「第N题」、答案页题号都按位置自动给——题干开头写的数字只是占位，调顺序时不用改。
"""

import os
import sys


def _kit():
    """找排版引擎（本 skill 的 kit/ 目录）：先看环境变量 EXAM_PAPER_KIT，再从当前目录往上、最后在用户目录里
    找各家工具的 skills 目录（Claude Code、Codex、WorkBuddy、CodeBuddy、TRAE、Qoder）。
    都找不到就把下面 KIT 改成 kit/ 的实际位置。"""
    if os.environ.get("EXAM_PAPER_KIT"):
        return os.environ["EXAM_PAPER_KIT"]
    dirs = (".claude/skills", ".agents/skills", ".codex/skills", ".workbuddy/skills",
            ".codebuddy/skills", ".trae/skills", ".qoderwork/skills", "skills")
    here = os.path.abspath(os.getcwd())
    roots = []
    while True:                                   # 项目级：当前目录一路往上
        roots.append(here)
        up = os.path.dirname(here)
        if up == here:
            break
        here = up
    roots.append(os.path.expanduser("~"))         # 用户级
    for root in roots:
        for d in dirs:
            p = os.path.normpath(os.path.join(root, d, "exam-paper", "kit"))
            if os.path.isdir(p):
                return p
    raise SystemExit("找不到 exam-paper 的 kit/ 目录：设环境变量 EXAM_PAPER_KIT，或者改这个文件里的 KIT。")


KIT = _kit()
sys.path.insert(0, KIT)

from reportlab.lib.units import mm  # noqa: E402

import skin as A
import paper_kit as P
import xxx_figs as F                      # ← 改成实际的配图模块
from layout import OUT
from paper_kit import cq, fill, qb

TITLE = "九上数学 · 示例卷"
WATERMARK = None                          # 要水印就填文字，比如学生的名字
C1, C2, C3, C4, C5, C6 = P.STAGE_COLORS

# ================================================================ 一、单项选择题
SINGLE = [
    ("示例选1", lambda s, c: cq(s, "1.（原创）关于x的一元二次方程x²-4x+k=0有两个相等的实数根，则k的值为（　　）",
                               ["A. 2", "B. 4", "C. -4", "D. 16"], c)),
    ("示例选2", lambda s, c: cq(s, "2.（原创）如图，将△ABC绕点C顺时针旋转40°得到△DEC，点A的对应点为D。"
                               "若∠ACB=30°，则∠BCD的度数为（　　）",
                               ["A. 10°", "B. 20°", "C. 40°", "D. 70°"], c, F.fig_q2)),
]

# ================================================================ 二、填空题
FILLS = [
    ("示例填1", lambda s, c: fill(s, "3.（原创）已知抛物线y=x²-2x+m与x轴有两个交点，则m的取值范围是＿＿＿＿。", c)),
    ("示例填2", lambda s, c: fill(s, "4.（原创）下表是二次函数y=ax²+bx+c的部分对应值，则这个函数图象的对称轴是直线＿＿＿＿。", c,
                                tab=(0, [["x", "-1", "0", "1", "2"], ["y", "3", "0", "-1", "0"]], [16, 14, 14, 14, 14]))),
]

# ================================================================ 三、解答题
BIG = [
    ("示例解1", lambda s, c: qb(s, "5.（原创）已知关于x的一元二次方程x²-(k+2)x+2k=0。（5分）\n"
                               "（1）求证：无论k取何值，方程总有两个实数根；\n（2）若方程的两个根都是正整数，求k的值。", 6, c)),
    ("示例解2", lambda s, c: qb(s, "6.（原创）在平面直角坐标系xOy中，抛物线y=x²-2x-3与x轴交于A，B两点（A在B的左侧），"
                               "与y轴交于点C。（6分）\n（1）求A，B，C的坐标；\n（2）求△ABC的面积。", 6, c,
                               figs=[(F.fig_b6, "第6题")], spare=[(F.fig_b6, "第6题 备用图")])),
]

# ================================================================ 答案（按 id 存，卷面题号自动对上）
ANSWER = {
    "示例选1": "B。Δ=16-4k=0，k=4。",
    "示例选2": "A。旋转角∠ACD=40°，∠BCD=∠ACD-∠ACB=40°-30°=10°。",
    "示例填1": "m<1。Δ=4-4m>0。",
    "示例填2": "x=1。x=0和x=2的函数值相等，对称轴是它们的中点。",
    "示例解1": "（1）Δ=(k+2)²-8k=(k-2)²≥0，所以总有两个实数根。（2）x<sub>1</sub>=2，x<sub>2</sub>=k，"
              "k为正整数即可：k=1，2，3，……（任意正整数）。",
    "示例解2": "（1）A(-1,0)，B(3,0)，C(0,-3)。（2）AB=4，OC=3，面积=4×3÷2=6。",
}


def build(path=None, ans_path=None):
    """试卷和答案各一个文件。"""
    path = path or OUT / "数学示例卷.pdf"
    ans_path = ans_path or OUT / "数学示例卷（答案）.pdf"
    P.setup()
    s = []
    P.banner(s, TITLE, "MATH · 人教版九年级上册（第21～24章）",
             [("第21章 一元二次方程", A.SKY), ("第22章 二次函数", A.MINT), ("第23章 旋转", A.LAV), ("第24章 圆", A.PEACH)],
             score=22, minutes=30)
    s.append(P.Note("卷首说明：题源、作答要求、限时。", A.PINK))
    P.section(s, "01", "单项选择题", "每题2分 · 共4分", C1)
    P.emit(s, SINGLE, 1, C1)
    P.section(s, "02", "填空题", "每题2分 · 共4分", C2, note="一句提示（可选），比如对着错因档案提醒一条。")
    P.emit(s, FILLS, 1 + len(SINGLE), C2)
    P.section(s, "03", "解答题", "共11分", C3)
    P.emit(s, BIG, 1 + len(SINGLE) + len(FILLS), C3)
    P.build_doc(path, TITLE, s, watermark=WATERMARK)

    a = P.answer_story(
        "示例卷 · 参考答案", "数值答案全部程序核算",
        [(f"<b>一、单项选择题</b>（每题2分）{P.key(SINGLE, ANSWER)}", SINGLE),
         ("<b>二、填空题</b>（每题2分）", FILLS), ("<b>三、解答题</b>", BIG)],
        ANSWER, note="对答案之前先自查：……",
        tail=f"答案来源：第{P.nums('示例选1', '示例选2')}题是原创……所有数值答案都用程序核算过（verify_xxx.py）。")
    P.build_doc(ans_path, TITLE + " · 答案", a, accent=A.MINT, watermark=WATERMARK, banner=False)
    return path, ans_path


if __name__ == "__main__":
    print(build())
