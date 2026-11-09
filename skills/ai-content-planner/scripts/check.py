#!/usr/bin/env python3
"""检查 videos/<短名>/ 下的 plan.md、research.md 是否符合模板，交接前加 --handoff。

用法：python3 -I <本 Skill 目录>/scripts/check.py <videos/短名 目录> [--handoff]

只用标准库。按 Markdown 标题找节、按表头找表，不依赖行号。
输出每个问题一行「文件:节: 问题」，最后一行「通过」或「N 个错、M 个提示」。
有错退出码 1，只有提示退出码 0。
"""
import argparse
import os
import re
import sys

PLAN_SECTIONS = ['确认记录', '立意', '段落', '取舍', '缺口']
RESEARCH_SECTIONS = ['资料清单', '要哪些单元', '待核实和有冲突', '检索记录']
SEG_HEAD = ['段', '作用', '观众收益', '核心内容', '素材编排', '预计时长']
GAP_HEAD = ['编号', '段', '缺什么', '归谁', '提出于', '状态', '怎么解决的']
SRC_HEAD = ['资料', '位置', '读到哪', '用途', '能不能公开', '用到哪些编号']
UNIT_LIST_HEAD = ['单元', '回答什么', '用在哪段', '状态']
DATA_HEAD = ['#', '内容', '种类', '来源', '必须写清的', '状态']

OWNERS = {'策划', '风格后', '分镜后'}
RAISED = {'阶段 1', '阶段 2', '分镜', '制作'}
GAP_STATES = {'待补', '已补', '改内容关闭'}
DATA_STATES = {'已核实', '〔待核实〕', '有冲突', '已过期', '设定'}
UNIT_STATES = {'收集中', '够了'}
USES = {'文案依据', '画面素材', '创作参考'}
HANDOFF_STATES = {'已交接', '回流中'}

PLACEHOLDER = re.compile(r'〔[^〕]*〕')
REF_DATA = re.compile(r'(?<![A-Za-z0-9_])U(\d+)-(\d+)(?![\d])')
REF_UNIT = re.compile(r'(?<![A-Za-z0-9_])U(\d+)(?![\d-])')
REF_SEG = re.compile(r'(?<![A-Za-z0-9_])P(\d+)(?![\d])')
REF_GAP = re.compile(r'(?<![A-Za-z0-9_])Q(\d+)(?![\d])')
NUM = r'\d+(?:\.\d+)?'
UNIT_SEC = {'秒': 1, 's': 1, '分钟': 60, '分': 60, 'min': 60}
DUR_FIND = re.compile(rf'{NUM}\s*分钟?\s*{NUM}\s*秒|{NUM}\s*(?:[–\-~—至到]\s*{NUM}\s*)?(?:秒|分钟|分|min|s)(?![A-Za-z])')


def is_placeholder(cell):
    """整格只是〔〕占位（〔待核实〕是状态，不算）"""
    rest = PLACEHOLDER.sub(lambda m: '' if m.group(0) != '〔待核实〕' else m.group(0), cell).strip()
    return cell.strip() != '' and rest == ''


def parse_duration(text):
    """'45 秒'、'40–50 秒'、'1 分 30 秒'、'1 分钟 30 秒'、'2 分钟'、'约 45 秒'、'45 秒左右' → (下限, 上限) 秒；解析不了返回 None"""
    s = re.sub(r'\s+', '', text)
    s = re.sub(r'^(约|大约|~)', '', s)
    s = re.sub(r'(左右|上下)$', '', s)
    m = re.fullmatch(rf'({NUM})分钟?({NUM})秒', s)
    if m:
        v = float(m.group(1)) * 60 + float(m.group(2))
        return v, v
    m = re.fullmatch(rf'({NUM})(?:[–\-~—至到]({NUM}))?(秒|分钟|分|min|s)', s)
    if m:
        k = UNIT_SEC[m.group(3)]
        lo = float(m.group(1)) * k
        hi = float(m.group(2)) * k if m.group(2) else lo
        return (lo, hi) if lo <= hi else None
    return None


def split_row(line):
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [c.strip() for c in s.split('|')]


def parse_md(text):
    """→ (标题, [(节名, 行列表)])；按二级标题切节，第一个二级标题之前的行归在节名 '' 下"""
    title, cur = '', ('', [])
    sections = [cur]
    for line in text.split('\n'):
        if line.startswith('# ') and not title:
            title = line[2:].strip()
        elif line.startswith('## '):
            cur = (line[3:].strip(), [])
            sections.append(cur)
        else:
            cur[1].append(line)
    return title, sections


def tables(lines):
    """节里的所有表 → [(表头, [行])]，表头下一行是分隔行"""
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip().startswith('|') and i + 1 < len(lines) and re.fullmatch(r'\|?[\s:|-]+\|?', lines[i + 1].strip() or 'x'):
            head = split_row(lines[i])
            rows, i = [], i + 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(split_row(lines[i]) + [''] * len(head))
                i += 1
            out.append((head, [dict(zip(head, r)) for r in rows]))
        else:
            i += 1
    return out


def find_table(lines, need):
    """找表头含 need 里全部列的表"""
    for head, rows in tables(lines):
        if all(c in head for c in need):
            return head, rows
    return None


class Report:
    def __init__(self):
        self.errors, self.notes = [], []

    def err(self, where, msg):
        self.errors.append(f'{where}: {msg}')

    def note(self, where, msg):
        self.notes.append(f'{where}: {msg}')


def check(folder, handoff=False):
    r = Report()
    texts = {}
    for name in ('plan.md', 'research.md'):
        p = os.path.join(folder, name)
        if not os.path.isfile(p):
            r.err(name, '文件不存在')
        else:
            with open(p, encoding='utf-8') as f:
                texts[name] = f.read()
    if len(texts) < 2:
        return r

    # ---------- research.md ----------
    rtitle, rsecs = parse_md(texts['research.md'])
    rmap = {}
    for name, lines in rsecs:
        rmap.setdefault(name, lines)
    for s in RESEARCH_SECTIONS:
        if s not in rmap:
            r.err(f'research.md:{s}', '缺这一节')

    units, data = {}, {}   # 'U1' → 节名；'U1-1' → 行
    for name, lines in rsecs:
        m = re.match(r'U(\S*)', name)
        if not m:
            continue
        where = f'research.md:{name}'
        um = re.fullmatch(r'U(\d+)', m.group(0))
        if not um:
            r.err(where, f'单元编号格式不对：{m.group(0)}（写 U1、U2）')
            continue
        uid = um.group(0)
        if uid in units:
            r.err(where, f'单元编号重复：{uid}')
        units[uid] = name
        t = find_table(lines, DATA_HEAD)
        if not t:
            r.err(where, '找不到信息数据表（表头：' + ' | '.join(DATA_HEAD) + '）')
            continue
        for row in t[1]:
            did = row['#']
            if not re.fullmatch(rf'{uid}-\d+', did):
                r.err(where, f'编号格式不对：{did or "（空）"}（这一节写 {uid}-1、{uid}-2）')
                continue
            if did in data:
                r.err(where, f'编号重复：{did}')
            data[did] = row
            st = row['状态']
            if st not in DATA_STATES:
                r.err(where, f'{did} 的状态「{st}」不在 ' + ' / '.join(sorted(DATA_STATES)) + ' 里')

    sec = '资料清单'
    if sec in rmap:
        t = find_table(rmap[sec], SRC_HEAD)
        if not t:
            r.err(f'research.md:{sec}', '找不到资料表（表头：' + ' | '.join(SRC_HEAD) + '）')
        else:
            for row in t[1]:
                use = row['用途']
                if is_placeholder(use):
                    continue
                bad = [u for u in re.split(r'、', use) if u.strip() not in USES]
                if not use or bad:
                    r.err(f'research.md:{sec}', f'「{row["资料"]}」的用途「{use}」要取 ' + ' / '.join(sorted(USES)) + '，多个用「、」隔开')
    sec = '要哪些单元'
    if sec in rmap:
        t = find_table(rmap[sec], UNIT_LIST_HEAD)
        if not t:
            r.err(f'research.md:{sec}', '找不到单元表（表头：' + ' | '.join(UNIT_LIST_HEAD) + '）')
        else:
            seen = set()
            for row in t[1]:
                u = row['单元']
                if not re.fullmatch(r'U\d+', u):
                    r.err(f'research.md:{sec}', f'单元编号格式不对：{u or "（空）"}')
                elif u in seen:
                    r.err(f'research.md:{sec}', f'单元编号重复：{u}')
                seen.add(u)
                if row['状态'] not in UNIT_STATES and not is_placeholder(row['状态']):
                    r.err(f'research.md:{sec}', f'{u} 的状态「{row["状态"]}」要取 收集中 / 够了')

    # ---------- plan.md ----------
    ptitle, psecs = parse_md(texts['plan.md'])
    pmap = {}
    for name, lines in psecs:
        pmap.setdefault(name, lines)
    if not ptitle.startswith('视频策划'):
        r.err('plan.md', '第一行标题要是「# 视频策划：片名」')
    for s in PLAN_SECTIONS:
        if s not in pmap:
            r.err(f'plan.md:{s}', '缺这一节')

    m = re.search(r'^状态[：:]\s*([^（(\n]*)', texts['plan.md'], re.M)
    status = m.group(1).strip().rstrip('。.') if m else ''
    if not m:
        r.err('plan.md', '找不到状态行（「状态：……（日期）」）')

    segs, seg_rows = set(), []
    sec = '段落'
    if sec in pmap:
        tbs = tables(pmap[sec])
        if not tbs:
            r.err(f'plan.md:{sec}', '找不到段落表')
        else:
            head, rows = tbs[0]
            if head != SEG_HEAD:
                r.err(f'plan.md:{sec}', '段落表表头要正好是「' + ' | '.join(SEG_HEAD) + f'」，现在是「{" | ".join(head)}」')
            else:
                seg_rows = rows
            for row in rows if '段' in head else []:   # 表头错了也收段号，免得引用检查连带报错
                p = row['段']
                if not re.fullmatch(r'P\d+', p):
                    r.err(f'plan.md:{sec}', f'段号格式不对：{p or "（空）"}（写 P1、P2）')
                    continue
                if p in segs:
                    r.err(f'plan.md:{sec}', f'段号重复：{p}')
                segs.add(p)
                d = row.get('预计时长', '')
                if '预计时长' in head and not is_placeholder(d) and parse_duration(d) is None:
                    r.err(f'plan.md:{sec}', f'{p} 的预计时长「{d}」解析不出（写「N 秒」或「N–M 秒」）')

    gaps, gap_rows = set(), []
    sec = '缺口'
    if sec in pmap:
        t = find_table(pmap[sec], GAP_HEAD)
        if not t:
            r.err(f'plan.md:{sec}', '找不到缺口表（表头：' + ' | '.join(GAP_HEAD) + '）')
        else:
            gap_rows = t[1]
            for row in gap_rows:
                q = row['编号']
                where = f'plan.md:{sec}'
                if not re.fullmatch(r'Q\d+', q):
                    r.err(where, f'缺口编号格式不对：{q or "（空）"}（写 Q1、Q2）')
                elif q in gaps:
                    r.err(where, f'缺口编号重复：{q}')
                gaps.add(q)
                for col, allowed in (('归谁', OWNERS), ('提出于', RAISED), ('状态', GAP_STATES)):
                    v = row[col]
                    if v not in allowed and not is_placeholder(v):
                        r.err(where, f'{q} 的{col}「{v}」要取 ' + ' / '.join(sorted(allowed)))
                how = row['怎么解决的']
                if row['状态'] == '改内容关闭' and (not how or is_placeholder(how)):
                    r.err(where, f'{q} 是「改内容关闭」，「怎么解决的」要写删了、收窄了或改了什么')

    # 引用都要存在：只查规定写编号的那几格（SPEC 3.1「编号写在哪」），别处的「华为 P40」「2026 年 Q1」是正文
    cells = []   # (位置, 格子内容, 查哪几种编号)
    for row in seg_rows:
        cells += [('段落', row['作用'], 'P'), ('段落', row['核心内容'], 'U'), ('段落', row['素材编排'], 'Q')]
    t = find_table(pmap.get('立意', []), ['项', '内容'])
    for row in (t[1] if t else []):
        if row['项'] == '凭什么信':
            cells.append(('立意', row['内容'], 'U'))
    for row in gap_rows:
        cells += [('缺口', row['段'], 'P'), ('缺口', row['怎么解决的'], 'U')]
    seen = set()
    for sec, cell, kinds in cells:
        found = []
        if 'U' in kinds:
            found += [(x.group(0), data, '引用的 {} 在 research.md 里没有') for x in REF_DATA.finditer(cell)]
            found += [(x.group(0), units, '引用的单元 {} 在 research.md 里没有') for x in REF_UNIT.finditer(cell)]
        if 'P' in kinds:
            found += [(x.group(0), segs, '引用的段 {} 在段落表里没有') for x in REF_SEG.finditer(cell)]
        if 'Q' in kinds:
            found += [(x.group(0), gaps, '引用的缺口 {} 在缺口表里没有') for x in REF_GAP.finditer(cell)]
        for ref, pool, msg in found:
            if ref not in pool and (sec, ref) not in seen:
                seen.add((sec, ref))
                r.err(f'plan.md:{sec}', msg.format(ref))

    # 时长合计和目标比
    target = None
    t = find_table(pmap.get('立意', []), ['项', '内容'])
    if t:
        for row in t[1]:
            if row['项'] == '时长与规格':
                m = DUR_FIND.search(PLACEHOLDER.sub('', row['内容']))
                target = parse_duration(m.group(0)) if m else None
    durs = [parse_duration(row['预计时长']) for row in seg_rows]
    if target and durs and all(durs):
        lo, hi = sum(d[0] for d in durs), sum(d[1] for d in durs)
        if hi < target[0] * 0.85 or lo > target[1] * 1.15:
            fmt = lambda a, b: f'{a:g} 秒' if a == b else f'{a:g}–{b:g} 秒'
            r.note('plan.md:段落', f'各段合计 {fmt(lo, hi)}，和目标时长 {fmt(*target)} 相差超过 15%')

    # 占位（〔待核实〕是状态，不算）
    count = lambda t: sum(1 for x in PLACEHOLDER.finditer(t) if x.group(0) != '〔待核实〕')
    for fname in ('plan.md', 'research.md'):
        title, secs = parse_md(texts[fname])
        for name, lines in [('标题', [title])] + secs:
            n = count('\n'.join([name] + lines))
            if n:
                (r.err if handoff else r.note)(f'{fname}:{name or "开头"}', f'还有 {n} 处〔〕占位没填')

    if not handoff:
        return r

    # ---------- 交接 ----------
    if not any(re.match(r'\s*[-*]\s.*方向(?:[（(][^）)]*[）)])?[：:]', line) for line in pmap.get('确认记录', [])):
        r.err('plan.md:确认记录', '没有「方向」一行：用户还没确认方向，不能交接')
    for row in gap_rows:
        if row['归谁'] == '策划' and row['状态'] == '待补':
            r.err('plan.md:缺口', f'{row["编号"]} 归策划、还待补，补完或改内容关闭后才能交接')
        if row['归谁'] in ('风格后', '分镜后'):
            if not row['缺什么'] or not (REF_SEG.search(row['段']) or row['段'] == '全片'):
                r.err('plan.md:缺口', f'{row["编号"]} 归{row["归谁"]}，要写清缺什么、哪段（段号，或「全片」）')
    for row in seg_rows:
        cell = row['核心内容']
        refs = set(x.group(0) for x in REF_DATA.finditer(cell))
        for u in set(x.group(0) for x in REF_UNIT.finditer(cell)):
            refs |= {d for d in data if d.startswith(u + '-')}
        for d in sorted(refs):
            st = data.get(d, {}).get('状态')
            if st in ('〔待核实〕', '有冲突'):
                r.err('plan.md:段落', f'{row["段"]} 的核心内容用了 {d}，它还是「{st}」')
    if status not in HANDOFF_STATES:
        r.note('plan.md', f'状态是「{status}」，交接时改成「已交接」')
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description='检查 videos/<短名>/ 下的 plan.md、research.md')
    ap.add_argument('folder', help='videos/<短名> 目录')
    ap.add_argument('--handoff', action='store_true', help='按交接条件检查')
    a = ap.parse_args(argv)
    r = check(a.folder, a.handoff)
    for line in r.errors + [f'{n}（提示）' for n in r.notes]:
        print(line)
    print('通过' if not r.errors and not r.notes else f'{len(r.errors)} 个错、{len(r.notes)} 个提示')
    return 1 if r.errors else 0


if __name__ == '__main__':
    sys.exit(main())
