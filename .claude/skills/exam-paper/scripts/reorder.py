# -*- coding: utf-8 -*-
"""按给定 id 顺序重排出卷模块里的题目列表（只搬条目，不改内容）。

用法：python reorder.py build_xxx.py "SINGLE=id1,id2,..." "FILLS=..." "BIG=..."

要求列表写成：
NAME = [
    ("id", ...),
    ...
]
每一项从 4 个空格加 ("id" 开始，列表以单独一行的 ] 结束。答案字典按 id 存，不用动。
"""
import io
import re
import sys


def reorder(s, name, order):
    m = re.search(rf"^{name} = \[\n", s, re.M)
    assert m, f"找不到 {name} = ["
    i0 = m.end()
    i1 = s.index("\n]\n", i0)
    body = s[i0:i1 + 1]
    starts = [x.start() for x in re.finditer(r'^    \("', body, re.M)]
    items = [body[a:b] for a, b in zip(starts, starts[1:] + [len(body)])]
    ids = [re.match(r'    \("([^"]+)"', it).group(1) for it in items]
    assert sorted(ids) == sorted(order), f"{name}：id 对不上\n现有 {ids}\n给的 {order}"
    by = dict(zip(ids, items))
    return s[:i0] + "".join(by[q] for q in order) + s[i1 + 1:]


def main():
    path = sys.argv[1]
    s = io.open(path, encoding="utf-8").read()
    for arg in sys.argv[2:]:
        name, ids = arg.split("=", 1)
        s = reorder(s, name, [x for x in ids.split(",") if x])
    compile(s, path, "exec")
    io.open(path, "w", encoding="utf-8").write(s)
    print("已重排", path)


if __name__ == "__main__":
    main()
