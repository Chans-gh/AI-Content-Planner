#!/usr/bin/env python3
"""按页面实际用到的字，把原字体裁成 5 个 woff2。

原字体来自 @fontsource（上游是 Noto Sans SC 400/700、Noto Serif SC 900、
JetBrains Mono 400/700，都是 SIL OFL），和 AI-Coding-Video 用的是同一批字体包，
所以字形一致；这里没有引用那个仓库的任何文件，脚本和产线都是本仓库自己的。

产物（不进仓库，发布时在 CI 里生成）：
    site/fonts/{sans-400,sans-700,serif-900,mono-400,mono-700}.woff2
    site/fonts.css          # 5 条 @font-face，页面用 <link> 引它

本地跑：

    npm install --no-save --no-package-lock --no-audit --no-fund \\
        --prefix /tmp/fontsrc $(python3 site/build-fonts.py --packages)
    FONTSRC=/tmp/fontsrc/node_modules/@fontsource python3 site/build-fonts.py

不跑也能预览：页面里 fonts.css 取不到就整段回退到系统字体栈，
字号和行高不变，只是字形换成本机字体。
"""

import html
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "fonts"
OUT_CSS = HERE / "fonts.css"

# 原字体包（版本只写在这里，CI 用 --packages 取）
PACKAGES = {"noto-sans-sc": "5.3.1", "noto-serif-sc": "5.3.1", "jetbrains-mono": "5.3.0"}

# (字体包, 字重, 输出名, 家族名, 是否只要拉丁字符)
FONTS = [
    ("noto-sans-sc", 400, "sans-400", "Planner Sans", False),
    ("noto-sans-sc", 700, "sans-700", "Planner Sans", False),
    ("noto-serif-sc", 900, "serif-900", "Planner Serif", False),
    ("jetbrains-mono", 400, "mono-400", "Planner Mono", True),
    ("jetbrains-mono", 700, "mono-700", "Planner Mono", True),
]

# 排版里会用到的标点（页面文字之外，CSS 的 content 也会用到一部分）
PUNCT = "“”‘’—–…·、，。：；！？（）《》「」【】〔〕×÷←→↑↓✓✗°％%＃#／/"


def fonts_root():
    """@fontsource 目录：环境变量优先，其次 site/.fontsrc（本地 npm --prefix 的默认位置）"""
    env = os.environ.get("FONTSRC")
    if env:
        return Path(env)
    return HERE / ".fontsrc" / "node_modules" / "@fontsource"


def page_chars():
    """页面（含 CSS 的 content 文案）里出现的所有字 + ASCII + 常用标点"""
    chars = set()
    text = (HERE / "index.html").read_text(encoding="utf-8")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.S)
    chars |= set(html.unescape(re.sub(r"<[^>]+>", "", text)))
    css = (HERE / "assets" / "site.css").read_text(encoding="utf-8")
    for value in re.findall(r'content:\s*"([^"]*)"', css):
        chars |= set(value)
    chars |= {chr(c) for c in range(0x20, 0x7F)}
    chars |= set(PUNCT)
    return {c for c in chars if c != "\n" and c != "\t"}


def weight_slices(pkg, weight, chars):
    """从 @fontsource 的字重 CSS 里挑出覆盖这些字的分片"""
    root = fonts_root()
    css = (root / pkg / f"{weight}.css").read_text(encoding="utf-8")
    picked = []
    for block in re.findall(r"@font-face\s*{(.*?)}", css, re.S):
        src = re.search(r"url\(\./files/([^)]+\.woff2)\)", block)
        if not src:
            continue
        rng = re.search(r"unicode-range:\s*([^;]+);", block)
        if not rng:
            picked.append(src.group(1))
            continue
        spans = []
        for part in rng.group(1).split(","):
            part = part.strip().upper().replace("U+", "")
            a, _, b = part.partition("-")
            try:
                spans.append((int(a, 16), int(b or a, 16)))
            except ValueError:
                continue
        if any(any(lo <= ord(ch) <= hi for lo, hi in spans) for ch in chars):
            picked.append(src.group(1))
    return [root / pkg / "files" / f for f in picked]


def build_one(pkg, weight, chars, out):
    """挑分片 → 各自子集化 → 合并 → 存 woff2，返回分片数"""
    from fontTools import subset
    from fontTools.merge import Merger
    from fontTools.ttLib import TTFont

    slices = weight_slices(pkg, weight, chars)
    if not slices:
        sys.exit(f"没有覆盖到 {pkg} {weight} 的字，@fontsource 装好了吗？")
    text = "".join(sorted(chars))
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for k, src in enumerate(slices):
            font = TTFont(src)
            opts = subset.Options()
            opts.layout_features = ["*"]
            opts.notdef_outline = True
            sub = subset.Subsetter(opts)
            sub.populate(text=text)
            sub.subset(font)
            font.flavor = None
            p = Path(tmp) / f"{k}.ttf"
            font.save(p)
            parts.append(str(p))
        merged = Merger().merge(parts) if len(parts) > 1 else TTFont(parts[0])
        merged.flavor = "woff2"
        # 时间戳取原字体的：同样的页面重新裁出来逐字节相同，不会每次构建都多出一份改动
        head = TTFont(slices[0])["head"]
        merged.recalcTimestamp = False
        merged["head"].created, merged["head"].modified = head.created, head.modified
        merged.save(out)
    return len(slices)


def write_css():
    lines = [
        "/* 由 site/build-fonts.py 生成，不进仓库（发布时在 CI 里产出）。",
        "   字体：Noto Sans SC 400/700、Noto Serif SC 900、JetBrains Mono 400/700，SIL OFL。",
        "   本地预览没跑这一步时，整段取不到，页面自动回退到系统字体栈。 */",
        "",
    ]
    for _, weight, name, family, _ in FONTS:
        lines += [
            "@font-face {",
            f'  font-family: "{family}";',
            "  font-style: normal;",
            f"  font-weight: {weight};",
            "  font-display: swap;",
            f'  src: url("./fonts/{name}.woff2") format("woff2");',
            "}",
            "",
        ]
    OUT_CSS.write_text("\n".join(lines), encoding="utf-8")


def main():
    if "--packages" in sys.argv:
        print(" ".join(f"@fontsource/{p}@{v}" for p, v in PACKAGES.items()))
        return
    if not fonts_root().is_dir():
        sys.exit(f"缺原字体：{fonts_root()} 不存在。先 npm install @fontsource 那几个包，"
                 "或用 FONTSRC 指向 @fontsource 目录。")
    chars = page_chars()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for pkg, weight, name, _, latin_only in FONTS:
        used = {c for c in chars if ord(c) < 0x250} if latin_only else chars
        out = OUT_DIR / f"{name}.woff2"
        n = build_one(pkg, weight, used, out)
        size = out.stat().st_size
        total += size
        print(f"  {name}.woff2  {len(used)} 字 · {n} 个分片 · {size / 1e3:.0f} KB")
    write_css()
    print(f"共 {len(FONTS)} 个 woff2，{total / 1e3:.0f} KB；已写 {OUT_CSS.name}")


if __name__ == "__main__":
    main()
