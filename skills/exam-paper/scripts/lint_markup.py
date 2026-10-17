# -*- coding: utf-8 -*-
"""排版前扫出卷模块里的字符串，找会排坏的写法（layout._markup 自动把 A÷B、√X 画成真分数线／真根号，有几个坑）。

用法：python lint_markup.py build_xxx.py [xxx_figs.py ...]

查的东西（都是踩过的）：
1. √ 后面紧跟字母：√2AF 会印成 √(2AF)、√3x 是 √(3x)。写 √(2)AF、√(3)x。
2. √ 或 ÷ 的操作数后面紧跟括号：√3（三帆解析）、9√3÷5m（约…）、√3(R+r)、27÷8（…）都会把括号吞进去。
   改成先写括号里的话、断句，或者 √(3)×(R+r)。
3. ÷ 左边隔几个字就是全角右括号：「（1）π(R²-r²)÷6」左操作数会一直吞到前面去。前面加几个汉字隔开。
4. 根号里套分式：√(4+2÷a) 排乱，换元。
5. 宋体缺字形的符号（⇒ ⇔ ⊂ ⊆ ⟺ ↔ ∉ ✓ ⅓ ⅔ 下标数字、⁴ 以上的上标）——用 <super>/<sub> 或换写法。
6. 数字和单位之间有空格（20 m 会拆两行）。
qa_render.py 交付前还会再拿字体文件比一遍字形，这里只是提前拦。
断言、注释里的字符串也会被扫到——不印到卷面上的可以不管。
"""
import ast
import io
import re
import sys

RULES = [
    (r"√\d+[A-Za-z]", "√ 后面紧跟字母会一起开方，写 √(2)AF 这种"),
    (r"√[0-9A-Za-z.]+[（(]", "√ 的操作数后面紧跟括号，括号会被吞进根号"),
    (r"÷[0-9A-Za-z.²³]+[（(]", "÷ 的分母后面紧跟括号，括号会被吞进分母"),
    (r"）[^，。；：、=＝<>≤≥\s（）]{0,10}÷", "÷ 左边不远处有全角右括号，左操作数可能吞到前面去"),
    (r"√\([^)]*÷", "根号里套分式会排乱，换元"),
    (r"[⇒⇔⊂⊆⟺↔∉✓⅓⅔₀₁₂₃₄₅₆₇₈₉ᵢ⁴⁵⁶⁷⁸⁹]", "宋体没有这个字形"),
    (r"\d (m|cm|mm|km|kg|g|s|min|h|°|%)\b", "数字和单位之间别空格"),
]


def strings(path):
    """模块里所有字符串常量（相邻字符串已由解析器拼好），跳过文档字符串。"""
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docs.add(id(first.value))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 3
                and id(node) not in docs):
            yield node.lineno, node.value


def main():
    n = 0
    for path in sys.argv[1:]:
        for line, s in strings(path):
            for pat, why in RULES:
                for m in re.finditer(pat, s):
                    a, b = max(0, m.start() - 12), min(len(s), m.end() + 12)
                    print(f"{path}:{line}  {why}\n    …{s[a:b]}…")
                    n += 1
    print(f"共 {n} 处可疑" if n else "没发现可疑写法")
    sys.exit(1 if n else 0)


if __name__ == "__main__":
    main()
