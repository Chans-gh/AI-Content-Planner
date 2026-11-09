# 内容策划 Skill（AI-content-planner）：实现规格

[← PRD：做什么、为什么](PRD.md)

| 项 | 内容 |
|---|---|
| 版本 | 2.0（2026-11-09）：解耦成新仓库 `Chans-gh/AI-content-planner`，Skill 改名 `ai-content-planner`，产出不限于视频 |
| 状态 | PRD 第 9 节已确认（2026-11-09），按本文件实施 |
| 起点 | AI-Coding-Video 分支 `claude/dazzling-faraday-lwjvus` 的提交 `6151c44`：`skills/video-content-planner/`（批 A、B 做完）和 `docs/video-content-planner/` |

开发严格按本文件做。本文件没写的，不加；要偏离的，先改本文件并经维护者确认，再动代码。下面「照旧」指起点提交里的写法不变。

## 0 两个仓库各改什么

| 仓库 | 批 | 做什么 |
|---|---|---|
| 新仓库 `AI-content-planner` | D | 迁入、改名、去掉视频专属的写法、加 `formats.md` 和 `handoff.md`、仓库外壳（README、清单、安装、自检、CI），见第 1–8 节 |
| AI-Coding-Video（本分支，PR #1） | C | 删掉策划的文件、撤回给两个 Skill 加的改动、做 ai-coding-video 接入，见第 9 节 |
| AI-Coding-Video | E（可选） | 插件市场清单加一条指向新仓库的插件，先实测，见第 10 节 |

顺序：D 做完、新仓库测试全过，才做 C（C 要删掉本分支上的策划文件，删之前新仓库里得有）。

## 1 新仓库的结构

照 AI-Coding-Video 的样子，各家助手都能装：

```
AI-content-planner/
  README.md                 给人看：做什么、怎么装、和下游怎么配合（中文，末尾一节 English）
  LICENSE                   MIT，同 AI-Coding-Video
  AGENTS.md                 给在本仓库干活的助手看的约定（目录表、规矩、改完跑什么）
  CLAUDE.md                 只有一行 `@AGENTS.md`（Claude Code 读 CLAUDE.md）
  PLAN.md                   批次和待办；抓原文脚本那条待办从 AI-Coding-Video 的 PLAN 搬来
  .gitattributes            skills/ai-content-planner/CHANGELOG.md merge=union
  .gitignore                dist/、__pycache__/
  .claude-plugin/marketplace.json
  .agents/plugins/marketplace.json
  skills/.claude-plugin/plugin.json
  skills/.codex-plugin/plugin.json
  skills/ai-content-planner/     Skill 本体，唯一正本（第 2 节）
  scripts/install.sh             照 AI-Coding-Video 批 A 改过的那版（装 skills/ 下每个含 SKILL.md 的目录）
  scripts/selfcheck.py           自检（第 7 节）
  .github/workflows/test.yml     push 和 PR 时跑 selfcheck
  docs/PRD.md、docs/SPEC.md      本两份
  docs/replay/                   批 B 的回放，转成第 2 版格式（第 6 节）
```

不加本表以外的文件。

### 1.1 插件清单

| 文件 | 内容 |
|---|---|
| `.claude-plugin/marketplace.json` | `name: ai-content-planner`，`owner.name: Chans`，`description`、一条插件 `{name: ai-content-planner, source: ./skills, description}` |
| `.agents/plugins/marketplace.json` | 照 AI-Coding-Video 那份，名字换成 `ai-content-planner`，`displayName: AI Content Planner`，`category: Productivity` |
| `skills/.claude-plugin/plugin.json` | 照 AI-Coding-Video 那份：`name`、`description`、`version`（= SKILL.md 的 version）、`author`、`homepage`、`repository`（`https://github.com/chans-gh/AI-content-planner`）、`license: MIT`、`keywords`（`planning`、`research`、`content`、`outline`、`fact-check`）、`skills: ./` |
| `skills/.codex-plugin/plugin.json` | 同上，加 `interface`（`displayName`、`shortDescription`、`longDescription`、`developerName`、`category`） |

描述统一意思：「做内容之前的策划：立意、段落、资料底稿、缺口表；产出可交给视频、PPT、报告、课件等下游。」

### 1.2 README

各节：一句话是什么 → 产出能用在哪（视频、PPT、报告、课件、图文、知识库；第一版写全的是视频）→ 安装（Claude Code、Codex 插件市场两行命令；其他助手 `scripts/install.sh claude|codex|dsh|all [项目目录]`、`zip`）→ 和下游配合（做视频再装 AI-Coding-Video，附链接和它的两行安装命令；其他下游照 `handoff.md`）→ 装好以后怎么问（两三句例子）→ 仓库结构 → English（五六句：what、install、handoff）。≤120 行。

## 2 Skill 的文件

```
skills/ai-content-planner/
  SKILL.md              入口，≤110 行
  README.md             维护说明，≤60 行
  CHANGELOG.md          更新记录
  handoff.md            交接说明：给下游 Skill 看的接口，≤80 行（新）
  formats.md            各输出形式：段是什么、篇幅单位、交接前多查什么，≤80 行（新）
  genres.md             各内容题材，≤120 行
  types.md              信息种类，≤130 行
  templates/plan.md
  templates/research.md
  example/plan.md、example/research.md
  scripts/check.py
  scripts/tests/
```

从起点提交的 `skills/video-content-planner/` 迁过来（`git mv` 改名，内容按下面各节改）。

### 2.1 frontmatter

```yaml
name: ai-content-planner
description: 〔中文一段〕做内容之前的策划：把一句话、要求、链接、文件、图片、音视频整理成立意、段落表、资料底稿和缺口表，定向补齐事实、参数、步骤、案例，确认方向后交给下游。产出能做视频、PPT、报告、课件、图文、知识库。用户只有想法、资料太多要取舍、资料不够要补、要定主线和段落、下游发现内容缺口时使用。做成成品交给对应的 Skill（视频用 ai-coding-video）。
version: 0.2.0
display_name: 内容策划
display_name_en: AI Content Planner
description_en: "〔上面那段的英文〕"
```

`description` 不超过 1024 个字符，`name` 和目录名一致（自检查）。

### 2.2 SKILL.md 改哪些

各节顺序照旧，只改这些：

| 节 | 改成 |
|---|---|
| 开头 | 「终点是交接给下游」；不写死 ai-coding-video |
| 什么时候用 | 照旧五条；「不用」改成「只做形式（选风格、排版、改构图、渲染）的，直接用对应的下游 Skill」 |
| 两个阶段 | 照旧；结尾改成「交接后按 `handoff.md` 交给下游；交给谁看立意的『输出形式』和 `formats.md`」 |
| 按输入读到什么程度 | 照旧，含批 B 加的「先在同一来源找别的入口」 |
| 写什么 | 目录改成 `plans/<短名>/`；段落表六列改名（第 3.1 节）；「归谁」改成两种（第 3.1 节）；加一句「先在立意里定输出形式，段怎么切、篇幅怎么写看 `formats.md`」 |
| 交接 | 第 5 条改成「归『下游』的行写清了缺什么、哪段」；第 4 条加「按 `formats.md` 该形式的『交接前多查』自查」；命令改成 `python3 -I <本 Skill 目录>/scripts/check.py plans/<短名> --handoff`；交接说明加一句「交给哪个下游」 |
| 回流 | 「`提出于` 是分镜或制作」改成「`提出于` 是下游」 |
| 文件 | 加 `handoff.md`、`formats.md` 两行 |

全文把只属于视频的说法换成通用的：「片子」→「成品」，「观众」→「受众」，「画面素材」→「素材」；讲视频的例子留在 `formats.md` 的视频一节。

## 3 模板

### 3.1 `templates/plan.md`

和起点相比改这几处，其余照旧：

```markdown
# 内容策划：〔题目〕

格式：ai-content-planner/1
状态：〔阶段 1 整理中 | 阶段 1 待确认 | 阶段 2 补齐中 | 已交接 | 回流中〕（〔日期〕）。〔下一步一句〕
```

- **立意**：「时长与规格」一行拆成两行，共十行：
  - `| 输出形式 | 〔视频 / PPT / 课件 / 报告 / 图文 / 知识库；别的写明；见 formats.md〕 | |`
  - `| 篇幅与规格 | 〔目标篇幅：60 秒、12 页、3000 字；规格：画幅或页面尺寸、语言、有没有旁白〕 | |`
- **段落表**表头：`| 段 | 作用 | 受众收益 | 核心内容 | 素材编排 | 篇幅 |`；篇幅占位 `〔N 秒 / N 页 / N 字，或区间；不适用写「不限」〕`。
- **缺口表**：`归谁` 取「策划 / 下游」；`提出于` 取「阶段 1 / 阶段 2 / 下游」；`段` 写段号，几段用「、」，全部都要的写「全部」。
- 规则段照旧，把「风格后、分镜后」换成「下游」，「按播放顺序」换成「按成品里的顺序」，「预计时长」换成「篇幅」。

### 3.2 `templates/research.md`

照旧，只改：资料清单的 `用途` 取「内容依据 / 素材 / 参考」（原来是文案依据、画面素材、创作参考）；说明文字里的「片子」换成「成品」。

### 3.3 `types.md`

照旧（大类、代号、必须写清的、例子都不变）；只把通用规则里「片子」「旁白」这类视频说法换成「成品」「讲的时候」。修改记录加一行。

### 3.4 `genres.md`

- 开头去掉「名字同 ai-coding-video 的内容类型」，改成「按内容题材找对应的一节；输出形式另看 `formats.md`」。题材名照旧。
- 三个写全的题材、其他题材照旧，只把「片」字样的通用说法换掉。
- 「无旁白、纯情绪、虚构的片子」一节改名「非事实型内容（纯情绪、虚构）」，只留和形式无关的两条（每段仍要具体；虚构记「设定」、真实的照样核实）；「不强制写事实型口播」那条搬到 `formats.md` 视频一节。

### 3.5 `formats.md`（新）

每种输出形式一节，固定四项：**段是什么**、**篇幅写法**、**素材编排写什么**、**交接前多查**，再加一行「交给谁」。

- **视频**（写全）：段 = 一段画面加旁白；篇幅写秒（「45 秒」「40–50 秒」「1 分 30 秒」）；素材编排写已有的画面素材和要拍、录、生成的；多查：各段合计贴近目标时长、有没有旁白定了、每段素材有着落或进了缺口表；无旁白的片子「核心内容」写画面推进和情绪变化（从 genres.md 搬来）；交给 ai-coding-video（附仓库链接）。
- **PPT**、**课件**、**报告**、**图文**、**知识库**：各一两行，写段是什么、篇幅单位（页、字、条；知识库写「不限」），注明「第一版只留位置，用到时补全」。

### 3.6 `handoff.md`（新）

给下游 Skill 看的接口，写全以下各项（下游可能没装策划，所以写全，不只放链接）：

1. 文件：`plans/<短名>/plan.md`、`research.md`、`source/`。
2. 格式版本：`plan.md` 第二行 `格式：ai-content-planner/1`。下游先认这一行；版本号不认识就停下，请用户更新下游或策划。
3. 能用的编号：段 `P1`；信息数据 `U1-1`、单元 `U1`；缺口 `Q1`。它们写在哪几格（照第 3.1 节「编号写在哪」）。
4. 什么时候能接：状态是「已交接」。「回流中」时等策划处理完。
5. 下游产物放下游自己的目录（视频是 `videos/<短名>/`），不写进 `plans/`；引用段号写 `seg`，引用事实写 `ref`（U 编号，设定写 `null`），产物里写明来自哪份 `plan.md`。
6. 下游只许改 `plan.md` 两处：缺口表加行（`提出于=下游`；缺内容的 `归谁=策划`、缺素材的 `归谁=下游`；`状态=待补`），以及把状态行改成「回流中」。别的不改，也不改 `research.md`。
7. 格式升级：改节名、表头、取值、编号规则时格式号加 1，CHANGELOG 写明怎么从旧格式转；只加说明不升。

## 4 交接条件

照旧六条，第 4、5 条改为：

4. 每段核心内容是具体内容，不是动作标题（按 `genres.md` 的「不算数」和 `formats.md` 该形式的「交接前多查」自查）；
5. 归「下游」的行写清了缺什么、哪段（段号或「全部」）。

## 5 check.py

用法：`python3 -I <本 Skill 目录>/scripts/check.py <plans/短名 目录> [--handoff]`。检查表照旧，改这几行：

| 查什么 | 普通 | `--handoff` |
|---|---|---|
| `plan.md` 有「格式：ai-content-planner/1」一行（版本号不是 1 也报，说明本脚本只认 1） | 错 | 错 |
| 立意有十行，项名照第 3.1 节 | 错 | 错 |
| 段落表表头正好是新六列 | 错 | 错 |
| `归谁`、`提出于`、`用途` 用新取值 | 错 | 错 |
| `篇幅` 能解析：时间（秒、分、分钟）、页、字（含「千字」「万字」），或「不限」；只写数字不带单位算错 | 错 | 错 |
| 各段篇幅单位和目标篇幅单位一致时，合计相差超过 15% | 提示 | 提示 |
| 各段篇幅单位不一致（「不限」除外） | 提示 | 提示 |
| 归「下游」的行「缺什么」非空，「段」是段号或「全部」 | — | 错 |
| 核心内容引用的单元一条数据都没有（新，批 B 留下的建议） | — | 错 |

其余各行（节、编号、引用只在规定格子里查、枚举、占位、方向一行含括注、改内容关闭要写理由、待核实和冲突）照旧。

`scripts/tests/`：起点的 17 个测试照旧改成新格式；去掉核对 `../ai-coding-video/data/tags.json` 的那个，换成：`genres.md` 每节都有那三项；`formats.md` 每节都有那四项，且节名和模板「输出形式」的选项一致。新加：缺格式行、格式版本是 2、篇幅用页和字、单位不一致的提示、引用空单元。运行：`python3 -m unittest discover -s skills/ai-content-planner/scripts/tests`。

## 6 例子和回放

- `example/`：起点的 Artemis II 例子转成新格式（加格式行、立意十行、新表头和取值），内容不变；`--handoff` 通过。
- `docs/replay/`：起点 `docs/video-content-planner/replay/` 的 7 个目录和 `README.md` 搬过来，转成新格式。README 开头加一句「这是第 1 版（video-content-planner）的回放，第 2 版只转了格式，结论不变」；链到 AI-Coding-Video 文件的相对路径改成 GitHub 链接。7 个目录 `--handoff` 都通过。
- 转格式用一次性的脚本做，脚本不进仓库；转完逐个跑 `check.py` 核。

## 7 自检和 CI

`scripts/selfcheck.py`（只用标准库），在仓库根目录运行，依次：

1. 四份清单是合法 JSON；两份 `plugin.json` 的 `version` 等于 SKILL.md 的 `version`；`name` 都是 `ai-content-planner`；
2. SKILL.md 有 frontmatter，`name` 和目录名一致，`description` ≤1024 字符，有 `description_en`；
3. 第 2 节各文件的行数上限；
4. 跑 `scripts/tests/` 的测试；
5. 对 `example/` 和 `docs/replay/` 下每个目录跑 `check.py --handoff`。

输出每项一行，最后一行「通过」或「N 项不通过」，不通过退出码 1。`.github/workflows/test.yml`：`ubuntu-latest`、Python 3，跑 `python3 scripts/selfcheck.py`。

## 8 迁移步骤（批 D）

1. 维护者在 GitHub 建空仓库 `Chans-gh/AI-content-planner`（不勾初始化 README），加到会话里。
2. 初始提交：照第 1 节建外壳，`skills/ai-content-planner/` 和 `docs/` 先原样拷入起点提交的内容（不改内容，只改目录名）。提交说明写「从 Chans-gh/AI-Coding-Video 分支 claude/dazzling-faraday-lwjvus 提交 6151c44 迁入」。推到新仓库的 `main`。
3. 之后在新仓库开分支做第 2–7 节的改动，PR 合并到 `main`。
4. Skill 的 CHANGELOG 记一行 0.2.0：改名、解耦、格式 1、`handoff.md`、`formats.md`。旧的 0.1.0 三行保留，标「在 AI-Coding-Video 分支上做，没发布」。

验收：`python3 scripts/selfcheck.py` 通过；GitHub 上 CI 绿；`scripts/install.sh claude <临时目录>` 装出 `ai-content-planner`；在一个没有 AI-Coding-Video 的干净目录里克隆新仓库，selfcheck 照样通过。

## 9 AI-Coding-Video 这边（批 C，本分支）

批 D 验收通过后做。

### 9.1 撤回

| 动作 | 文件 |
|---|---|
| 删除 | `skills/video-content-planner/`、`docs/video-content-planner/`（`docs/` 空了就整个删） |
| 恢复成 `main` 上的样子 | `scripts/install.sh`、`.gitattributes`、`skills/.claude-plugin/plugin.json`、`skills/.codex-plugin/plugin.json`、`.claude-plugin/marketplace.json`、`AGENTS.md` |
| 恢复后再按 9.2 改 | `README.md`、`PLAN.md` |

### 9.2 接入

1. **`skills/ai-coding-video/SKILL.md`**：
   - 「什么时候用」加两条：内容还没定（只有想法、资料没整理）→ 先用 ai-content-planner（附新仓库链接）；项目里有 `plans/<短名>/plan.md`、状态「已交接」、输出形式是视频 → 从 `storyboard.md` 开始。
   - description 句末加：「内容策划用 ai-content-planner。」
2. **新文件 `skills/ai-coding-video/storyboard.md`**（≤80 行）：
   - 先认 `plan.md` 的格式行，只接 `ai-content-planner/1`；状态不是「已交接」的不接。
   - 读 `plan.md`、`research.md`，选风格照现有 0 级。
   - 分镜写 `videos/<短名>/storyboard.json`：`{"plan": "plans/<短名>/plan.md", "segments": [{"seg": "P1", "title", "content", "sec", "lead", "uses", "note"}]}`。字段含义写全（同 `cases/` 的 `case.json` 段落，`cases/` 不随 Skill 安装，不能只放链接）；一段策划可拆成几段分镜。
   - 逐字稿写 `videos/<短名>/script.json`：`vo`、`facts`、`pace`，`facts` 每条加 `ref`（U 编号；设定写 `null`）。
   - 用户确认后进阶段 4，照 `making.md`。
   - 回流：缺内容在 `plan.md` 缺口表加一行（`提出于=下游`、`归谁=策划`、`状态=待补`），状态改「回流中」，转策划处理；缺画面自己处理。
3. **版本**：`ai-coding-video/SKILL.md` 和两份 `plugin.json` 升到 0.7.0；CHANGELOG 记一行。
4. **`README.md`**：「安装」段开头加一句「内容还没想好的，先装 [AI-content-planner](https://github.com/Chans-gh/AI-content-planner) 做策划，再用本 Skill 出片」，附它的两行插件命令。
5. **`PLAN.md`**：阶段 7 改成一行「策划已搬到 AI-content-planner；本仓库只做接入（批 C）」，做完删掉；抓原文脚本的待办删掉（已搬到新仓库 PLAN）。

不动：`site/`、`.github/workflows/`、`samples/`、`packs/`、`cases/`、`media.json`、`candidates.md`、`build_index.py`、`release.sh`。改 `skills/ai-coding-video/SKILL.md` 会在合进 `main` 后触发一次介绍页重建，内容不变。

验收：`build_index.py --check` 通过；`git diff main --stat` 只有 9.2 列的文件；从新仓库的 `example/` 起，在新对话里写出 `storyboard.json`、`script.json`，`seg` 和 `ref` 都对得上 `plan.md`、`research.md`。

## 10 一站式安装（批 E，可选）

先实测再定：在 AI-Coding-Video 的 `.claude-plugin/marketplace.json` 的 `plugins` 里加一条 `{"name": "ai-content-planner", "source": {"source": "github", "repo": "Chans-gh/AI-content-planner"}, "description": …}`，看 `claude plugin install ai-content-planner@ai-coding-video` 能不能装上；Codex 的清单查文档、实测。能装就加，README 写一句；不能装就不加，README 照第 9.2 节写两行命令。

## 11 批次

| 批 | 在哪 | 内容 | 验收 |
|---|---|---|---|
| 0 | 本分支 | PRD、SPEC 第 2 版 | 维护者确认 PRD 第 9 节 |
| D | 新仓库 | 第 1–8 节 | 第 8 节验收 |
| C | 本分支 | 第 9 节 | 第 9 节验收 |
| E | 本分支 | 第 10 节（可选） | 实测结果写进 PLAN |

一批一个对话。每批做完：对应仓库的 CHANGELOG 记一行、PLAN 更新状态。
