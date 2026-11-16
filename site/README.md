# 介绍页

这是 `https://chans-gh.github.io/AI-Content-Planner/` 的源码，发布由 `.github/workflows/pages.yml` 完成：合并到 `main` 后自动把 `site/` 整个目录上传到 GitHub Pages。

- `index.html`：单页，中英双语（右上角切换，默认中文；`?lang=en` 可以直接进英文），深色跟随系统。所有样式和脚本都在本目录，不引 CDN、不引外链。
- `assets/site.css`、`assets/site.js`：样式和语言切换。
- `assets/diagrams/{zh,en,zh-dark,en-dark}/`：七张示意图（首屏一张，其余分在五节里），纯 SVG、无外部依赖；中英各一套，深色各一套，共 28 个文件。
- `build-diagrams.py`：图的生成脚本（只用标准库）。图和页面里的文字一样要换语言，所以文字全在脚本的 `LABELS` 里，布局写在函数里，配色在 `LIGHT`/`DARK` 两张表里（和 `site.css` 的 token 一一对应）；改图就改脚本，然后：

  ```bash
  python3 site/build-diagrams.py
  ```

- `build-fonts.py`：字体子集化。按 `index.html`（连 CSS 里 `content:` 的字）实际用到的 550 个字，把 `@fontsource` 的 Noto Sans SC 400/700、Noto Serif SC 900、JetBrains Mono 400/700 裁成 5 个 woff2（共约 260 KB），并写出 `fonts.css`。这两个产物不进仓库，发布时由 `pages.yml` 生成：

  ```bash
  npm install --no-save --no-package-lock --prefix /tmp/fontsrc $(python3 site/build-fonts.py --packages)
  FONTSRC=/tmp/fontsrc/node_modules/@fontsource python3 site/build-fonts.py
  ```

  需要 `fontTools`、`brotli`（`pip install fonttools brotli`）。本地不跑也能预览：`fonts.css` 取不到，页面整段回退到系统字体栈（Songti / PingFang / JetBrains Mono），字号行高不变。字重变化大（标题 900）时视觉差别明显，这是有意为之——线上用裁好的字体，本机不留二进制。

- `llms.txt`：给 AI 检索用的摘要。

版式（配色 token、1180px 容器、字号、分节编号、顶栏和页脚）和 AI-Coding-Video 的介绍页是同一套。字体和它用的是同一批上游包（Noto Sans SC / Noto Serif SC / JetBrains Mono），所以字形一致；但**页面里没有任何一处引用那个仓库**：字是这里自己裁的，图是本仓库自己画的 SVG。

改文案只改 `index.html`；改图改 `build-diagrams.py` 再重跑。页面里的案例原文来自 `docs/replay/news-artemis/`，改案例时记得同步。本地预览：

```bash
python3 -m http.server -d site 8000
```
