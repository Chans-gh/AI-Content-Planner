#!/usr/bin/env python3
"""生成介绍页里的示意图（纯 SVG，中英各一套）。

只处理结构不变、文字要换语言的图，所以布局写在代码里、文字放进 LABELS。
改图改这里，然后重跑：

    python3 site/build-diagrams.py

产出：site/assets/diagrams/{zh,en}/*.svg
"""

import os
import xml.etree.ElementTree as ET

INK = "#15171b"
MUTED = "#5f6570"
LINE = "#e5e0d6"
CARD = "#ffffff"
PANEL = "#f6f3ec"
ACCENT = "#0f5f4e"
ACCENT_SOFT = "#eaf3ef"
WARN = "#8a4b00"
WARN_SOFT = "#fdf3e3"
SOFT = "#f1ede4"

FONT = '-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,Microsoft YaHei,sans-serif'
MONO = 'ui-monospace,SFMono-Regular,Menlo,monospace'

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "diagrams")


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
            '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10 z" fill="{MUTED}"/></marker>'
            '<marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10 z" fill="{ACCENT}"/></marker></defs>',
        ]

    def rect(self, x, y, w, h, fill=CARD, stroke=LINE, r=10, dash=None, sw=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'
        )

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight=400, mono=False):
        fam = MONO if mono else FONT
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>'
        )

    def line(self, x1, y1, x2, y2, stroke=LINE, sw=1, arrow=False, accent=False, dash=None):
        if arrow:
            stroke = ACCENT if accent else MUTED
            m = ' marker-end="url(#ag)"' if accent else ' marker-end="url(#a)"'
        else:
            m = ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{sw}"{m}{d}/>'
        )

    def path(self, d, stroke=MUTED, sw=1.4, arrow=True, accent=False, dash=None):
        m = ""
        if arrow:
            m = ' marker-end="url(#ag)"' if accent else ' marker-end="url(#a)"'
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{ACCENT if accent else stroke}" '
            f'stroke-width="{sw}"{m}{ds}/>'
        )

    def pill(self, x, y, w, h, label, fill=ACCENT_SOFT, stroke=ACCENT, color=ACCENT, size=12.5, mono=False):
        self.rect(x, y, w, h, fill=fill, stroke=stroke, r=h / 2, sw=1)
        self.text(x + w / 2, y + h / 2 + size * 0.36, label, size=size, fill=color,
                  anchor="middle", weight=600, mono=mono)

    def save(self, path):
        self.parts.append("</svg>")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        raw = "\n".join(self.parts) + "\n"
        ET.fromstring(raw)  # 生成时顺手验一下是不是合法 XML
        with open(path, "w") as f:
            f.write(raw)


# ---------------------------------------------------------------- 图 1：首屏
def hero(L):
    s = Svg(520, 452)
    s.rect(0, 0, 520, 452, fill=CARD, stroke=LINE, r=16)
    steps = [
        (24, L["s1"], L["s1f"]),
        (132, L["s2"], L["s2f"]),
        (240, L["s3"], L["s3f"]),
    ]
    for i, (y, name, artifact) in enumerate(steps):  # noqa: B007
        s.rect(28, y, 300, 76, fill=CARD, stroke=LINE, r=12)
        s.rect(44, y + 20, 36, 36, fill=ACCENT_SOFT, stroke=ACCENT_SOFT, r=10)
        s.text(62, y + 43, f"{i + 1:02d}", size=12.5, fill=ACCENT, anchor="middle", weight=600)
        s.text(92, y + 34, name, size=15, weight=600)
        s.text(92, y + 56, artifact, size=11.5, fill=MUTED, mono=True)
        s.pill(352, y + 21, 140, 34, L["gates"][i], size=12.5)
    s.line(178, 104, 178, 128, arrow=True)
    s.line(178, 212, 178, 236, arrow=True)

    s.rect(28, 344, 464, 48, fill=PANEL, stroke=LINE, r=12)
    s.text(48, 374, "check.py --handoff", size=12, fill=INK, mono=True)
    s.line(200, 368, 298, 368, arrow=True)
    s.pill(312, 352, 158, 32, L["handed"], size=12.5)
    s.text(260, 428, L["next"], size=12, fill=MUTED, anchor="middle")
    return s


# ---------------------------------------------------------------- 图 2：六问
def six(L):
    s = Svg(760, 232)
    s.rect(0, 0, 760, 232, fill=CARD, stroke=LINE, r=16)
    s.rect(20, 66, 140, 100, fill=PANEL, stroke=LINE, r=12)
    s.text(90, 106, L["input1"], size=13.5, anchor="middle", weight=600)
    s.text(90, 128, L["input2"], size=11.5, fill=MUTED, anchor="middle")
    s.line(162, 116, 194, 116, arrow=True)
    names = L["qs"]
    xs = [204, 352, 500]
    ys = [46, 124]
    for i, n in enumerate(names):
        x, y = xs[i % 3], ys[i // 3]
        s.rect(x, y, 132, 62, fill=CARD, stroke=LINE, r=11)
        s.text(x + 14, y + 24, f"{i + 1}", size=11, fill=ACCENT, weight=600)
        s.text(x + 14, y + 45, n, size=13, weight=600)
    s.line(640, 116, 664, 116, arrow=True)
    s.text(668, 112, "plan.md", size=11, fill=MUTED, mono=True)
    s.text(668, 128, "content.md", size=11, fill=MUTED, mono=True)
    return s


# ---------------------------------------------------------------- 图 3：打法
def angle(L):
    s = Svg(760, 268)
    s.rect(0, 0, 760, 268, fill=CARD, stroke=LINE, r=16)
    for i, (y, name) in enumerate([(38, L["a"]), (106, L["b"]), (174, L["c"])]):
        s.rect(24, y, 196, 58, fill=CARD, stroke=LINE, r=11)
        s.text(40, y + 26, name, size=13.5, weight=600)
        s.text(40, y + 45, L["diff"], size=11, fill=MUTED)
    s.line(224, 134, 262, 134, arrow=True, accent=True)
    s.rect(266, 96, 150, 76, fill=ACCENT_SOFT, stroke=ACCENT, r=12)
    s.text(341, 126, L["picked"], size=13.5, fill=ACCENT, anchor="middle", weight=600)
    s.text(341, 148, L["picked2"], size=11, fill=ACCENT, anchor="middle")
    s.line(420, 134, 458, 134, arrow=True, accent=True)
    s.rect(462, 34, 276, 200, fill=CARD, stroke=LINE, r=12)
    s.text(478, 58, L["frame"], size=13, weight=600)
    for i in range(4):
        y = 74 + i * 36
        s.rect(478, y, 244, 28, fill=PANEL, stroke=PANEL, r=8)
        s.text(490, y + 19, f"P{i + 1}", size=11.5, fill=ACCENT, mono=True)
        s.text(518, y + 19, L["row"], size=11.5, fill=MUTED)
    s.text(478, 222, L["more"], size=11.5, fill=MUTED)
    return s


# ---------------------------------------------------------------- 图 4：一条信息
def fact(L):
    s = Svg(760, 252)
    s.rect(0, 0, 760, 252, fill=CARD, stroke=LINE, r=16)
    s.rect(24, 30, 452, 192, fill=CARD, stroke=LINE, r=12)
    s.text(44, 58, "P1-1", size=14, fill=ACCENT, mono=True, weight=600)
    s.text(110, 58, L["fact"], size=13, weight=600)
    rows = L["fields"]
    for i, (k, v) in enumerate(rows):
        y = 84 + i * 34
        s.text(44, y, k, size=12, fill=MUTED)
        s.text(150, y, v, size=12, mono=(i == 1))
    for i, (label, fill, color) in enumerate(L["states"]):
        y = 44 + i * 44
        s.rect(504, y, 228, 36, fill=fill, stroke=fill, r=18)
        s.text(618, y + 23, label, size=12.5, fill=color, anchor="middle", weight=600)
    return s


# ---------------------------------------------------------------- 图 5：检查关
def gate(L):
    s = Svg(760, 252)
    s.rect(0, 0, 760, 252, fill=CARD, stroke=LINE, r=16)
    s.rect(24, 66, 140, 44, fill=PANEL, stroke=LINE, r=10)
    s.text(94, 93, "plan.md", size=12, anchor="middle", mono=True)
    s.rect(24, 140, 140, 44, fill=PANEL, stroke=LINE, r=10)
    s.text(94, 167, "content.md", size=12, anchor="middle", mono=True)
    s.line(166, 114, 208, 114, arrow=True)
    s.line(166, 162, 208, 140, arrow=True)
    s.rect(212, 30, 250, 192, fill=CARD, stroke=ACCENT, r=12, dash="5 4")
    s.text(337, 58, "check.py --handoff", size=12, fill=ACCENT, anchor="middle", mono=True)
    for i in range(4):
        y = 78 + i * 30
        s.rect(240, y, 194, 18, fill=ACCENT_SOFT, stroke=ACCENT_SOFT, r=6)
        s.text(252, y + 14, L["conds"][i], size=11, fill=ACCENT)
    s.text(337, 210, L["eight"], size=11, fill=MUTED, anchor="middle")
    s.line(464, 88, 512, 88, arrow=True, accent=True)
    s.pill(516, 70, 208, 36, L["pass"], size=12.5)
    s.line(464, 172, 512, 172, arrow=True)
    s.pill(516, 154, 208, 36, L["fail"], fill=WARN_SOFT, stroke=WARN, color=WARN, size=12.5)
    s.text(620, 216, L["failnote"], size=11, fill=MUTED, anchor="middle")
    return s


# ---------------------------------------------------------------- 图 6：三条安装路
def install(L):
    s = Svg(760, 236)
    s.rect(0, 0, 760, 236, fill=CARD, stroke=LINE, r=16)
    cards = [
        (30, "Codex", "plugin marketplace"),
        (270, "WorkBuddy", "ai-content-planner.zip"),
        (510, "DeepSeek Harness", "install.sh dsh"),
    ]
    for x, name, sub in cards:
        s.rect(x, 30, 220, 74, fill=CARD, stroke=LINE, r=12)
        s.text(x + 18, 60, name, size=13.5, weight=600)
        s.text(x + 18, 82, sub, size=11, fill=MUTED, mono=True)
        s.line(x + 110, 106, x + 110, 138, arrow=True)
    s.rect(30, 142, 700, 54, fill=PANEL, stroke=LINE, r=12)
    s.text(380, 176, L["target"], size=13, anchor="middle", weight=600)
    s.text(380, 216, L["nokey"], size=11.5, fill=MUTED, anchor="middle")
    return s


# ---------------------------------------------------------------- 图 7：回流
def loop(L):
    s = Svg(760, 240)
    s.rect(0, 0, 760, 240, fill=CARD, stroke=LINE, r=16)
    s.pill(30, 88, 150, 44, L["done"], size=13)
    s.line(184, 110, 232, 110, arrow=True, accent=True)
    s.rect(236, 76, 200, 68, fill=CARD, stroke=LINE, r=12)
    s.text(336, 104, L["down1"], size=13, anchor="middle", weight=600)
    s.text(336, 126, L["down2"], size=11.5, fill=MUTED, anchor="middle")
    s.line(440, 110, 488, 110, arrow=True)
    s.rect(492, 76, 240, 68, fill=CARD, stroke=LINE, r=12)
    s.text(612, 104, L["gap1"], size=12.5, anchor="middle", weight=600)
    s.text(612, 126, L["gap2"], size=11.5, fill=MUTED, anchor="middle")
    s.path("M 612 148 L 612 184 L 105 184 L 105 140", arrow=True, accent=True)
    s.text(360, 206, L["back"], size=12, fill=ACCENT, anchor="middle", weight=600)
    return s


LABELS = {
    "zh": {
        "hero": {
            "s1": "定效果", "s1f": "plan.md 效果、形式",
            "s2": "定框架", "s2f": "立意、打法、分段",
            "s3": "补齐内容", "s3f": "content.md 每条带来源",
            "gates": ["你确认 ✓", "你确认 ✓", "交接条件 ✓"], "handed": "已交接 ✓",
            "next": "下游 · 选风格、写分镜、出片",
        },
        "six": {
            "input1": "你的一句话", "input2": "和给的材料",
            "qs": ["接触时刻", "起点", "阻力", "终点", "衡量", "杠杆"],
        },
        "angle": {
            "a": "打法 A", "b": "打法 B", "c": "打法 C",
            "diff": "抓哪条阻力 · 用哪个杠杆",
            "picked": "选定 A", "picked2": "你挑一个",
            "frame": "框架：每段四件事", "row": "从 → 到 · 要讲的点", "more": "… 一直排到 P8",
        },
        "fact": {
            "fact": "这条信息", "fields": [
                ("内容", "美东 4 月 6 日 19:02 到达离地球最远处 252,756 英里"),
                ("种类", "B1"),
                ("来源", "NASA 返回新闻稿 · 导语 · 一手"),
                ("必须写清的", "口径、统计方、日期、单位"),
            ],
            "states": [("已核实", ACCENT_SOFT, ACCENT), ("待核实", SOFT, MUTED),
                       ("有冲突", WARN_SOFT, WARN), ("已过期", SOFT, MUTED)],
        },
        "gate": {
            "conds": ["有「效果」「框架」两行", "缺口表没有待补的行", "每个点都有信息对应", "没有待核实和冲突"],
            "eight": "交接条件一共 8 条",
            "pass": "已交接 ✓", "fail": "拦下，不许交接",
            "failnote": "把空模板原样跑一遍：24 个错、2 个提示",
        },
        "install": {
            "target": "装进你的助手", "nokey": "只用 Python 标准库 · 不要 API Key",
        },
        "loop": {
            "done": "已交接", "down1": "下游出片", "down2": "选风格、写分镜",
            "gap1": "缺口表加一行", "gap2": "状态改「回流中」",
            "back": "回流中：回到第 3 步补齐，再改回「已交接」",
        },
    },
    "en": {
        "hero": {
            "s1": "Effect", "s1f": "plan.md effect + form",
            "s2": "Frame", "s2f": "throughline, angle, segments",
            "s3": "Content", "s3f": "content.md every fact sourced",
            "gates": ["your nod ✓", "your nod ✓", "conditions ✓"], "handed": "handed off ✓",
            "next": "next: style, storyboard, render",
        },
        "six": {
            "input1": "Your one line", "input2": "plus whatever you bring",
            "qs": ["Moment", "Start", "Resistance", "End state", "Measure", "Leverage"],
        },
        "angle": {
            "a": "Angle A", "b": "Angle B", "c": "Angle C",
            "diff": "which resistance · which leverage",
            "picked": "You pick one", "picked2": "e.g. A",
            "frame": "Frame: four things a segment", "row": "from → to · points", "more": "… all the way to P8",
        },
        "fact": {
            "fact": "the fact", "fields": [
                ("Fact", "19:02 EDT, April 6: 252,756 mi from Earth"),
                ("Type", "B1"),
                ("Source", "NASA return release · lede · primary"),
                ("Must be clear", "basis, who counted, date, unit"),
            ],
            "states": [("verified", ACCENT_SOFT, ACCENT), ("unverified", SOFT, MUTED),
                       ("conflicting", WARN_SOFT, WARN), ("expired", SOFT, MUTED)],
        },
        "gate": {
            "conds": ["effect + frame logged", "no open planning gaps", "every point has a fact", "nothing unverified"],
            "eight": "eight handoff conditions in all",
            "pass": "handed off ✓", "fail": "blocked, no handoff",
            "failnote": "empty templates, run as-is: 24 errors, 2 notes",
        },
        "install": {
            "target": "into your assistant", "nokey": "standard library only · no API key",
        },
        "loop": {
            "done": "handed off", "down1": "production", "down2": "style, storyboard",
            "gap1": "a new gap row", "gap2": "status: flowing back",
            "back": "flow back: fill it in step 3, then hand off again",
        },
    },
}

BUILDERS = [
    ("hero-flow", "hero", hero),
    ("six-questions", "six", six),
    ("angle-frame", "angle", angle),
    ("fact-anatomy", "fact", fact),
    ("handoff-gate", "gate", gate),
    ("install-paths", "install", install),
    ("handoff-loop", "loop", loop),
]


def main():
    made = []
    for lang, labels in LABELS.items():
        for name, key, fn in BUILDERS:
            path = os.path.join(OUT, lang, name + ".svg")
            fn(labels[key]).save(path)
            made.append(os.path.relpath(path, os.path.dirname(OUT)))
    print(f"生成 {len(made)} 个 SVG：")
    for m in made:
        print(" ", m)


if __name__ == "__main__":
    main()
