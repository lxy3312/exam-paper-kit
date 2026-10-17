# -*- coding: utf-8 -*-
"""列出出卷脚本（build_*.py）里已经用过的原题出处（扫题干里的「（学校……第N题）」），选题前先跑，避免和旧卷子重复。

用法：python used_sources.py [--dir 出卷脚本所在目录] [关键词 ...]（目录默认是当前目录）
  不给关键词：按出处排序全部列出（同一道题在几份卷子里出现会合并）
  给关键词：只列含这些词的（如 四中 2025 期中）
"""
import glob
import io
import os
import re
import sys

PAT = re.compile(r"[（(]([^（）()]{0,40}?(?:期中|期末|一模|二模|中考|月考|统考|竞赛|入試|AMC|奥赛|ОГЭ|POTW)"
                 r"[^（）()]{0,24}?)[）)]")


def norm(t):
    t = t.replace("—", "-").replace("–", "-").replace(" ", "")
    t = re.sub(r"[，,；;].*$", "", t)            # 「…第28题，官方答案」只留出处
    return t


def main():
    args = sys.argv[1:]
    work = "."
    if args[:1] == ["--dir"]:
        work, args = args[1], args[2:]
    keys = args
    seen = {}
    for f in sorted(glob.glob(os.path.join(work, "build_*.py"))):
        s = io.open(f, encoding="utf-8").read()
        for m in PAT.finditer(s):
            t = norm(m.group(1))
            if not re.search(r"\d+题|第\d+|(期中|期末|一模|二模|中考|月考|统考)\D{0,6}\d+", t):
                continue
            seen.setdefault(t, set()).add(os.path.basename(f))
    rows = sorted(seen.items())
    if keys:
        rows = [r for r in rows if all(k in r[0] for k in keys)]
    for t, fs in rows:
        print(f"{t}    ← {'、'.join(sorted(fs))}")
    print(f"共 {len(rows)} 条")


if __name__ == "__main__":
    main()
