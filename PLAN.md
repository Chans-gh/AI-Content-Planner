# 批次规划和待办

设计见 [docs/PRD.md](docs/PRD.md)、[docs/SPEC.md](docs/SPEC.md)、[docs/SPEC-3.md](docs/SPEC-3.md)、[docs/SPEC-4.md](docs/SPEC-4.md)、[docs/SPEC-5.md](docs/SPEC-5.md)、[docs/SPEC-5-P.md](docs/SPEC-5-P.md)（下游侧 [SPEC-5-V](docs/SPEC-5-V.md)）。一批开一个分支、一个 PR 合并到 `main`。

## 待办

- **批 J 交接格式 5**（SPEC-5-P，维护者 2026-11-19 已确认；下游另开会话做 SPEC-5-V）：`content.md` 成为唯一交付物、`plan.md` 只给用户看。J1 改格式、模板、检查、转 example 和 8 支回放；J2 等下游按 SPEC-5-V 接上 `/5` 后，用 ep05 的题和快速档模型的下游一起回放。
- **批 H3 跨类型回放**（SPEC-4 第 9、10 节）：获客、公益、预告各一支，从一句真实需求按 0.6.0 从头走，按第 10 节验收；另开分支和 PR。
- **非视频回放**：格式 2 的 7 支回放都是视频；有了 PPT、课件、报告、图文或知识库的下游、要做真实案例时，各做一支回放验收（SPEC-3 第 10 节）。
- **子代理实测**：批 G 没在本仓库的云端会话里实测派出 `finder`、`reader`（权限没放行），装好后在 Claude Code 里各派一次，看回报格式和模型（SPEC-3 第 11 节批 G 的验收）。
