# 内容策划

做内容之前的策划：先从用户的一句话、要求、链接、文件、图片、音视频里挖出要的**效果**（看完要受众怎样）和**形式**，再按效果排框架、补齐内容、写参考说法，每步请用户确认，补齐后交给下游——做视频交给 [ai-coding-video](https://github.com/Chans-gh/AI-Coding-Video)，做 PPT、课件、报告等交给对应的 Skill。

给 AI 助手用时见 [SKILL.md](SKILL.md)。

## 和下游怎么分工

| 步 | 谁做 | 产出 |
|---|---|---|
| 1 挖效果和形式、2 打法和框架、3 补齐内容 | 本 Skill | 用户项目的 `plans/<短名>/plan.md`、`content.md`、`source/` |
| 之后：做成品 | 下游 Skill（视频是 ai-coding-video） | 下游自己的目录，如 `videos/<短名>/` |

两边不互相调用，靠 `plans/<短名>/` 衔接，格式写在 [handoff.md](handoff.md)（格式 3）。下游发现缺内容，在 `plan.md` 的缺口表加一行，回到本 Skill。

## 里面有什么

| 路径 | 内容 |
|---|---|
| [`SKILL.md`](SKILL.md) | 入口：什么时候用、三步、每步怎么做、读到什么程度、核实、交接、回流、规矩 |
| [`effect.md`](effect.md) | 效果和形式怎么挖、打法和框架怎么排、说法、素材、约束、衍生怎么写；不分类型 |
| [`handoff.md`](handoff.md) | 交接说明：给下游 Skill 看的文件、编号、格式版本、能改哪里 |
| [`formats.md`](formats.md) | 各输出形式的篇幅单位、注意力预算按什么算、交给谁（一张表） |
| [`types.md`](types.md) | 信息的种类（7 大类 32 小类和「设定」）和每类必须写清的 |
| [`templates/plan.md`](templates/plan.md) | 策划稿模板 |
| [`templates/content.md`](templates/content.md) | 内容表模板（每段一节） |
| [`example/`](example/) | 填好的例子：Artemis II 的 60 秒短解说，事实全部来自 NASA 公开来源 |
| [`scripts/check.py`](scripts/check.py) | 检查两份文件；`--handoff` 按交接条件查 |
| [`scripts/brief.py`](scripts/brief.py) | 从两份文件生成给下游看的精简版，打到屏幕（`--out` 写文件），不存档 |
| [`scripts/fetch_article.py`](scripts/fetch_article.py) | 抓原文：网页落成 `plans/<短名>/source/<名字>/` 的正文和图表清单（原图加 `--images` 才下载），用法和产物写在文件开头 |
| [`scripts/tests/`](scripts/tests/) | 三个脚本的离线测试：`check.py`、`brief.py` 用夹具和例子，`fetch_article.py` 在本机起假网站，不连外网 |
| [`../agents/`](../agents/) | 随包的子代理 `finder`（检索、抓原文）、`reader`（读长原文写要点卡），都用 haiku；Claude Code 插件自动带上，`install.sh claude` 拷到 `.claude/agents/` |
| [`CHANGELOG.md`](CHANGELOG.md) | 更新记录 |

## 检查脚本

```bash
python3 -I <本 Skill 目录>/scripts/check.py plans/<短名>            # 格式：节、表头、编号、引用、取值、篇幅
python3 -I <本 Skill 目录>/scripts/check.py plans/<短名> --handoff  # 再加交接条件
python3 -I <本 Skill 目录>/scripts/brief.py plans/<短名>            # 精简版，先过 check.py
```

脚本都只用 Python 标准库。按标题找节、按表头找表，不依赖行号。每个问题一行「文件:节: 问题」，最后一行「通过」或「N 个错、M 个提示」；有错退出码 1。

## 维护

- 设计记录在仓库的 `docs/`（PRD、SPEC、回放，不随 Skill 安装）；实施完成后以本 Skill 为准。
- 改模板的节名、表头、取值时，`scripts/check.py` 的常量、`scripts/tests/fixtures/`、`handoff.md` 一起改，格式号加 1；再在仓库根目录跑 `python3 scripts/selfcheck.py`。
- 加输出形式：`formats.md` 的表加一行（篇幅单位、注意力预算按什么算、交给谁），模板形式「输出形式和规格」的选项跟着加，测试会核对两边一致。
- `types.md` 的大类和代号只增不改，加小类在它末尾的修改记录记一行。
- 每次改动在 [CHANGELOG.md](CHANGELOG.md) 表头下加一行；改了行为的升 `SKILL.md` 的 `version`，两份 `plugin.json` 跟着改。
- 发版：合并到 `main` 后推标签 `v<version>`（和 `SKILL.md` 的 `version` 一致），`.github/workflows/release.yml` 自检、打 zip、发 Release；插件市场直接读 `main`，不用另发。
- 本 Skill 不带素材和生成服务；抓网页用 `scripts/fetch_article.py`（只用标准库，不要 Key），别的读取用宿主自带的工具。
