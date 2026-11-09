# 批次规划和待办

设计见 [docs/PRD.md](docs/PRD.md)、[docs/SPEC.md](docs/SPEC.md)。

| 批 | 在哪 | 内容 | 状态 |
|---|---|---|---|
| D | 本仓库 | 从 AI-Coding-Video 迁入、改名、通用化、`handoff.md`、`formats.md`、仓库外壳和 CI（SPEC 第 1–8 节） | 做完（2026-11-09），待合并 |
| C | AI-Coding-Video 分支 `claude/dazzling-faraday-lwjvus` | 删掉那边的策划文件、ai-coding-video 接入（SPEC 第 9 节） | 未开始 |
| E | AI-Coding-Video | 插件市场一站式安装，先实测（SPEC 第 10 节，可选） | 未开始 |

## 待办

- **抓原文脚本随包（重要，维护者定）**：把维护者 Test 仓库 `chansclaude-research` 的 `fetch_article.py` 改写后放进 Skill 的 `scripts/`。原文先落成本地 Markdown（正文、图表清单），助手按需读片段，不把整页网页灌进对话，是省 token 的关键。要定：依赖（beautifulsoup4、Pillow）缺了怎么降级（Skill 规矩是只用标准库）、离线测试怎么带、抓下来的文件哪些进用户项目（`plans/<短名>/source/`）。批 C 之后排期。
- **补全其他输出形式（按需）**：`formats.md` 里 PPT、课件、报告、图文、知识库现在各一两行；有了对应的下游、要做真实案例时，照视频一节写全，再做一支回放验收。
