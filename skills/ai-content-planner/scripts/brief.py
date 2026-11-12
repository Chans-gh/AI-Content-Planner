#!/usr/bin/env python3
"""从 plans/<短名>/ 的 plan.md、content.md 生成给下游看的精简版，打到标准输出；只生成，不存档。

用法：python3 -I <本 Skill 目录>/scripts/brief.py <plans/短名 目录> [--out 文件]

只用标准库，读法和 check.py 一样（按标题找节、按表头找表）。两份文件先过 check.py（不加 --handoff）；
有错就把错打到标准错误、退出码 1，不出精简版。
内容：主线、效果、形式、每段的「从 → 到」、要讲的点、怎么证明、说法、用到的信息（内容和必须写清的）、
约束、不能送生成的素材、衍生。状态不是「已交接」时，开头写一行提醒。
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
    return [] if t is None else [r for r in t[1] if not c.is_placeholder(r.get(head[0], ''))]


def kv(lines, head):
    return [(r[head[0]], r[head[1]]) for r in rows(lines, head)]


def br(cell):
    return re.sub(r'<br\s*/?>', '；', cell).strip()


def segment_data(csecs):
    """content.md 每段一节 → {段号: [行]}，「也用」的行也算进那段"""
    own, shared = {}, {}
    for name, lines in csecs.items():
        m = re.match(r'(P\d+)(?!\d)', name)
        if not m:
            continue
        for r in rows(lines, c.DATA_HEAD):
            letters, also = c.parse_which(r['讲哪一点'])
            if letters is not None:
                own.setdefault(m.group(1), []).append(r)
            for seg, _ in also:
                shared.setdefault(seg, []).append(r)
    return {k: own.get(k, []) + shared.get(k, []) for k in set(own) | set(shared)}


def brief(folder):
    title, p = section_map(read(folder, 'plan.md'))
    _, cm = section_map(read(folder, 'content.md'))
    out = [f'# 精简版：{title.split("：", 1)[-1]}', '']
    plan_text = read(folder, 'plan.md')
    m = re.search(r'^状态[：:]\s*([^（(\n]*)', plan_text, re.M)
    state = m.group(1).strip().rstrip('。.') if m else ''
    out.append(f'> 从 `plan.md`、`content.md` 生成，不存档；以两份文件为准。状态：{state}')
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

    for name, head in (('效果', ['项', '内容']), ('形式', ['项', '内容'])):
        out += [f'## {name}', '']
        out += [f'- **{k}**：{br(v)}' for k, v in kv(p.get(name), head)]
        out.append('')

    says = rows(p.get('说法'), c.SAY_HEAD)
    data = segment_data(cm)
    out += ['## 每段', '']
    for r in rows(p.get('框架'), c.FRAME_HEAD):
        seg = r['段']
        out += [f'### {seg} {r["作用"]}（{r["篇幅"]}）', '', f'- 受众：{r["受众：从 → 到"]}']
        for letter, point in c.parse_points(r['要讲的点']) or []:
            out.append(f'- {letter}. {point}')
        out.append(f'- 怎么证明：{r["怎么证明"]}')
        for s in says:
            if any(n == seg for n, _ in c.seg_points(s['点'])):
                out.append(f'- 说法 {s["点"]}：{s["参考说法"]}（要的效果：{s["要的效果"]}；不能丢：{s["不能丢的"]}）')
        for d in data.get(seg, []):
            must = f'；必须写清：{d["必须写清的"]}' if d['必须写清的'] not in ('', '—', c.NONE) and not c.is_placeholder(d['必须写清的']) else ''
            out.append(f'- {d["#"]}〔{d["状态"]}〕{d["内容"]}{must}')
        out.append('')

    rules = rows(cm.get('约束'), c.RULE_HEAD)
    if rules:
        out += ['## 约束（生成、重画、合成都要守）', '']
        out += [f'- {r["#"]}〔{r["状态"]}〕{r["必须守的样子"]}' for r in rules]
        out.append('')
    banned = [r for r in rows(cm.get('素材'), c.ASSET_HEAD) if c.value_of(r['能不能送生成']) != '能']
    if banned:
        out += ['## 不能送生成的素材', '']
        out += [f'- {r["#"]} {r["文件"]}：{r["能不能送生成"]}' for r in banned]
        out.append('')
    spins = rows(p.get('衍生'), c.SPIN_HEAD)
    if spins:
        out += ['## 衍生', '']
        out += [f'- {r["条"]}（{r["放在哪"]}）：{r["第一句"]}；用 {r["用哪些点"]}' for r in spins]
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='从 plan.md、content.md 生成精简版')
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
