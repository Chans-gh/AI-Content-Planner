#!/usr/bin/env python3
"""从 plans/<短名>/ 生成给下游看的精简版，打到标准输出；只生成，不存档。

用法：python3 -I <本 Skill 目录>/scripts/brief.py <plans/短名 目录> [--out 文件]

只用标准库，读法和 check.py 一样（按标题找节、按表头找表）。先过 check.py（不加 --handoff）；
有错就把错打到标准错误、退出码 1，不出精简版。
主要读 content.md（格式 5 的唯一交付物）：总则、红线、约束；每段的段头、看什么、念什么（标级别）、
去向是念或上屏的信息；不能送生成的素材、衍生；末尾是每段的字数表（估算）。plan.md 只取一句话主线和选中的打法。
状态不是「已交接」时，开头写一行提醒。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check as c  # noqa: E402


def read(folder, name):
    with open(os.path.join(folder, name), encoding='utf-8') as f:
        return f.read()


def section_map(text):
    title, secs = c.parse_md(text)
    out = {}
    for name, lines in secs:
        out.setdefault(name, lines)
    return title, out


def rows(lines, head):
    t = c.find_table(lines or [], head)
    return [] if t is None else [r for r in t[1] if not c.is_placeholder(r.get(head[0], '')) and r.get(head[0], '').strip()]


def br(cell):
    return re.sub(r'<br\s*/?>', '；', cell).strip()


def budget(ctext):
    """每段字数 → [(段号, 篇幅秒数或 None, 原句 + 必讲, 全部, 上限或 None)]；上限 = 篇幅 × 语速档，只是估算"""
    _, cm = section_map(ctext)
    gen = {r['项']: r['内容'] for r in rows(cm.get('总则'), ['项', '内容', '依据'])}
    rate = c.RATES.get(gen.get('语速', '').strip()[:1])
    out = []
    for pid, _, subs in c.segments(ctext):
        if not pid:
            continue
        head = {r['项']: r['内容'] for r in rows(subs.get(''), ['项', '内容'])}
        says = rows(subs.get('念什么'), c.SAY_HEAD)
        must = sum(c.char_count(c.spoken(r['句'])) for r in says if r['级'].strip() in (c.ORIGINAL, c.MUST))
        total = sum(c.char_count(c.spoken(r['句'])) for r in says)
        e = c.parse_extent(head.get('篇幅', ''))
        secs = (e[1] + e[2]) / 2 if e and e[0] == '时间' else None
        out.append((pid, secs, must, total, secs * rate if secs and rate else None))
    return out


def brief(folder):
    ptext, ctext = read(folder, 'plan.md'), read(folder, 'content.md')
    _, p = section_map(ptext)
    title, cm = section_map(ctext)
    out = [f'# 精简版：{title.split("：", 1)[-1]}', '']
    state = c.status_of(ctext) or ''
    out.append(f'> 从 `content.md` 生成，不存档；以它为准。状态：{state}')
    if state not in c.HANDOFF_STATES:
        out.append('> 还没交接，下面的内容会变。')
    out.append('')
    main_line = next((l.split('：', 1)[1].strip() for l in p.get('立意', []) if l.startswith('一句话主线')), '')
    if main_line:
        out += [f'**主线**：{main_line}', '']
    play = [r for r in rows(p.get('立意'), c.PLAY_HEAD) if r['选'] == '选']
    if play:
        r = play[0]
        out += [f'**打法**：{r["打法"]}（抓 {r["抓哪条阻力"]}，用 {r["用哪个杠杆"]}）；开头 {r["开头"]}', '']

    out += ['## 总则', '']
    out += [f'- **{r["项"]}**：{br(r["内容"])}' for r in rows(cm.get('总则'), ['项', '内容', '依据'])]
    out.append('')
    reds = rows(cm.get('红线'), c.LINE_HEAD)
    if reds:
        out += ['## 红线', '']
        out += [f'- {r["#"]} 不许：{r["不许"]}（{r["怎么查"]}）' for r in reds]
        out.append('')
    rules = rows(cm.get('约束'), c.RULE_HEAD)
    if rules:
        out += ['## 约束（生成、重画、合成都要守）', '']
        out += [f'- {r["#"]}〔{r["状态"]}〕{r["必须守的样子"]}' for r in rules]
        out.append('')

    out += ['## 每段', '']
    for pid, name, subs in c.segments(ctext):
        if not pid:
            continue
        head = {r['项']: r['内容'] for r in rows(subs.get(''), ['项', '内容'])}
        out += [f'### {name}（{head.get("篇幅", "")}；情绪 {head.get("情绪", "")}，节奏 {head.get("节奏", "")}）', '',
                f'- 从 → 到：{head.get("从 → 到", "")}']
        for letter, point in c.parse_points(head.get('要讲的点', '')) or []:
            out.append(f'- {letter}. {point}')
        for h in rows(subs.get('看什么'), c.VIEW_HEAD):
            out.append(f'- 看 {h["#"]}〔{h["来源"]} · {h["主角"]}〕{h["要看到什么"]}；最大的字：{h["最大的字"]}；上屏：{h["上屏的字"]}；配 {h["配哪句"]}')
        for s in rows(subs.get('念什么'), c.SAY_HEAD):
            out.append(f'- 念 {s["#"]}〔{s["级"]}〕{s["句"]}（{s["依据"]}）')
        for d in rows(subs.get('信息'), c.DATA_HEAD):
            to = c.parse_to(d['去向'])
            if to['不讲'] is not None or not (to['念'] or to['上屏']):
                continue
            must = f'；必须写清：{d["必须写清的"]}' if d['必须写清的'] not in ('', '—', c.NONE) and not c.is_placeholder(d['必须写清的']) else ''
            out.append(f'- {d["#"]}〔{d["状态"]}〕{d["内容"]}{must}（{d["去向"]}）')
        out.append('')

    banned = [r for r in rows(cm.get('素材'), c.ASSET_HEAD) if c.value_of(r['能不能送生成']) != '能']
    if banned:
        out += ['## 不能送生成的素材', '']
        out += [f'- {r["#"]} {r["文件"]}：{r["能不能送生成"]}' for r in banned]
        out.append('')
    spins = rows(cm.get('衍生'), c.SPIN_HEAD)
    if spins:
        out += ['## 衍生', '']
        out += [f'- {r["条"]}（{r["放在哪"]}）：{r["第一句"]}；用 {r["用哪些点"]}' for r in spins]
        out.append('')
    nums = budget(ctext)
    if any(n[4] for n in nums):
        out += ['## 字数（估算，以配音实测为准）', '', '| 段 | 篇幅 | 原句 + 必讲 | 全部 | 上限 | 85% | 115% |', '|---|---|---|---|---|---|---|']
        for pid, secs, must, total, limit in nums:
            if limit:
                out.append(f'| {pid} | {secs:g} 秒 | {must} | {total} | {limit:.0f} | {limit * c.MUST_SHARE:.0f} | {limit * c.ALL_SHARE:.0f} |')
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='从 content.md 生成精简版')
    ap.add_argument('folder')
    ap.add_argument('--out', help='写进这个文件；不给就打到标准输出')
    a = ap.parse_args(argv)
    r = c.check(a.folder)
    if r.errors:
        for e in r.errors:
            print(e, file=sys.stderr)
        print(f'{len(r.errors)} 个错：先按 check.py 修好再生成', file=sys.stderr)
        return 1
    text = brief(a.folder)
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
