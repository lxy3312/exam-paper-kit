# AGENTS.md

这个仓库是一个出卷 skill（`skills/exam-paper/`）加它自带的排版引擎。给 AI 编程助手（Codex、Claude Code、WorkBuddy、CodeBuddy、TRAE、Cursor……）看的说明：

## 用户让你「安装这个 skill」

1. 确认有 Python 3.10 以上。
2. 在仓库根目录运行 `python install.py --tool <你自己>`：Claude Code 是 `claude`，Codex 是 `codex`，WorkBuddy 是 `workbuddy`，
   CodeBuddy 是 `codebuddy`，TRAE 是 `trae`，Qoder 是 `qoder`。不在列表里的，用 `--dest <你读取 skill 的目录>`；
   只想装到当前项目里，加 `--project <项目目录>`。
3. 脚本会复制 skill、装依赖（reportlab、pymupdf、pillow）、跑一份示例卷。把装到的目录、示例卷是否生成成功告诉用户；
   要重启的工具（比如 WorkBuddy）提醒用户重启。
4. 示例卷报找不到字体：见 README「字体」一节，让用户装字体或设环境变量，别跳过。

## 用户让你「出一份卷子」

读 `skills/exam-paper/SKILL.md`（装好之后在你的 skills 目录里），按里面的七步走。你的工具不支持 skill 也没关系，直接读这个文件照做。

## 改这个仓库

- `skills/exam-paper/kit/` 是排版引擎，`scripts/` 是工具脚本，`templates/` 是模板，`examples/` 是能直接跑的示例卷。
- 改完至少跑一遍：`cd examples && python build_demo.py && python verify_demo.py`，再用 `scripts/check_pdf.py` 量一下。
- 不要往仓库里放原卷、扫描件、任何现成作品的人物或漫画，也不要放学生的个人信息。
