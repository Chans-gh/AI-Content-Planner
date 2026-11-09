# AGENTS.md

给在本仓库里干活的 AI 助手（Claude Code、Codex、DeepSeek Harness 等）看的约定。想用这个 Skill 做内容策划，读 [`skills/ai-content-planner/SKILL.md`](skills/ai-content-planner/SKILL.md)。和维护者交流用中文。

## 目录

| 路径 | 是什么 | 怎么对待 |
|---|---|---|
| `skills/ai-content-planner/` | Skill 本体，唯一正本 | 改完跑 `python3 scripts/selfcheck.py`；维护规矩见它的 [README](skills/ai-content-planner/README.md)「维护」一节 |
| `skills/.claude-plugin/`、`skills/.codex-plugin/` | 两家的插件清单 | `version` 和 SKILL.md 的 `version` 一起改，自检会查 |
| `.claude-plugin/`、`.agents/plugins/` | 两家的插件市场清单 | 只改描述 |
| `scripts/` | `install.sh` 拷贝安装和打包；`selfcheck.py` 自检 | 路径一律相对脚本自己的位置 |
| `docs/` | 设计记录：PRD、SPEC、回放验收 | 不随 Skill 安装；实施完成后以 Skill 为准，不再同步 |
| `PLAN.md` | 批次和待办 | 做完的删掉，记进 Skill 的 CHANGELOG |

## 规矩

- **交接格式是对外的接口**：改 `templates/` 的节名、表头、取值或编号规则，要同时改 `check.py`、测试夹具、`handoff.md`，并把格式号加 1（`ai-content-planner/2`），CHANGELOG 写明怎么从旧格式转。
- **不依赖下游**：不读、不引用 AI-Coding-Video 或别的仓库的文件；测试离开别的仓库也要能跑。
- **只用标准库，不要 Key**：脚本只用 Python 标准库；抓网页用 Skill 随包的 `fetch_article.py`，别的读取用宿主自带的工具，不写死服务。
- **编号只增不改**；**一件事只记一处**，别处要用就放链接。
- **按 SPEC 做**：有 SPEC 的批次严格照做；要偏离先改 SPEC 并经维护者确认。

## 分支和提交

- 默认分支 `main`；一批一个分支、一个对话，做完开 PR 合并到 `main`。
- 提交前跑 `python3 scripts/selfcheck.py`；CI 也跑它。
- 不在代码、日志、提交里写 API Key。
