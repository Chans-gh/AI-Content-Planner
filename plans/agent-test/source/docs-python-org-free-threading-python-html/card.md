# 要点卡：Python experimental support for free threading

- 出处：/home/user/AI-Content-Planner/plans/agent-test/source/docs-python-org-free-threading-python-html/article.md（抓自 https://docs.python.org/3.13/howto/free-threading-python.html）；发布方：Python 官方文档（CPython）；发布日期：（页面未写）；来源等级：一手
- 读到哪：全文（第 1–91 行）。没读的：无。

| 段 | 点 | 要点（数字带单位、口径、时间） | 行号 | 原话摘录 |
|---|---|---|---|---|
| P1 | a | 自由线程（free threading）指关掉 GIL 的 CPython 构建；页面写明它是「experimental」（实验性）。文中只提到 PEP 703，标题为 "Making the Global Interpreter Lock Optional in CPython"，未写明状态为正式或实验以外的其他地位 | 12, 14, 20 | 「Starting with the 3.13 release, CPython has experimental support for a build of Python called free threading where the global interpreter lock (GIL) is disabled.」；「The free-threaded mode is experimental」；「PEP 703 – Making the Global Interpreter Lock Optional in CPython」 |
| P1 | b | 安装：3.13 起 macOS、Windows 官方安装包可选装自由线程版；其他平台见社区安装指南；源码构建用 `--disable-gil` 配置项。确认：`python -VV` 和 `sys.version` 含 “experimental free-threading build”；运行时用 `sys._is_gil_enabled()` 查 GIL 是否真的关着；构建配置用 `sysconfig.get_config_var("Py_GIL_DISABLED")`，值为 1 即支持（页面称这是推荐方式）。运行时可用环境变量 PYTHON_GIL 或 `-X gil` 把 GIL 重新打开 | 24, 26, 28, 32, 34, 38 | 「the official macOS and Windows installers optionally support installing free-threaded Python binaries」；「`--disable-gil` configure option should be used」；「This is the recommended mechanism for decisions related to the build configuration.」 |
| P1 | b | 可执行文件名：页面没有写（没有 python3.13t 之类的名字） | — | — |
| P1 | c | 单线程性能：3.13 的自由线程构建在 pyperformance 上额外开销约 40%；程序大部分时间在 C 扩展或 I/O 里则影响较小；最大原因是自适应解释器（PEP 659）在自由线程构建里被禁用；目标是后续版本降到 10% 以下（对比默认 GIL 构建） | 14, 90 | 「In 3.13, this overhead is about 40% on the pyperformance suite.」；「We are aiming for an overhead of 10% or less on the pyperformance suite compared to the default GIL-enabled build.」 |
| P1 | c | C 扩展兼容：页面只给出指向 “C API Extension Support for Free Threading” 的指引，没有写具体处理办法；导入未显式声明支持自由线程的 C-API 扩展模块时，GIL 会自动打开并打印警告；另有两个跟踪包支持情况的网站 | 16, 40, 42–46 | 「See C API Extension Support for Free Threading for information on how to write C extensions」；「The GIL may also automatically be enabled when importing a C-API extension module that is not explicitly marked as supporting free threading. A warning will be printed in this case.」 |
| P1 | 旁注 | 线程安全：内置类型 dict、list、set 用内部锁，行为与 GIL 版相近，但页面称这只是当前实现的描述，不是保证；建议改用 threading.Lock（可作为补充，计划未列） | 50, 52–54 | 「this should be treated as a description of the current implementation, not a guarantee」 |

## 和框架对不上的

- Q1（PEP 编号和 3.13 地位）：原文给了 PEP 703，地位写的是 “experimental”，够用；但原文没有 “正式 / 实验 之外” 的其他说明，计划里的「实验性还是正式」只能答「实验性」。
- Q2（可执行文件名）：原文没有写，原文里找不到可执行文件名。查 GIL 状态的办法原文有（`sys._is_gil_enabled()`）。这一项缺口未补上，需另找来源（例如 python.org 安装说明或 free-threading 安装指南，非本原文）。
- Q3（性能口径）：原文给出 3.13 的 40% 和 3.14 目标的 10% 以下，口径是 pyperformance 对比默认 GIL 版；C 扩展兼容只有指引，没有「处理办法」细节，计划里的「怎么处理」需要靠指引文档（原文未抓取）或 C API 文档补。
- 框架里 P1 一段放三点，篇幅 300–500 字；原文的 JIT 等内容与计划的取舍无关，未读到需要更正的地方。
- 没有发现和框架冲突的内容。原文有 “In 3.13” 和 “3.14 expected” 的时间区分，写稿时注意不要把 3.14 的目标写成 3.13 的现状。
