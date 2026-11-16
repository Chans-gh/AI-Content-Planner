# 介绍页

这是 `https://chans-gh.github.io/AI-Content-Planner/` 的源码，发布由 `.github/workflows/pages.yml` 完成：合并到 `main` 后自动把 `site/` 整个目录上传到 GitHub Pages。

- `index.html`：单页，中英双语（右上角切换，默认中文），所有样式和脚本都在本目录，不引 CDN。
- `assets/site.css`、`assets/site.js`：样式和语言切换。
- `assets/diagrams/{zh,en}/`：七张示意图（首屏一张，其余分在五节里），纯 SVG、无外部依赖、中英各一套。
- `build-diagrams.py`：图的生成脚本（只用标准库）。图和页面里的文字一样要换语言，所以文字全在脚本的 `LABELS` 里，布局写在函数里；改图就改脚本，然后：

  ```bash
  python3 site/build-diagrams.py
  ```

- `llms.txt`：给 AI 检索用的摘要。

改文案只改 `index.html`；改图改 `build-diagrams.py` 再重跑。页面里的案例原文来自 `docs/replay/news-artemis/`，改案例时记得同步。本地预览：

```bash
python3 -m http.server -d site 8000
```
