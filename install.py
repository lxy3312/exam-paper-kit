# -*- coding: utf-8 -*-
"""安装 exam-paper skill：复制到你用的 AI 工具的 skills 目录、装 Python 依赖、跑一份示例卷确认能用。

用法：
  python install.py --tool claude              # Claude Code（~/.claude/skills/）
  python install.py --tool codex               # Codex（~/.agents/skills/）
  python install.py --tool workbuddy           # WorkBuddy（~/.workbuddy/skills/，装完重启 WorkBuddy）
  python install.py --tool claude --tool codex # 一次装给好几个
  python install.py --tool all                 # 所有支持的工具都装
  python install.py --dest 某个目录             # 别的工具：装到它读取 skill 的目录
  python install.py --tool codex --project .   # 装到项目里（项目级目录，比如 ./.agents/skills/）

其他参数：--force 覆盖已有的同名 skill；--no-deps 不装依赖；--no-test 不跑示例卷。
只用标准库，Windows / macOS / Linux 都能跑。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE / "skills" / "exam-paper"
NAME = "exam-paper"

# 工具 → (用户级目录, 项目级目录, 装完要不要重启)。路径来自各家文档，工具更新后如有变化，用 --dest 指定。
TOOLS = {
    "claude": ("~/.claude/skills", ".claude/skills", False),        # Claude Code
    "codex": ("~/.agents/skills", ".agents/skills", False),         # OpenAI Codex（老版本是 ~/.codex/skills）
    "workbuddy": ("~/.workbuddy/skills", ".workbuddy/skills", True),  # 腾讯 WorkBuddy
    "codebuddy": ("~/.codebuddy/skills", ".codebuddy/skills", False),
    "trae": ("~/.trae/skills", ".trae/skills", False),
    "qoder": ("~/.qoderwork/skills", ".qoderwork/skills", False),
}


def copy_skill(dest_root, force):
    dest = Path(dest_root).expanduser().resolve() / NAME
    if dest.exists():
        if not force:
            print(f"  已经有了：{dest}（要覆盖就加 --force）")
            return dest
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"  已复制到：{dest}")
    return dest


def install_deps():
    print("装 Python 依赖（reportlab、pymupdf、pillow）……")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(HERE / "requirements.txt")])
    if r.returncode:
        sys.exit("依赖没装上：看上面的报错，或者手动运行 pip install -r requirements.txt")


def smoke_test(kit):
    """用刚装好的 kit 出一份示例卷并验算。"""
    print("跑一份示例卷试试……")
    out = Path(tempfile.mkdtemp(prefix="exam-paper-test-"))
    env = dict(os.environ, EXAM_PAPER_KIT=str(kit), EXAM_PAPER_OUT=str(out), PYTHONIOENCODING="utf-8")
    for script in ("build_demo.py", "verify_demo.py"):
        r = subprocess.run([sys.executable, str(HERE / "examples" / script)], cwd=out, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-3000:])
            sys.exit(f"示例卷没跑通（{script}）。常见原因：缺中文字体——见 README「字体」一节。")
    pdfs = sorted(p.name for p in out.glob("*.pdf"))
    print(f"  示例卷已生成：{out}（{'、'.join(pdfs)}），验算通过。")


def main():
    ap = argparse.ArgumentParser(description="安装 exam-paper skill")
    ap.add_argument("--tool", action="append", default=[], choices=list(TOOLS) + ["all"],
                    help="装给哪个工具，可以写多次")
    ap.add_argument("--dest", action="append", default=[], help="直接指定 skills 目录（会在里面建 exam-paper/）")
    ap.add_argument("--project", default=None, help="装到这个项目目录的项目级 skills 目录里，而不是用户目录")
    ap.add_argument("--force", action="store_true", help="覆盖已有的同名 skill")
    ap.add_argument("--no-deps", action="store_true", help="不装 Python 依赖")
    ap.add_argument("--no-test", action="store_true", help="不跑示例卷")
    a = ap.parse_args()
    if not a.tool and not a.dest:
        ap.print_help()
        sys.exit("\n要指定 --tool 或 --dest。不知道填什么：Claude Code 填 claude，Codex 填 codex，WorkBuddy 填 workbuddy。")
    if sys.version_info < (3, 10):
        sys.exit(f"需要 Python 3.10 以上，现在是 {sys.version.split()[0]}")

    tools = list(TOOLS) if "all" in a.tool else a.tool
    targets, restart = [], []
    for t in tools:
        user_dir, proj_dir, need_restart = TOOLS[t]
        targets.append((t, Path(a.project) / proj_dir if a.project else Path(user_dir)))
        if need_restart:
            restart.append(t)
    targets += [("自定义", Path(d)) for d in a.dest]

    print("复制 skill……")
    installed = [(t, copy_skill(d, a.force)) for t, d in targets]
    if not a.no_deps:
        install_deps()
    if not a.no_test:
        smoke_test(installed[0][1] / "kit")

    print("\n装好了：")
    for t, d in installed:
        print(f"  {t}: {d}")
    if restart:
        print(f"需要重启：{'、'.join(restart)}")
    print("用法：跟 AI 说「用 exam-paper 出一份人教版九上期中数学卷，100 分，试卷和答案分开」。")


if __name__ == "__main__":
    main()
