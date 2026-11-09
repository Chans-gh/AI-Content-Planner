# 要点卡：What’s New In Python 3.13

- 出处：plans/agent-test/source/docs-python-org-3-13-html/article.md（抓自 https://docs.python.org/3.13/whatsnew/3.13.html）；发布方：Python 官方文档（Python 文档团队）；发布日期：原文未写；来源等级：一手
- 读到哪：第 Summary 节（第 22、24、36、38 行）；「New Features」中 Free-threaded CPython（第 150–166 行）、An experimental JIT compiler（第 168–202 行）；「Build Changes」（第 1066–1090 行）；「Porting」中 Changes in the C API（第 1112–1126 行）。其余小节（各模块、Deprecations、Removed 等）没读，原因：与 P1、P2 无关。

| 段 | 点 | 要点（数字带单位、口径、时间） | 行号 | 原话摘录 |
|---|---|---|---|---|
| P1 | a | 自由线程由 PEP 703 提出（原文只给 PEP 703 标题，没有提出时间）；3.13 里是「实验性支持」，不默认开启 | article.md:22, 36, 152, 164 | 「CPython 3.13 has experimental support for running with the global interpreter lock disabled.」「This is an experimental feature and therefore is not enabled by default.」 |
| P1 | b | 单独的可执行文件名 python3.13t（Windows 为 python3.13t.exe），原文写 “usually called”；官方 Windows、macOS 安装包可装自由线程预编译版（原文未提 Linux）；从源码构建用 `--disable-gil`。pkg-config 文件名为 python-3.13t.pc。运行时：`sys._is_gil_enabled()` 查 GIL 是否真关；`python -VV` 或 `sys.version` 含 “experimental free-threading build” 说明是自由线程构建；`PYTHON_GIL` 环境变量或 `-X gil=1` 可让自由线程构建运行时开启 GIL，`PYTHON_GIL=0` 或 `-X gil=0` 为显式关闭 | article.md:152, 154, 156, 158, 1088 | 「The free-threaded mode requires a different executable, usually called python3.13t or python3.13t.exe.」「The new sys._is_gil_enabled() function can be used to check whether the GIL is actually disabled in the running process.」 |
| P1 | c | 代价：原文说「expect some bugs and a substantial single-threaded performance hit」，**没有百分比，也没有版本号**（Q3 的数字缺口）。C 扩展：自由线程构建需要单独编译；支持无 GIL 运行的扩展用 `Py_mod_gil` slot；单阶段初始化的扩展用 `PyUnstable_Module_SetGIL()` 声明；未用这些机制的 C 扩展被导入时会开启 GIL（除非已用 PYTHON_GIL 或 -X gil=0 显式关掉）；安装带 C 扩展的包需要 pip 24.1 或更新版本 | article.md:154, 158 | 「expect some bugs and a substantial single-threaded performance hit」「pip 24.1 or newer is required to install packages with C extensions in the free-threaded build.」 |
| P2 | a | JIT 由 PEP 744 提出（原文只给 PEP 744 编号）；3.13 里是「basic JIT compiler」「experimental」；**默认关闭**（Summary 原句：currently disabled by default，并附「though we may turn it on later」） | article.md:22, 38, 168, 200 | 「A basic JIT compiler was added. It is currently disabled by default (though we may turn it on later).」 |
| P2 | b | 构建选项：`--enable-experimental-jit`，取值 no / yes（不写值时默认 yes）/ yes-off / interpreter。运行时环境变量：`PYTHON_JIT=0`（yes 构建里关掉 JIT）、`PYTHON_JIT=1`（yes-off 构建里开启 JIT）；interpreter 构建里 `PYTHON_JIT=0` 可关掉 Tier 2 解释器。Windows：`PCbuild/build.bat --experimental-jit`，解释器用 `--experimental-jit-interpreter`。构建依赖：新增对 LLVM 的构建期依赖（copy-and-patch 技术，运行时无依赖） | article.md:170, 172, 176, 178, 180, 192, 196 | 「yes : Enable the JIT. To disable the JIT at runtime, pass the environment variable PYTHON_JIT=0 .」「yes-off : Build the JIT but disable it by default. To enable the JIT at runtime, pass the environment variable PYTHON_JIT=1 .」 |
| P2 | c | 效果：原文只有定性说法。Summary 说「Performance improvements are modest」，并称「we expect to improve this over the next few releases」；New Features 说「may speed up some Python programs」。**没有百分比或基准数字**（Q6 的缺口）。Tier 2 解释器原文定位为主要用于调试优化流水线前段 | article.md:38, 170, 192 | 「Performance improvements are modest – we expect to improve this over the next few releases.」「which may speed up some Python programs」 |

## 和框架对不上的

- Q3 要的「单线程性能损失的百分比、哪个版本」原文没有：只有「substantial」（很大）这种定性说法。不能补数字。
- Q6 要的「性能提升的官方口径」原文没有数字：只有「modest」（有限）和「may speed up some」。不能补数字。
- Q4 的「默认开不开」原文有明确口径：Summary 说 JIT「currently disabled by default」，New Features 说只有构建时加 `--enable-experimental-jit` 才加入。两处一致；原文没说官方安装包是否包含 JIT。
- 框架 P1 b 的「运行时怎么查 GIL 是否关着」：原文用 `sys._is_gil_enabled()`。`sys.version` / `python -VV` 的 “experimental free-threading build” 只说明是不是自由线程构建，不说明 GIL 是否真的关了。讲的时候要分开。
- P1 a、P2 a 的「3.13 里是什么地位」：原文用词是 experimental（实验性）、basic（基础），两段都属于实验性，和框架没有冲突。
- 无数字冲突，原文没有与框架矛盾的说法。
