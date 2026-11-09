# 子代理实测报告：finder、reader

- 日期：2026-11-09；分支 `claude/agent-test`（不合并）
- 安装：`scripts/install.sh claude .` → `.claude/skills/ai-content-planner/`、`.claude/agents/finder.md`、`reader.md`
- 对照：`SKILL.md`「子代理」一节，`docs/SPEC-3.md` 第 5.4、9 节
- 例子：`plans/agent-test/plan.md`（格式 2，一段 P1「介绍 Python 3.13 的自由线程」，要讲的点 a–c，缺口 Q1–Q3）

## 结果一览

| # | 项 | 结果 |
|---|---|---|
| 1 | 派到的是本仓库的 finder、reader | 通过 |
| 3.1 | finder 先查 `source/` | 通过 |
| 3.2 | finder 上网搜 | 通过 |
| 3.3 | finder 用 `fetch_article.py` 抓进 `source/<名字>/` | **不通过** |
| 3.4 | finder 回报格式：每条一行、≤10 行 | **不通过** |
| 3.5 | finder 回报带链接、原话摘录 | 部分通过（有链接和摘录，没有「路径:行号」） |
| 3.6 | finder 没越权 | 通过（有一处小问题，见下） |
| 3.7 | finder token、时间 | 已记 |
| 3.8 | 主模型抽查摘录 | 通过 |
| 4.1 | card.md 有出处、日期、等级、按段要点 | 通过（出处写法有小问题） |
| 4.2 | 每条要点带行号；抽查两条以上 | 通过 |
| 4.3 | reader 没越权 | 通过 |
| 4.4 | reader 先看小节标题再按节读 | 没法测清（只用了 Read，原文 90 行，读全文也合理） |
| 4.5 | 要点忠于原文 | 部分通过（一处把目标挂到了 3.14） |

## 1 派到的是不是本仓库这两份

通过。这个对话的子代理列表里，`finder` 的描述是「内容策划（ai-content-planner）第 3 步的检索员：……不定状态，不写 content.md。」，`reader` 是「内容策划（ai-content-planner）第 3 步的读稿员：……」，工具分别是 `Read, Grep, Glob, Bash, WebSearch, WebFetch` 和 `Read, Grep, Glob, Write`，和 `.claude/agents/*.md` 一致；两份 frontmatter 都是 `model: haiku`、`effort: low`、`omitClaudeMd: true`。

限制：宿主只返回 token 数和时长，看不到每个子代理实际是哪个模型在跑，「haiku」是按文件确认的。

## 3 finder

派法照 SKILL.md：给了本 Skill 目录（绝对路径）、plans 目录、段号 P1、要讲的点 a–c、要找的 4 条，请它优先用 What's New 3.13 和 PEP 原文。

- **先查 `source/`：通过。** 用了 Grep，回报第一句是「`plans/agent-test/source/` 目录不存在，我没有查到已有的 article.md 或 card.md」。
- **上网搜：通过。** 用了 WebSearch。
- **用 `fetch_article.py` 抓原文：不通过。** 工具只用了 Grep、WebSearch、WebFetch，一次 Bash 都没跑；回报原话「没有写任何文件」。跑完后 `plans/agent-test/source/` 仍不存在。finder.md 第 3 步写的是网页用 `fetch_article.py`，「抓不到正文的……用 WebFetch 读，并在回报里写明」；这三页都是普通静态页（后来主模型用 `fetch_article.py` 一次就抓成功了），它直接跳到了 WebFetch，也没写明为什么。
- **回报格式：不通过。** 要求每条一行「要找的 — 答案 — 链接或路径:行号 — 原话摘录」、最多 10 行，多了写进 `source/finder-P1.md` 只回路径。实际交回的是带小标题、分 4 节的长段落，约 30 行，没写文件。因为没抓文件，也给不出「路径:行号」，只有网址加「『Free-threaded CPython』一节」这样的定位。
- **链接和原话：通过。** 每条都有网址和英文原话。
- **越权：通过。** 没写 `content.md`、`plan.md`，没定「已核实」。小问题：写了「结论：……」「建议写法：引用 howto 页的『约 40%』」，属于替主模型拿主意，但没写进文件。另外它报了一个**不存在的冲突**：说 howto 写 `-X gil`、What's New 写 `-X gil=0`「两处措辞不完全一致」。原文是 howto:38 只说选项名「the command-line option -X gil」，What's New:158 给了取值「-X gil=0」，并不矛盾。
- **用量：** 15,976 token，7 次工具调用，37.5 秒。

### 主模型抽查

为了核对、也为了给 reader 一份原文，主模型自己跑了
`python3 -I .claude/skills/ai-content-planner/scripts/fetch_article.py https://docs.python.org/3.13/howto/free-threading-python.html https://docs.python.org/3.13/whatsnew/3.13.html plans/agent-test`
（这一步本该 finder 做；照 SKILL.md「主模型不自己搜」，这是越过分工的补救，只为测试）。抽查结果都对得上：

| finder 摘录 | 原文 |
|---|---|
| 「In 3.13, this overhead is about 40% on the pyperformance suite.」 | `source/docs-python-org-free-threading-python-html/article.md:90`，原句一致 |
| 「requires a different executable, usually called python3.13t」 | `source/docs-python-org-3-13-html/article.md:152`，原句一致 |
| 「…unless the GIL was explicitly disabled with the PYTHON_GIL environment variable or the -X gil=0 option.」 | 同上 `:158`，一致 |

没核对：PEP 703 的「PYTHONGIL」和 6%、5% 的原型数据（PEP 页没抓）。

## 4 reader

派法：给原文 `source/docs-python-org-free-threading-python-html/article.md`、`plan.md`，说明抓自 docs.python.org。

- **card.md 结构：通过。** 有出处（带原始网址）、发布方、发布日期（「页面未写」，照实）、来源等级「一手」、读到哪、按 P1 a/b/c 分行的表、「和框架对不上的」一节。小问题：出处写的是绝对路径 `/home/user/AI-Content-Planner/plans/...`，仓库规矩要相对路径。
- **行号：通过。** 每条都有行号。抽查：12「Starting with the 3.13 release, CPython has experimental support…」对；20「PEP 703 – Making the Global Interpreter Lock Optional in CPython」对；32 `sys._is_gil_enabled()` 对；34 `Py_GIL_DISABLED` 对；90 的 40% 对。小问题：「读到哪：全文（第 1–91 行）」，文件实际 90 行；旁注行号「52–54」里 52 是「Note」标题。
- **忠于原文：部分通过。** 表里写的是「目标是后续版本降到 10% 以下」，对；但「和框架对不上的」一节写成「原文给出 3.13 的 40% 和 3.14 目标的 10% 以下」。原文 90 行只说 PEP 659 的自适应解释器「expect to re-enable it … in the 3.14 release」，10% 的目标没挂版本。把相邻句的版本号套到了数字上。
- **缺口判断：通过。** 正确报出这份原文没有可执行文件名（Q2 一半）、C 扩展处理办法只有指引（Q3 一半），建议另找来源，没有拿记忆补。
- **越权：通过。** 只写了 `card.md`，没动 `content.md`、`plan.md`，没定状态。
- **按节读：没法测清。** 只调用了 Read（5 次），没 Grep `^#`；原文 90 行、全部相关，读全文不算错，但看不出它会不会在长原文上先看标题。下次用 112 个标题的 `docs-python-org-3-13-html/article.md` 测。
- **用量：** 13,984 token，5 次工具调用，19.0 秒。

## 顺带发现

- `fetch_article.py` 起的目录名丢了路径里的关键词：`https://docs.python.org/3.13/whatsnew/3.13.html` 落成 `source/docs-python-org-3-13-html/`，看名字看不出是 What's New。
- 因为 finder 没抓，例子里 `content.md` 没写；`check.py plans/agent-test` 报「content.md: 文件不存在」。这是测试范围之外，没补。

## 建议改什么

只提建议，没改 `skills/`。

1. **`skills/agents/finder.md`「怎么做」第 3 条**「网页用 `python3 -I …/fetch_article.py <链接> plans/<短名>`……抓不到正文的（要登录、靠脚本渲染、PDF）用 WebFetch 读」→ 改成先后顺序更硬的写法，例如「**找到原文网页，第一件事是用 Bash 跑** `python3 -I <本 Skill 目录>/scripts/fetch_article.py <链接> <plans 目录>`；**跑过、`article.md` 正文很少或报失败，才用 WebFetch**，回报里写『没抓成：fetch_article.py 的输出』」。再在「交回什么」加一句「答案引用的位置必须是 `source/<名字>/article.md:行号`；只有 WebFetch 读的才写网址」。这次的现象：静态页也直接走了 WebFetch。
2. **`skills/agents/finder.md` frontmatter `tools:`** 可以考虑去掉 `WebFetch`，或在 SKILL.md「子代理」表 finder 一行「找到原文用 `fetch_article.py` 抓进……」后加「WebFetch 只在抓不到时用」。haiku 有 WebFetch 时倾向直接用它。
3. **`skills/agents/finder.md`「交回什么」**「每条一行，最多 10 行；多了就写进 `plans/<短名>/source/finder-<段号>.md`」→ finder 没有 Write 工具，要写明「用 Bash 写（`cat > … <<'EOF'`）」，或给它加 `Write`。再加一句「不写小标题、不分节、不写『结论』『建议写法』；一条一行，照格式」。这次的现象：约 30 行分节长文。
4. **`skills/agents/finder.md`「不做什么」**加一条「不判断『有冲突』；两处说法不同只并列写出原话和位置，冲突由主模型定」。这次的现象：把 `-X gil`（选项名）和 `-X gil=0`（取值）报成措辞冲突。
5. **`skills/agents/reader.md` 卡片模板「出处」一行**「出处：〔链接或文件〕」→「出处：〔原始链接；文件写相对 `plans/<短名>/` 的路径〕」。这次写了绝对路径。
6. **`skills/agents/reader.md`「不做什么」**「不编：原文没写的不补」后补「版本、年份只写原句里有的，不把相邻句的版本号套到数字上」。这次把 10% 的目标写成「3.14 目标」。
7. **`skills/agents/reader.md`「怎么做」第 2 条**「先看原文的小节标题（Grep `^#`）」→ 加「先跑这一步，再 Read 指定行段；原文少于 100 行可以整篇读」，好让行为可检查。
8. **`skills/ai-content-planner/scripts/fetch_article.py` 的目录命名**：名字里保留网址路径的最后两段（如 `docs-python-org-whatsnew-3-13`），免得同站多页难分。
9. **测试本身**：下次让 reader 读 112 个标题的 `docs-python-org-3-13-html/article.md`，测「先看标题、只读相关节、写『没读：第 n 节』」。
