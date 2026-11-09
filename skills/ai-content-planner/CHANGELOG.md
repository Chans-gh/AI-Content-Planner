# 更新记录

[← 返回说明](README.md)

最新的在最上面。

| 日期 | 更新内容 |
|---|---|
| 2026-11-09 | 0.2.0：从 AI-Coding-Video 解耦成独立仓库，`video-content-planner` 改名 `ai-content-planner`，产出不限于视频。交接格式定为 `ai-content-planner/1`（`plan.md` 第二行），新加 `handoff.md`（给下游 Skill 看的接口）和 `formats.md`（各输出形式，第一版写全视频）；用户项目里改放 `plans/<短名>/`；立意十项（加「输出形式」，「时长与规格」改「篇幅与规格」）；段落表「观众收益」「预计时长」改「受众收益」「篇幅」（秒、页、字或「不限」）；缺口「归谁」只分策划、下游，「提出于」的分镜、制作合成下游，「全片」改「全部」；资料用途改「内容依据 / 素材 / 参考」；`check.py` 查格式行、立意十项、篇幅单位，核心内容引用空单元时 `--handoff` 报错；`genres.md` 不再依赖 ai-coding-video 的题材表 |
| 2026-11-08 | 0.1.0（`video-content-planner`，在 AI-Coding-Video 分支上做，没发布） 批 B 回放后修（还没发布，版本号不变）：`example/` 换成 Artemis II 的 60 秒短解说（3 段，事实全部来自 NASA 公开来源）；`check.py` 认「方向（括注）：」这种写法；`types.md` 加「事先的时间表、计划标 C4」；`genres.md` 新闻的限制加「计划和事后记录分开」、带货加「有功效宣称规定的品类先查规定」，新闻再加「几个数字之间能算的自己算一遍」（接手测试查出 NASA 两个数字对不上）；`SKILL.md` 读不到时先在同一来源找别的入口。回放记录见仓库的 `docs/video-content-planner/replay/` |
| 2026-11-08 | 0.1.0（`video-content-planner`，在 AI-Coding-Video 分支上做，没发布） 质检后修（还没发布，版本号不变）：`check.py` 只在规定的格子里查 P、Q、U 引用，正文里的「华为 P40」「2026 年 Q1」不再当引用；时长多认「1 分钟 30 秒」「约 45 秒」「45 秒左右」；缺口表的「段」可写「全片」；检查命令写成 `<本 Skill 目录>/scripts/check.py` |
| 2026-11-08 | 0.1.0（`video-content-planner`，在 AI-Coding-Video 分支上做，没发布）：第一版（阶段 7 批 A）。`SKILL.md` 管内容整理、补齐两个阶段和交接、回流；模板 `templates/plan.md`、`templates/research.md`；`types.md` 由 chansclaude-research 的 7 大类 31 小类改写，例子换成新闻、带货、教程，加「设定」；`genres.md` 写全新闻资讯解说、产品广告和带货、教程和录屏演示三类，另有六类各一两行；`scripts/check.py`（只用标准库）和离线测试；`example/` 先放一份虚构的占位例子 |
