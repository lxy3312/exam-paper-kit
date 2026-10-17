# exam-paper-kit

给 [Claude Code](https://claude.com/claude-code) 用的出卷 skill：从定范围、按题位选题、写出卷脚本、按题干条件画图、程序验算答案，
到两栏排版、去空白、交付前检查，出**可以直接打印**的初中数学试卷——A4 两栏、黑白卡片风格，试卷和答案各一个 PDF。

附带一套基于 ReportLab 的中文试卷排版引擎，不用 Claude 也能直接写 Python 出卷。

<p>
<img src="docs/preview-paper.png" width="48%" alt="试卷第一页">
<img src="docs/preview-answers.png" width="48%" alt="答案页">
</p>

（图里是 `examples/` 里的示例卷，题目是原创的。）

## 里面有什么

```
.claude/skills/exam-paper/
├── SKILL.md              出卷流程（七步）
├── reference/            卷面规矩清单、技术上的坑、题源和难题题位
├── kit/                  排版引擎
│   ├── layout.py         两栏版面、字体、公式（A÷B、√X 自动画成真分数线/真根号）、作答留白
│   ├── skin.py           横幅（分数印章）、关卡式章节头、图卡、题号徽章、选项字母、页面装饰、水印
│   ├── skin_q.py         不拆的整块（放不下先缩图再换栏）、中文断行禁则、填空横线
│   ├── paper_kit.py      题目按 id 存、题号按位置自动给、选择/填空/大题、出试卷和答案两个 PDF
│   ├── geometry.py       几何作图（Fig 自然坐标自动缩放、Coord 网格坐标系）
│   ├── figkit.py         坐标系、弧、圆上标签、几张小图拼一行
│   └── contact_sheet.py  把一个模块里的图拼成一张总览图
├── scripts/
│   ├── packsim.py        模拟两栏排版，找栏底空白最少的题目顺序
│   ├── reorder.py        按 id 重排题目列表
│   ├── check_pdf.py      量每栏栏底空白、查行首标点和水印、导出总览图
│   ├── lint_markup.py    出 PDF 前查会排坏的公式写法和缺字形的符号
│   ├── used_sources.py   列出以前的卷子用过哪些原题
│   └── crop.py           从原卷裁一道题出来看
└── templates/            出卷、配图、验算三个模板
examples/                 用模板做的示例卷，可以直接跑
```

几个设计上的取舍：

- **题干和图、题干和选项绝不拆开**；大题的作答留白可以流到下一栏，备用图可以单独流动。宁愿留空也不拆，留空再靠调顺序补。
- **题号按位置生成**：题目按 id 存，调顺序只挪列表条目，卷面题号、图注里的「第N题」、答案页全跟着变。
- **图由题干条件算出来**：`*_points()` 返回的点同时给画图、验算、审计用，图和答案对得上。
- **作答区只留白不画线**，分式一律真分数线，卷面不出现 `/` 和 `^`。

## 安装

需要 Python 3.10 以上（在 3.12 上测过）：

```bash
pip install -r requirements.txt
```

字体默认用 Windows 自带的宋体、黑体、微软雅黑、幼圆。别的系统用环境变量指到 **TrueType 轮廓**的中文字体文件
（ReportLab 不支持 CFF 轮廓的 OTF，比如 Noto CJK 的 `.otf`）。

**当 Claude Code skill 用**：把 `.claude/skills/exam-paper` 整个文件夹复制到 `~/.claude/skills/`（所有项目都能用），
或者直接在本仓库目录里打开 Claude Code。然后跟它说「出一份人教版九上期中数学卷，100 分」之类的就行。

**直接跑示例**：

```bash
cd examples
python build_demo.py      # 出 outputs/数学示例卷.pdf 和 outputs/数学示例卷（答案）.pdf
python verify_demo.py     # 答案验算
python ../.claude/skills/exam-paper/scripts/check_pdf.py outputs/数学示例卷.pdf --png png --montage png
```

## 环境变量

| 变量 | 作用 | 默认 |
|---|---|---|
| `EXAM_PAPER_KIT` | 模板去哪儿找 `kit/` | `~/.claude/skills/exam-paper/kit`（示例里是仓库内的相对路径） |
| `EXAM_PAPER_OUT` | PDF 输出目录 | 当前目录下的 `outputs/` |
| `EXAM_PAPER_CACHE` | 公式小图缓存 | `~/.cache/exam-paper-kit` |
| `EXAM_PAPER_FONT_BODY` / `EXAM_PAPER_FONT_HEAD` | 正文 / 标题字体文件 | Windows 宋体 / 黑体 |

## 说明

- 仓库里没有任何原卷、扫描件或题库。用公开考试题出卷时，题源自己准备，遵守来源网站的条款和当地规定。
- 卷面格式默认按北京初三数学（单选 8×2、填空 8×2、解答 12 道），换地区、换学科照着改结构就行。
- 不含任何现成作品的人物或漫画。

## License

[MIT](LICENSE)
