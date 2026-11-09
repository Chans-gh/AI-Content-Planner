# 内容策划

做内容之前的策划：把用户的一句话、要求、链接、文件、图片、音视频整理成立意、段落、资料底稿和缺口表，补齐内容，确认方向后交给下游——做视频交给 [ai-coding-video](https://github.com/Chans-gh/AI-Coding-Video)，做 PPT、课件、报告等交给对应的 Skill。

给 AI 助手用时见 [SKILL.md](SKILL.md)。

## 和下游怎么分工

| 阶段 | 谁做 | 产出 |
|---|---|---|
| 1 内容整理、2 补齐 | 本 Skill | 用户项目的 `plans/<短名>/plan.md`、`research.md` |
| 3 起：做成品 | 下游 Skill（视频是 ai-coding-video） | 下游自己的目录，如 `videos/<短名>/` |

两边不互相调用，靠 `plans/<短名>/` 衔接，格式写在 [handoff.md](handoff.md)（格式 1）。下游发现缺内容，在 `plan.md` 的缺口表加一行，回到本 Skill。

## 里面有什么

| 路径 | 内容 |
|---|---|
| [`SKILL.md`](SKILL.md) | 入口：什么时候用、两个阶段、读到什么程度、怎么问、写什么、交接、回流、规矩 |
| [`handoff.md`](handoff.md) | 交接说明：给下游 Skill 看的文件、编号、格式版本、能改哪里 |
| [`formats.md`](formats.md) | 各输出形式：段是什么、篇幅怎么写、交接前多查什么、交给谁（第一版写全视频） |
| [`genres.md`](genres.md) | 各内容题材的段落组织、交接前至少要有的、不算数的写法 |
| [`types.md`](types.md) | 信息的种类（7 大类 31 小类和「设定」）和每类必须写清的 |
| [`templates/plan.md`](templates/plan.md) | 策划稿模板 |
| [`templates/research.md`](templates/research.md) | 资料底稿模板 |
| [`example/`](example/) | 填好的例子：Artemis II 的 60 秒短解说，事实全部来自 NASA 公开来源 |
| [`scripts/check.py`](scripts/check.py) | 检查两份文件；`--handoff` 按交接条件查 |
| [`scripts/tests/`](scripts/tests/) | `check.py` 的离线测试和夹具 |
| [`CHANGELOG.md`](CHANGELOG.md) | 更新记录 |

## 检查脚本

```bash
python3 -I <本 Skill 目录>/scripts/check.py plans/<短名>            # 格式：节、表头、编号、引用、取值、篇幅
python3 -I <本 Skill 目录>/scripts/check.py plans/<短名> --handoff  # 再加交接条件
```

只用 Python 标准库。按标题找节、按表头找表，不依赖行号。每个问题一行「文件:节: 问题」，最后一行「通过」或「N 个错、M 个提示」；有错退出码 1。

## 维护

- 设计记录在仓库的 `docs/`（PRD、SPEC、回放，不随 Skill 安装）；实施完成后以本 Skill 为准。
- 改模板的节名、表头、取值时，`scripts/check.py` 的常量、`scripts/tests/fixtures/`、`handoff.md` 一起改，格式号加 1；再在仓库根目录跑 `python3 scripts/selfcheck.py`。
- 加输出形式：`formats.md` 加一节（四项加「交给谁」），模板立意「输出形式」的选项跟着加，测试会核对两边一致。
- `types.md` 的大类和代号只增不改，加小类在它末尾的修改记录记一行。
- 每次改动在 [CHANGELOG.md](CHANGELOG.md) 表头下加一行；改了行为的升 `SKILL.md` 的 `version`，两份 `plugin.json` 跟着改。
- 本 Skill 不带素材和生成服务；读网页、读文档用宿主自带的工具。
