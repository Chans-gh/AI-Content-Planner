# 批次规划和待办

设计见 [docs/PRD.md](docs/PRD.md)、[docs/SPEC.md](docs/SPEC.md)、[docs/SPEC-3.md](docs/SPEC-3.md)、[docs/SPEC-4.md](docs/SPEC-4.md)。一批开一个分支、一个 PR 合并到 `main`。

## 待办

- **批 H3 跨类型回放**（SPEC-4 第 9、10 节）：获客、公益、预告各一支，从一句真实需求按 0.6.0 从头走，按第 10 节验收；另开分支和 PR。
- **下游适配**：ai-coding-video 读格式 3（说法、约束、素材「能不能送生成」），在 ai-coding-video 仓库进行中；合并前，下游还只认格式 2。
- **非视频回放**：格式 2 的 7 支回放都是视频；有了 PPT、课件、报告、图文或知识库的下游、要做真实案例时，各做一支回放验收（SPEC-3 第 10 节）。
- **子代理实测**：批 G 没在本仓库的云端会话里实测派出 `finder`、`reader`（权限没放行），装好后在 Claude Code 里各派一次，看回报格式和模型（SPEC-3 第 11 节批 G 的验收）。
