#!/usr/bin/env python3
"""检查 plans/<短名>/ 下的 plan.md、content.md 是否符合模板（格式 ai-content-planner/2），交接前加 --handoff。

用法：python3 -I <本 Skill 目录>/scripts/check.py <plans/短名 目录> [--handoff]

只用标准库。按 Markdown 标题找节、按表头找表，不依赖行号。
输出每个问题一行「文件:节: 问题」，最后一行「通过」或「N 个错、M 个提示」。
有错退出码 1，只有提示退出码 0。
"""
import argparse
import os
import re
import sys

FORMAT = 'ai-content-planner/2'
OLD_FORMATS = {'ai-content-planner/1'}
PLAN_SECTIONS = ['确认记录', '需求', '立意', '框架', '取舍', '缺口']
CONTENT_SECTIONS = ['资料清单', '待核实和有冲突', '检索记录']
NEED_ROWS = ['用途和场景', '给谁看', '输出形式', '篇幅与规格', '必须有', '不要', '已有材料', '品牌与风格']
IDEA_ROWS = ['看完得到什么', '一句话主线', '怎么讲']
FRAME_HEAD = ['段', '作用', '受众收益', '要讲的点', '用到哪些输入', '篇幅']
GAP_HEAD = ['编号', '段', '缺什么', '归谁', '提出于', '状态', '怎么解决的']
SRC_HEAD = ['资料', '位置', '读到哪', '用途', '能不能公开', '用到哪些编号']
DATA_HEAD = ['#', '讲哪一点', '内容', '种类', '来源', '必须写清的', '状态']

STATUSES = {'需求待确认', '框架待确认', '补齐中', '已交接', '回流中'}
OWNERS = {'策划', '下游'}
RAISED = {'第 1 步', '第 2 步', '第 3 步', '下游'}
GAP_STATES = {'待补', '已补', '改内容关闭'}
DATA_STATES = {'已核实', '〔待核实〕', '有冲突', '已过期', '设定'}
USES = {'内容依据', '素材', '参考'}
HANDOFF_STATES = {'已交接', '回流中'}
NOT_USED = '不用'
TBD = '待你定'
FIRST_STEP = '需求待确认'
CONTENT_STUB = ('# 内容表\n\n## 资料清单\n\n| 资料 | 位置 | 读到哪 | 用途 | 能不能公开 | 用到哪些编号 |\n|---|---|---|---|---|---|\n'
                '\n## 待核实和有冲突\n\n## 检索记录\n')   # 第 1 步还没建 content.md 时代替它，内容表的检查都跳过

PLACEHOLDER = re.compile(r'〔[^〕]*〕')
REF_DATA = re.compile(r'(?<![A-Za-z0-9_])P(\d+)-(\d+)(?![\d])')
REF_SEG = re.compile(r'(?<![A-Za-z0-9_])P(\d+)(?![\d-])')
REF_GAP = re.compile(r'(?<![A-Za-z0-9_])Q(\d+)(?![\d])')
POINT = re.compile(r'([a-z])\.\s*(.*)', re.S)
SHARED = re.compile(r'[（(]([^（）()]*?)\s*也用[）)]')
SHARED_REF = re.compile(r'P(\d+)\s*([a-z](?:\s*[、,，]\s*[a-z])*)?')
CONFIRM_LINE = re.compile(r'\s*[-*]\s.*?(需求|框架|局部)(?:[（(][^）)]*[）)])?[：:]')
NUM = r'\d+(?:\.\d+)?'
UNITS = {'秒': ('时间', 1), 's': ('时间', 1), '分钟': ('时间', 60), '分': ('时间', 60), 'min': ('时间', 60),
         '页': ('页', 1), '千字': ('字', 1000), '万字': ('字', 10000), '字': ('字', 1)}
UNIT_RE = '千字|万字|分钟|min|秒|分|页|字|s'
EXT_FIND = re.compile(rf'{NUM}\s*分钟?\s*{NUM}\s*秒|{NUM}\s*(?:[–\-~—至到]\s*{NUM}\s*)?(?:{UNIT_RE})(?![A-Za-z])')
SHOW = {'时间': '秒', '页': '页', '字': '字'}


def is_placeholder(cell):
    """整格只是〔〕占位（〔待核实〕是状态，不算）"""
    rest = PLACEHOLDER.sub(lambda m: '' if m.group(0) != '〔待核实〕' else m.group(0), cell).strip()
    return cell.strip() != '' and rest == ''


def parse_extent(text):
    """篇幅 → (类, 下限, 上限)，类是 时间（折成秒）/ 页 / 字；「不限」→ ('不限', 0, 0)；解析不了返回 None。
    认：'45 秒'、'40–50 秒'、'1 分 30 秒'、'1 分钟 30 秒'、'2 分钟'、'3 页'、'1500 字'、'3 千字'、'约 45 秒'、'45 秒左右'"""
    s = re.sub(r'\s+', '', text)
    s = re.sub(r'^(约|大约|~)', '', s)
    s = re.sub(r'(左右|上下)$', '', s)
    if s == '不限':
        return '不限', 0, 0
    m = re.fullmatch(rf'({NUM})分钟?({NUM})秒', s)
    if m:
        v = float(m.group(1)) * 60 + float(m.group(2))
        return '时间', v, v
    m = re.fullmatch(rf'({NUM})(?:[–\-~—至到]({NUM}))?({UNIT_RE})', s)
    if m:
        kind, k = UNITS[m.group(3)]
        lo = float(m.group(1)) * k
        hi = float(m.group(2)) * k if m.group(2) else lo
        return (kind, lo, hi) if lo <= hi else None
    return None


def parse_points(cell):
    """要讲的点「a. ……<br>b. ……」→ [(字母, 这一点)]；有一点不是「字母. 」开头就返回 None"""
    if is_placeholder(cell):
        return []
    out = []
    for part in re.split(r'<br\s*/?>', cell):
        part = part.strip()
        if not part:
            continue
        m = POINT.fullmatch(part)
        if not m:
            return None
        out.append((m.group(1), m.group(2).strip()))
    return out


def parse_which(cell):
    """讲哪一点「a、b（P3 也用）」→ (字母列表, [(段号, 字母列表)])；「不用」→ ([], [])，字母列表为 None 表示「不用」"""
    shared = []
    for m in SHARED.finditer(cell):
        for r in SHARED_REF.finditer(m.group(1)):
            shared.append((f'P{r.group(1)}', re.findall(r'[a-z]', r.group(2) or '')))
    rest = SHARED.sub('', cell).strip()
    if rest == NOT_USED:
        return None, shared
    return [x.strip() for x in re.split(r'[、,，]', rest) if x.strip()], shared


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


def check_rows(r, pmap, sec, names):
    """需求、立意表：项要正好是 names → 行列表"""
    t = find_table(pmap.get(sec, []), ['项', '内容'])
    if sec in pmap and not t:
        r.err(f'plan.md:{sec}', f'找不到{sec}表（表头：项 | 内容 | 来源）')
        return []
    if t and [row['项'] for row in t[1]] != names:
        r.err(f'plan.md:{sec}', f'{sec}要正好是这{len(names)}项：' + '、'.join(names) + '；现在是 ' + '、'.join(row['项'] for row in t[1]))
    return t[1] if t else []


def check(folder, handoff=False):
    r = Report()
    texts, stub = {}, False
    for name in ('plan.md', 'content.md'):
        p = os.path.join(folder, name)
        if os.path.isfile(p):
            with open(p, encoding='utf-8') as f:
                texts[name] = f.read()
    if 'plan.md' not in texts:
        r.err('plan.md', '文件不存在')
    elif 'content.md' not in texts:
        m = re.search(r'^状态[：:]\s*([^（(\n]*)', texts['plan.md'], re.M)
        if m and m.group(1).strip().rstrip('。.') == FIRST_STEP and not handoff:
            r.note('content.md', f'还没建：「{FIRST_STEP}」时可以先不建，第 2 步前复制模板、先填资料清单')
            texts['content.md'] = CONTENT_STUB
            stub = True
        else:
            hint = '（格式 1 的 research.md 改名 content.md，按 CHANGELOG 转）' if os.path.isfile(os.path.join(folder, 'research.md')) else ''
            r.err('content.md', '文件不存在' + hint)
    if len(texts) < 2:
        return r

    # ---------- plan.md ----------
    ptitle, psecs = parse_md(texts['plan.md'])
    pmap = {}
    for name, lines in psecs:
        pmap.setdefault(name, lines)
    if not ptitle.startswith('内容策划'):
        r.err('plan.md', '第一行标题要是「# 内容策划：题目」')
    m = re.search(r'^格式[：:]\s*(\S+)', texts['plan.md'], re.M)
    if not m:
        r.err('plan.md', f'找不到格式行（标题下第一行写「格式：{FORMAT}」）')
    elif m.group(1) != FORMAT:
        hint = '；这是旧格式，按本 Skill 的 CHANGELOG.md 转成格式 2' if m.group(1) in OLD_FORMATS else ''
        r.err('plan.md', f'格式是「{m.group(1)}」，本脚本只认 {FORMAT}{hint}')
        return r
    for s in PLAN_SECTIONS:
        if s not in pmap:
            r.err(f'plan.md:{s}', '缺这一节')

    m = re.search(r'^状态[：:]\s*([^（(\n]*)', texts['plan.md'], re.M)
    status = m.group(1).strip().rstrip('。.') if m else ''
    if not m:
        r.err('plan.md', '找不到状态行（「状态：……（日期）」）')
    elif status not in STATUSES and not is_placeholder(status):
        r.err('plan.md', f'状态「{status}」要取 ' + ' / '.join(sorted(STATUSES)))
    confirms = []
    for line in pmap.get('确认记录', []):
        if not re.match(r'\s*[-*]\s', line):
            continue
        cm = CONFIRM_LINE.match(line)
        if cm:
            confirms.append(cm.group(1))
        else:
            r.err('plan.md:确认记录', f'这一行认不出是哪种确认（写「日期 需求：」「框架：」或「局部：」）：{line.strip()[:30]}')

    need_rows = check_rows(r, pmap, '需求', NEED_ROWS)
    check_rows(r, pmap, '立意', IDEA_ROWS)

    segs, seg_rows, points = set(), [], {}   # points: 'P1' → {'a': 这一点}
    sec = '框架'
    if sec in pmap:
        if not any(re.match(r'\s*内容流程[：:]', line) for line in pmap[sec]):
            r.err(f'plan.md:{sec}', '缺「内容流程：」一行（P1 → P2 → P3 的逻辑线）')
        tbs = tables(pmap[sec])
        if not tbs:
            r.err(f'plan.md:{sec}', '找不到段落表')
        else:
            head, rows = tbs[0]
            if head != FRAME_HEAD:
                r.err(f'plan.md:{sec}', '段落表表头要正好是「' + ' | '.join(FRAME_HEAD) + f'」，现在是「{" | ".join(head)}」')
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
                d = row.get('篇幅', '')
                if '篇幅' in head and not is_placeholder(d) and parse_extent(d) is None:
                    r.err(f'plan.md:{sec}', f'{p} 的篇幅「{d}」解析不出（写「N 秒」「N 页」「N 字」、区间，或「不限」）')
                if '要讲的点' in head:
                    pts = parse_points(row['要讲的点'])
                    letters = [x[0] for x in pts or []]
                    if pts is None or not row['要讲的点'].strip():
                        r.err(f'plan.md:{sec}', f'{p} 的要讲的点要按「a. 一点一句<br>b. ……」写')
                    elif letters != [chr(ord('a') + i) for i in range(len(letters))]:
                        r.err(f'plan.md:{sec}', f'{p} 的要讲的点要从 a 起按顺序编：现在是 ' + '、'.join(letters))
                    points[p] = dict(pts or [])

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

    # ---------- content.md ----------
    ctitle, csecs = parse_md(texts['content.md'])
    cmap = {}
    for name, lines in csecs:
        cmap.setdefault(name, lines)
    for s in CONTENT_SECTIONS:
        if s not in cmap:
            r.err(f'content.md:{s}', '缺这一节')

    data = {}            # 'P1-1' → 行
    covered = {}         # ('P1', 'a') → [编号]
    seen_secs = set()
    for name, lines in csecs:
        m = re.match(r'P(\S*)', name)
        if not m or name in CONTENT_SECTIONS:
            continue
        where = f'content.md:{name}'
        pm = re.fullmatch(r'P\d+', m.group(0))
        if not pm:
            r.err(where, f'节名的段号格式不对：{m.group(0)}（写「## P1 段的作用」）')
            continue
        pid = pm.group(0)
        if pid in seen_secs:
            r.err(where, f'段 {pid} 有两节')
        seen_secs.add(pid)
        if segs and pid not in segs:
            r.err(where, f'段 {pid} 在 plan.md 的框架里没有')
        t = find_table(lines, DATA_HEAD)
        if not t:
            r.err(where, '找不到信息表（表头：' + ' | '.join(DATA_HEAD) + '）')
            continue
        for row in t[1]:
            did = row['#']
            if not re.fullmatch(rf'{pid}-\d+', did):
                r.err(where, f'编号格式不对：{did or "（空）"}（这一节写 {pid}-1、{pid}-2）')
                continue
            if did in data:
                r.err(where, f'编号重复：{did}')
            data[did] = row
            if is_placeholder(row['内容']):
                continue
            st = row['状态']
            if st not in DATA_STATES:
                r.err(where, f'{did} 的状态「{st}」不在 ' + ' / '.join(sorted(DATA_STATES)) + ' 里')
            which = row['讲哪一点']
            letters, shared = parse_which(which)
            if letters is not None and not letters:
                r.err(where, f'{did} 的「讲哪一点」空着（写这段要讲的点的字母，记着不讲的写「{NOT_USED}」）')
            for x in letters or []:
                if pid in points and x not in points[pid]:
                    r.err(where, f'{did} 讲的「{x}」不在 {pid} 的要讲的点里')
                covered.setdefault((pid, x), []).append(did)
            for sp, sl in shared:
                if sp == pid or (segs and sp not in segs):
                    r.err(where, f'{did} 写了「{sp} 也用」，{sp} ' + ('就是本段' if sp == pid else '在框架里没有'))
                    continue
                for x in sl:
                    if sp in points and x not in points[sp]:
                        r.err(where, f'{did} 写了「{sp} {x} 也用」，「{x}」不在 {sp} 的要讲的点里')
                    covered.setdefault((sp, x), []).append(did)

    sec = '资料清单'
    if sec in cmap:
        t = find_table(cmap[sec], SRC_HEAD)
        if not t:
            r.err(f'content.md:{sec}', '找不到资料表（表头：' + ' | '.join(SRC_HEAD) + '）')
        else:
            for row in t[1]:
                use = row['用途']
                if is_placeholder(use):
                    continue
                bad = [u for u in re.split(r'、', use) if u.strip() not in USES]
                if not use or bad:
                    r.err(f'content.md:{sec}', f'「{row["资料"]}」的用途「{use}」要取 ' + ' / '.join(sorted(USES)) + '，多个用「、」隔开；补充说明写进「读到哪」或「能不能公开」')

    # 引用都要存在：只查规定写编号的那几格，别处的「华为 P40」「2026 年 Q1」是正文
    cells = []   # (位置, 格子内容, 查哪几种编号)
    for row in seg_rows:
        cells.append(('框架', row['作用'], 'P'))
    for row in gap_rows:
        cells += [('缺口', row['段'], 'P'), ('缺口', row['怎么解决的'], 'D')]
    reported = set()
    for sec, cell, kinds in cells:
        found = []
        if 'D' in kinds and not stub:
            found += [(x.group(0), data, '引用的 {} 在 content.md 里没有') for x in REF_DATA.finditer(cell)]
        if 'P' in kinds:
            found += [(x.group(0), segs, '引用的段 {} 在框架里没有') for x in REF_SEG.finditer(cell)]
        for ref, pool, msg in found:
            if ref not in pool and (sec, ref) not in reported:
                reported.add((sec, ref))
                r.err(f'plan.md:{sec}', msg.format(ref))

    # 篇幅合计和目标比：单位一致才比
    target = None
    for row in need_rows:
        if row['项'] == '篇幅与规格':
            m = EXT_FIND.search(PLACEHOLDER.sub('', row['内容']))
            target = parse_extent(m.group(0)) if m else None
    exts = [parse_extent(row['篇幅']) for row in seg_rows]
    if exts and all(exts):
        kinds = {e[0] for e in exts} - {'不限'}
        if len(kinds) > 1:
            r.note('plan.md:框架', '各段篇幅单位不一致：' + ' / '.join(sorted(kinds)))
        elif target and kinds == {target[0]}:
            lo = sum(e[1] for e in exts if e[0] != '不限')
            hi = sum(e[2] for e in exts if e[0] != '不限')
            if hi < target[1] * 0.85 or lo > target[2] * 1.15:
                u = SHOW[target[0]]
                fmt = lambda a, b: f'{a:g} {u}' if a == b else f'{a:g}–{b:g} {u}'
                r.note('plan.md:框架', f'各段合计 {fmt(lo, hi)}，和目标篇幅 {fmt(target[1], target[2])} 相差超过 15%')

    # 占位（〔待核实〕是状态，不算）
    count = lambda t: sum(1 for x in PLACEHOLDER.finditer(t) if x.group(0) != '〔待核实〕')
    for fname in ('plan.md', 'content.md'):
        title, secs = parse_md(texts[fname])
        for name, lines in [('标题', [title])] + secs:
            n = count('\n'.join([name] + lines))
            if n:
                (r.err if handoff else r.note)(f'{fname}:{name or "开头"}', f'还有 {n} 处〔〕占位没填')

    if not handoff:
        return r

    # ---------- 交接（SKILL.md「交接」1–4、6 条） ----------
    for kind in ('需求', '框架'):
        if kind not in confirms:
            r.err('plan.md:确认记录', f'没有「{kind}」一行：{kind}还没确认（或没写「自动，未问用户」），不能交接')
    for row in need_rows:
        if TBD in row['内容'] or TBD in row.get('来源', ''):
            r.err('plan.md:需求', f'「{row["项"]}」还是「{TBD}」，用户定了才能交接')
    for row in gap_rows:
        if row['归谁'] == '策划' and row['状态'] == '待补':
            r.err('plan.md:缺口', f'{row["编号"]} 归策划、还待补，补完或改内容关闭后才能交接')
        if row['归谁'] == '下游':
            if not row['缺什么'] or not (REF_SEG.search(row['段']) or row['段'] == '全部'):
                r.err('plan.md:缺口', f'{row["编号"]} 归下游，要写清缺什么、哪段（段号，或「全部」）')
    for row in seg_rows:
        p = row['段']
        for x in points.get(p, {}):
            ids = covered.get((p, x), [])
            if not ids:
                r.err('content.md', f'{p} 的「{x}」在 content.md 里没有对应的信息')
            for d in ids:
                st = data[d]['状态']
                if st in ('〔待核实〕', '有冲突'):
                    r.err(f'content.md:{p}', f'{p} 的「{x}」用了 {d}，它还是「{st}」')
    if status not in HANDOFF_STATES:
        r.note('plan.md', f'状态是「{status}」，交接时改成「已交接」')
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description='检查 plans/<短名>/ 下的 plan.md、content.md')
    ap.add_argument('folder', help='plans/<短名> 目录')
    ap.add_argument('--handoff', action='store_true', help='按交接条件检查')
    a = ap.parse_args(argv)
    r = check(a.folder, a.handoff)
    for line in r.errors + [f'{n}（提示）' for n in r.notes]:
        print(line)
    print('通过' if not r.errors and not r.notes else f'{len(r.errors)} 个错、{len(r.notes)} 个提示')
    return 1 if r.errors else 0


if __name__ == '__main__':
    sys.exit(main())
