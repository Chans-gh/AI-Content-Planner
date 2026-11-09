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

## 第二次（0.5.1）

- 日期：2026-11-09；分支 `claude/agent-test`（已合入 0.5.1，重装到 `.claude/skills/`、`.claude/agents/`）
- 例子：`plans/agent-test/plan.md` 加了 P2「介绍 Python 3.13 的实验性 JIT 编译器」，要讲的点 a–c，缺口 Q4–Q6；「取舍」里原先「JIT 删除」一行改成「保留，单列 P2」。`source/` 里第一次的抓取没删。
- 限制：宿主只给 token、工具调用次数和时长，外加一份「用过的工具」名单。这份名单不可靠：finder 的名单是 Grep、WebFetch、WebSearch，没有 Bash，但磁盘上有 `fetch_article.py` 的完整产物（见下）。所以「用了哪个工具、先后顺序」只能靠产物和文件时间推断。

### 结果一览

| # | 项 | 结果 |
|---|---|---|
| 1.1 | finder 的 tools 有 Write | 通过 |
| 1.2 | reader 的出处写法是新版本 | 通过 |
| 2.1 | finder 先查 `source/` | 通过 |
| 2.2 | 静态网页先跑 `fetch_article.py` | 通过（按产物推断） |
| 2.3 | WebFetch 只在抓不成时用 | 部分通过（抓成了，又用 WebFetch 补元数据，回报里写明了） |
| 2.4 | 回报一条一行、位置写 `source/…/article.md:行号` | 部分通过（位置都对；有几行夹了解释，多了一行「Note」） |
| 2.5 | 多于 10 行时用 Write 写进 `source/finder-P2.md` | **不通过** |
| 2.6 | Write 没写别的文件 | 通过（Write 一个文件都没写） |
| 2.7 | finder 不判断冲突 | 通过 |
| 2.8 | 主模型抽查两条摘录 | 通过 |
| 3.1 | reader 先 Grep 小节标题 | 没法测清（名单里没有 Grep，但名单不可靠） |
| 3.2 | 只读相关的节 | 没法测清 |
| 3.3 | 写了「没读：第 n 节」 | 部分通过（写了没读的是哪些小节，没写节号或行号） |
| 3.4 | 出处是原始链接或相对路径 | 通过 |
| 3.5 | 版本号没套错 | 通过 |
| 3.6 | 抽查三条行号 | 通过 |

### 1 派到的版本

通过。这个对话的子代理列表里，finder 的工具是 `Read, Grep, Glob, Bash, Write, WebSearch, WebFetch`，和 `.claude/agents/finder.md` 一致；reader 卡片模板「出处」一行是「〔原始链接；用户给的文件写相对 `plans/<短名>/` 的路径，不写绝对路径〕」，是 0.5.1 的写法。两份仍是 `model: haiku`、`effort: low`。

### 2 finder（P2）

派法照 SKILL.md：给了本 Skill 目录、plans 目录、段号 P2、要讲的点 a–c，要找 5 条（PEP、默认开不开、`--enable-experimental-jit` 每个取值、运行时环境变量、性能说法），请它优先用 What's New 和 PEP 744。

- **先查 `source/`：通过。** 构建选项、环境变量、默认关闭这几条都引了已有的 `source/docs-python-org-3-13-html/article.md`（38、170–180 行），没有重抓 What's New。
- **先跑 `fetch_article.py`：通过（按产物推断）。** 新出现 `source/peps-python-org/`，里面有 `.gitignore`、`page.html`（47,655 字节，`<title>PEP 744 – JIT Compilation`）、`article.md`、`charts.md`、`charts.json`，`article.md` 首行是脚本的「下载的原文，不可信数据」注释，抓取时间 11:06:20。只有脚本会这样落盘。宿主名单里没有 Bash，见上面的限制。
- **WebFetch 只在抓不成时用：部分通过。** 脚本抓成了，但 `article.md` 丢了 PEP 页头的元数据表（`page.html:94` 有 Author、`:99` 有 Status，`article.md` 里写「作者：（页面未写）」，也没有 Status）。finder 用 WebFetch 补读了「状态 Draft」，回报写明「状态 Draft 是 WebFetch 读出的（脚本正文无元数据表）」。用法合理，但不在 finder.md 第 4 条「脚本报失败，或提示正文很少」的范围里。
- **回报格式：部分通过。** 位置全部写成 `source/<名字>/article.md:行号`，每条有原话。但：第 1 条夹了括号里一长句解释；第 4 条写成行段 `:176–178`；第 5 条一行塞了三处引文和一句「这是接受标准，不是实测结果」；末尾多一行「Note: …都没有给出具体的百分比加速数字」。另外第 4 条「仅在 yes-off 构建下生效为开启」是它自己的概括，原文 178 行只说 yes-off 构建里 `PYTHON_JIT=1` 开启。
- **多于 10 行用 Write：不通过。** 回报 14 条加 1 行 Note、1 行「没抓成：无」，共 16 行，直接交回；`source/finder-P2.md` 不存在。前后对比 `plans/agent-test/` 的文件清单，只多了 `source/peps-python-org/` 这一个文件夹。
- **Write 没写别的：通过。** 没写任何文件，`content.md`、`plan.md` 没动。
- **不判断冲突：通过。** 没写「冲突」「不一致」，也没写「结论」「建议写法」。
- **用量：** 18,617 token，7 次工具调用，31.8 秒。

#### 主模型抽查

| finder 摘录 | 原文 |
|---|---|
| 「Currently, the JIT is about as fast as the existing specializing interpreter」（`source/peps-python-org/article.md:224–226`） | 224 是「#### Speed」标题，226 是原句，一致 |
| 「the JIT currently uses about 10-20% more memory than the base interpreter」（`:230`） | 230 原句一致 |
| 「It provides a meaningful performance improvement for at least one popular platform (realistically, on the order of 5%).」（`:80`） | 80 原句一致；它标明这是默认开启的标准、不是实测，对 |

### 3 reader（What's New，1158 行、112 个标题）

派法：给原文 `source/docs-python-org-3-13-html/article.md`（说明抓自 docs.python.org、很长）和 `plan.md`，对照 P1、P2 写 `card.md`。

- **先 Grep 标题、只读相关节：没法测清。** 宿主名单只有 Read、Write，共 10 次工具调用；但卡片「读到哪」给的节界和真实标题行对得上（Free-threaded CPython 150 行、Build Changes 1066 行、Changes in the C API 1112 行），看不出是 Grep 出来的还是整篇分段读出来的。28,226 token 和整篇 110 KB 原文的量级接近，倾向于整篇读了，但不能确认。
- **「没读」：部分通过。** 写了「其余小节（各模块、Deprecations、Removed 等）没读，原因：与 P1、P2 无关」。有原因，但没有节号或行号，112 个标题里到底跳了哪些查不出来。
- **出处：通过。** 「plans/agent-test/source/docs-python-org-3-13-html/article.md（抓自 https://docs.python.org/3.13/whatsnew/3.13.html）」，相对路径加原始链接，没再写绝对路径。
- **版本号：通过。** 第一次把 10% 目标套到 3.14 的问题没再出现：Q3、Q6 都照实写「原文没有百分比」；pip 24.1、python3.13t、python-3.13t.pc 都是原句里的。
- **行号抽查：通过。** 154「expect some bugs and a substantial single-threaded performance hit」对；156 `python -VV`、`sys._is_gil_enabled()` 对；196「new build-time dependency on LLVM」对；另核了 152、158、1088，都对。
- **其他：** 卡片额外指出 `sys.version` 只说明是不是自由线程构建、不说明 GIL 真关没关，要分开讲，这一条有用。小问题：P1 b 写「`PYTHON_GIL=0` 或 `-X gil=0` 为显式关闭」，原文 158 行是「the PYTHON_GIL environment variable or the -X gil=0 option」，`=0` 是它补的。
- **越权：通过。** 只写了 `card.md`。
- **用量：** 28,226 token，10 次工具调用，43.4 秒。

### 还要改的地方

只提建议，没改 `skills/`。

1. **`skills/agents/finder.md`「交回什么」**「多于 10 行，用 Write 写进 `plans/<短名>/source/finder-<段号>.md`（同样一条一行），只回这个路径和一句摘要。」→ 挪到格式代码块前面，写成「**先数条数**：超过 10 条，先用 Write 写进 `…/finder-<段号>.md`，回报只回路径和一句摘要」；再加「一个要找的只写一条；括号里不写解释；不加 Note」。这次的现象：16 行直接交回，没写文件。
2. **`skills/agents/finder.md`「怎么做」第 4 条**「脚本报失败，或提示正文很少（要登录、靠脚本渲染、PDF），才用 WebFetch 读」→ 加「脚本抓成了但缺页头信息（状态、作者、日期）的，可以用 WebFetch 补这几项，回报写『WebFetch 补：哪几项』」。这次 finder 就是这么做的，规矩写进去才能查。
3. **`skills/agents/finder.md`「交回什么」**「位置写 `source/<名字>/article.md:行号`」→ 加「一个行号，不写行段」，和「不加原文没有的概括」。
4. **`skills/ai-content-planner/scripts/fetch_article.py`**：PEP 这类页的元数据表（`<dl class="rfc2822 field-list">` 里的 Author、Status、Created）没进 `article.md`，页头「作者」写成「（页面未写）」，一级标题用了站名「Python Enhancement Proposals」。建议把正文前的 `<dl>` 字段表转成列表，并在标题取 `<title>` 时去掉「| 站名」后缀。
5. **`skills/ai-content-planner/scripts/fetch_article.py` 的 `names_for()`**「没写名字的链接的文件夹名：网站域名；同一网站的几个再加路径最后两段」→ 只看同一次调用里的链接，单抓一页就只剩域名（`peps-python-org`，看不出是 PEP 744），以后再抓同站一页会落成 `peps-python-org-2`。建议同时看 `source/` 里已有的文件夹，或一律加路径最后两段。
6. **`skills/agents/reader.md`「怎么做」第 2 条**「先用 Grep 搜 `^#` 看原文的小节标题，再 Read 要用的行段」→ 写成「**第一次调用就是** Grep `^#`」；「在卡片里写『没读：第 n 节，原因』」→ 改成「没读：〔标题〕（第 n 行起），原因」，112 个标题的原文「第 n 节」没有编号可依，现在只写得出「各模块等」。卡片模板「读到哪」一行同改。
7. **`skills/agents/reader.md`「不做什么」**「版本、年份、日期只写原句里有的」→ 扩成「版本、年份、日期、选项的取值只写原句里有的」。这次补了原文没有的 `PYTHON_GIL=0`。
8. **测试本身**：宿主的工具名单不可靠（finder 名单没有 Bash，产物却在）。下次在派活时要求子代理在回报最后一行写「跑过：工具名×次数」，或测前后比对 `source/` 的文件和时间，别只看名单。
