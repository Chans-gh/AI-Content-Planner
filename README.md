# AI Content Planner · 内容策划

做任何内容之前，先把「讲什么、凭什么、缺什么」想清楚。一个给 AI 助手（Claude Code、Codex 等）用的 Agent Skill：把一句话、要求、链接、文件、图片、音视频整理成**立意、段落表、资料底稿和缺口表**，定向补齐事实、参数、步骤、案例，你确认方向后，交给下游去做成品。

## 产出能用在哪

| 输出形式 | 交给谁 | 第一版 |
|---|---|---|
| 视频 | [AI-Coding-Video](https://github.com/Chans-gh/AI-Coding-Video)（风格、分镜、逐字稿、出片） | 写全 |
| PPT、课件、报告、图文 | 对应的 Skill 或人 | 留了位置，用到时补全 |
| 知识库、资料库 | 资料底稿 `research.md` 本身就是：每条信息带种类、来源和核实状态 | 留了位置 |

交接格式写在 [`handoff.md`](skills/ai-content-planner/handoff.md)，任何下游照它读就能接上。

## 安装

**Claude Code**（插件市场）：

```bash
claude plugin marketplace add chans-gh/AI-content-planner
claude plugin install ai-content-planner@ai-content-planner
```

**Codex**（插件市场）：

```bash
codex plugin marketplace add chans-gh/AI-content-planner
codex plugin add ai-content-planner@ai-content-planner
```

**其他助手**（拷贝 Skill 文件夹）：先 `git clone` 本仓库，再运行：

```bash
scripts/install.sh claude   # → ~/.claude/skills/
scripts/install.sh codex    # → ~/.agents/skills/（Codex 不走插件时用；DeepSeek Harness 也读这里）
scripts/install.sh dsh      # → ~/.dsh/skills/（DeepSeek Harness）
scripts/install.sh all      # 以上三处都装
scripts/install.sh dsh ~/my-project     # 只装进某个项目（→ ~/my-project/.dsh/skills）
scripts/install.sh zip      # 打成 dist/ai-content-planner.zip，用于 WorkBuddy 等“上传技能包”的助手
```

只用 Python 标准库（检查脚本要 Python 3），不要 API Key；读网页、读文档用助手自带的工具。

## 和下游一起用

做视频的，再装 AI-Coding-Video：

```bash
claude plugin marketplace add chans-gh/AI-Coding-Video
claude plugin install ai-coding-video@ai-coding-video
```

先用本 Skill 把内容定下来（产出在你项目的 `plans/<短名>/`），状态变成「已交接」后，ai-coding-video 从这里接着选风格、写分镜、出片。下游发现缺内容，会在缺口表加一行，回到本 Skill 补。

## 装好以后怎么问

- 「我想做一支讲 Artemis II 绕月的 60 秒竖屏短视频，先帮我把内容策划好」
- 「这几个链接是我们新品的资料，帮我理一份带货视频的内容，卖点要有依据」
- 「把这份 40 页的培训讲义整理成一节课的内容提纲，缺什么列出来」

## 仓库结构

```
skills/ai-content-planner/   Skill 本体（唯一正本，随插件和 install.sh 安装）
skills/.claude-plugin/       Claude Code 插件清单（插件市场清单在 .claude-plugin/）
skills/.codex-plugin/        Codex 插件清单（插件市场清单在 .agents/plugins/）
scripts/install.sh           拷贝安装、打 zip
scripts/selfcheck.py         自检（CI 也跑这个）
docs/                        设计记录：PRD、SPEC、回放验收，不随 Skill 安装
PLAN.md                      批次和待办
AGENTS.md                    给在本仓库干活的 AI 助手看的约定
```

## English

AI Content Planner is an Agent Skill for Claude Code, Codex and other assistants. Before you make anything, it turns a one-line idea, a brief, links, files, images or media into a purpose, a segment table, a sourced research sheet and a gap list, fills in the missing facts, and hands the plan off to a downstream skill once you confirm the direction. Version 1 fully covers video (handed to [AI-Coding-Video](https://github.com/Chans-gh/AI-Coding-Video)); slides, courses, reports, articles and knowledge bases have placeholders. Install with `claude plugin marketplace add chans-gh/AI-content-planner` then `claude plugin install ai-content-planner@ai-content-planner`, or run `scripts/install.sh`. The handoff format is documented in [`handoff.md`](skills/ai-content-planner/handoff.md). The skill is written in Chinese.

## 许可

[MIT](LICENSE)
