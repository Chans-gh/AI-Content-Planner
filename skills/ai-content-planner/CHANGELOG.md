# 更新记录

[← 返回说明](README.md)

最新的在最上面。

| 日期 | 更新内容 |
|---|---|
| 2026-11-09 | 0.4.0：三步流程和交接格式 `ai-content-planner/2`（SPEC-3 批 F）。流程从两个阶段改成三步：读输入出需求 → 构建框架 → 补齐内容，每步请用户确认；简单任务可合并第 1、2 步，确认记录写「自动，未问用户」。立意十项拆成「需求」八项、「立意」三项；「段落」改「框架」（内容流程一句 + 要讲的点 a、b、c + 用到哪些输入）；`research.md` 改名 `content.md`，不再用信息单元，按段一节、编号 `P1-1`，承担信息的素材记成 F 类行；`SKILL.md` 补「核实」的判定标准；`genres.md` 删掉，只留「不算数的写法」「合规先查」两条进 `SKILL.md`「规矩」；`formats.md` 缩成一张表；`check.py`、测试夹具、`example/` 都改成格式 2。**格式 1 → 2 怎么转**：格式行改 `/2`；`research.md` 改名 `content.md`；立意十项按 `handoff.md` 第 6 节的表拆成需求、立意（凭什么信去掉）；段落表改框架：加「内容流程：」一行，核心内容按「；」拆成 `a. …<br>b. …`、去掉编号，素材编排去掉，加「用到哪些输入」；每条 `U1-1` 挪到第一次用到它的段那一节、改编号 `P1-1`，「讲哪一点」写字母，别的段用到写「（P3 b 也用）」，没被引用的写「不用」，正文、缺口表里的旧编号跟着换；删「要哪些单元」；检索记录加「谁查的」；确认记录「方向」拆成「需求」「框架」两行；状态和缺口「提出于」换新取值（阶段 2 → 第 3 步）。下游引用事实改写 `ref: "P1-1"` |
| 2026-11-09 | 0.3.0：抓原文脚本随包。`scripts/fetch_article.py` 由维护者 chansclaude-research 的同名脚本改写成纯标准库（`html.parser` 搭的小 DOM 代替 beautifulsoup4，读文件头量 PNG、JPEG、GIF、WebP 尺寸代替 Pillow；按响应头和 `<meta charset>` 解码；`--name` 只许字母、数字、`_.-`；纯编号的文件名不当图表标题；正文很少时提示换工具），把网页落成 `plans/<短名>/source/<名字>/` 的 `article.md`、`charts.md`、`charts.json`。和原版不同，原图默认不下载，只读每张图开头的字节量尺寸；加 `--images` 才下到 `images/`，一篇最多 50 MB，单张太大换较小的版本，超出的只记链接。`page.html`、`images/` 由自动写的 `.gitignore` 挡在仓库外。离线测试 `scripts/tests/test_fetch.py` 在本机起假网站，selfcheck 一并跑。`SKILL.md`「按输入读到什么程度」加先抓原文、按小节读片段、私密原文不进公开仓库。交接格式不变 |
| 2026-11-09 | 下游 ai-coding-video 0.7.0 接入（`storyboard.md` 从 `plans/<短名>/` 接手），AI-Coding-Video 的插件市场也能装本 Skill；仓库 README「和下游一起用」加这条命令，PLAN 删掉做完的批次表。只整理，版本号不变 |
| 2026-11-09 | 0.2.0：从 AI-Coding-Video 解耦成独立仓库，`video-content-planner` 改名 `ai-content-planner`，产出不限于视频。交接格式定为 `ai-content-planner/1`（`plan.md` 第二行），新加 `handoff.md`（给下游 Skill 看的接口）和 `formats.md`（各输出形式，第一版写全视频）；用户项目里改放 `plans/<短名>/`；立意十项（加「输出形式」，「时长与规格」改「篇幅与规格」）；段落表「观众收益」「预计时长」改「受众收益」「篇幅」（秒、页、字或「不限」）；缺口「归谁」只分策划、下游，「提出于」的分镜、制作合成下游，「全片」改「全部」；资料用途改「内容依据 / 素材 / 参考」；`check.py` 查格式行、立意十项、篇幅单位，核心内容引用空单元时 `--handoff` 报错；`genres.md` 不再依赖 ai-coding-video 的题材表 |
| 2026-11-08 | 0.1.0（`video-content-planner`，在 AI-Coding-Video 分支上做，没发布） 批 B 回放后修（还没发布，版本号不变）：`example/` 换成 Artemis II 的 60 秒短解说（3 段，事实全部来自 NASA 公开来源）；`check.py` 认「方向（括注）：」这种写法；`types.md` 加「事先的时间表、计划标 C4」；`genres.md` 新闻的限制加「计划和事后记录分开」、带货加「有功效宣称规定的品类先查规定」，新闻再加「几个数字之间能算的自己算一遍」（接手测试查出 NASA 两个数字对不上）；`SKILL.md` 读不到时先在同一来源找别的入口。回放记录见仓库的 `docs/video-content-planner/replay/` |
| 2026-11-08 | 0.1.0（`video-content-planner`，在 AI-Coding-Video 分支上做，没发布） 质检后修（还没发布，版本号不变）：`check.py` 只在规定的格子里查 P、Q、U 引用，正文里的「华为 P40」「2026 年 Q1」不再当引用；时长多认「1 分钟 30 秒」「约 45 秒」「45 秒左右」；缺口表的「段」可写「全片」；检查命令写成 `<本 Skill 目录>/scripts/check.py` |
| 2026-11-08 | 0.1.0（`video-content-planner`，在 AI-Coding-Video 分支上做，没发布）：第一版（阶段 7 批 A）。`SKILL.md` 管内容整理、补齐两个阶段和交接、回流；模板 `templates/plan.md`、`templates/research.md`；`types.md` 由 chansclaude-research 的 7 大类 31 小类改写，例子换成新闻、带货、教程，加「设定」；`genres.md` 写全新闻资讯解说、产品广告和带货、教程和录屏演示三类，另有六类各一两行；`scripts/check.py`（只用标准库）和离线测试；`example/` 先放一份虚构的占位例子 |
