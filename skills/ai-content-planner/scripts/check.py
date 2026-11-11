#!/usr/bin/env python3
"""检查 plans/<短名>/ 下的 plan.md、content.md 是否符合模板（格式 ai-content-planner/3），交接前加 --handoff。

用法：python3 -I <本 Skill 目录>/scripts/check.py <plans/短名 目录> [--handoff]

只用标准库。按 Markdown 标题找节、按表头找表，不依赖行号。
输出每个问题一行「文件:节: 问题」，最后一行「通过」或「N 个错、M 个提示」。
有错退出码 1，只有提示退出码 0。
"""
import argparse
import os
import re
import sys

FORMAT = 'ai-content-planner/3'
OLD_FORMATS = {'ai-content-planner/1', 'ai-content-planner/2'}
PLAN_SECTIONS = ['确认记录', '需求', '效果', '形式', '立意', '框架', '效果自查', '说法', '衍生', '取舍', '缺口']
CONTENT_SECTIONS = ['资料清单', '受众', '素材', '约束', '待核实和有冲突', '检索记录']
NEED_ROWS = ['用途和场景', '必须有', '不要', '已有材料', '品牌与风格']
EFFECT_ROWS = ['接触时刻', '起点', '阻力', '终点', '衡量', '杠杆']
FORM_ROWS = ['输出形式和规格', '篇幅和注意力', '结构', '声音', '证明方式', '制作条件', '衍生']
FORM_NEED_BASIS = ['篇幅和注意力', '结构', '声音', '证明方式']   # 「由哪条效果推出」不能空
SELF_ROWS = ['阻力', '终点', '注意力预算', '换题测试', '衍生']
PLAY_HEAD = ['打法', '抓哪条阻力', '用哪个杠杆', '开头', '代价', '选']
FRAME_HEAD = ['段', '作用', '受众：从 → 到', '要讲的点', '怎么证明', '用到哪些输入', '篇幅']
SAY_HEAD = ['点', '要的效果', '参考说法', '不能丢的']
SPIN_HEAD = ['条', '用哪些点', '第一句', '放在哪']
GAP_HEAD = ['编号', '段', '缺什么', '归谁', '提出于', '状态', '怎么解决的']
SRC_HEAD = ['资料', '位置', '读到哪', '用途', '能不能公开', '用到哪些编号']
VOICE_HEAD = ['#', '内容', '种类', '来源', '对应哪条阻力', '状态']
ASSET_HEAD = ['#', '文件', '内容', '字、标志、水印、人脸', '能怎么用', '能不能送生成', '用到哪段']
RULE_HEAD = ['#', '必须守的样子', '依据', '状态']
DATA_HEAD = ['#', '讲哪一点', '内容', '种类', '来源', '必须写清的', '状态']

STATUSES = {'效果待确认', '框架待确认', '补齐中', '已交接', '回流中'}
OWNERS = {'策划', '下游'}
RAISED = {'第 1 步', '第 2 步', '第 3 步', '下游'}
GAP_STATES = {'待补', '已补', '改内容关闭'}
DATA_STATES = {'已核实', '〔待核实〕', '有冲突', '已过期', '设定'}
RULE_STATES = {'已核实', '〔待核实〕', '设定'}
USES = {'内容依据', '素材', '参考'}
ASSET_USES = {'原样', '裁后用', '重画', '只作参考'}
ASSET_GEN = {'能', '不能', '〔待核实〕'}
HANDOFF_STATES = {'已交接', '回流中'}
NOT_USED = '不用'
NONE = '无'
TBD = '待你定'
FIRST_STEP = '效果待确认'
CONTENT_STUB = ('# 内容表\n\n## 资料清单\n\n| 资料 | 位置 | 读到哪 | 用途 | 能不能公开 | 用到哪些编号 |\n|---|---|---|---|---|---|\n'
                '\n## 受众\n\n## 素材\n\n## 约束\n\n## 待核实和有冲突\n\n## 检索记录\n')   # 第 1 步还没建 content.md 时代替它，内容表的检查都跳过
INFO_TO = ('知道', '了解', '感受到', '认识到')            # 「到」这样开头是信息收益，提示
EMPTY_WORDS = ('引发共鸣', '提升好感', '增强信任', '提升认知', '加深印象')
CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩'

PLACEHOLDER = re.compile(r'〔[^〕]*〕')
REF_DATA = re.compile(r'(?<![A-Za-z0-9_])P(\d+)-(\d+)(?![\d])')
REF_SEG = re.compile(r'(?<![A-Za-z0-9_])P(\d+)(?![\d-])')
REF_GAP = re.compile(r'(?<![A-Za-z0-9_])Q(\d+)(?![\d])')
REF_V = re.compile(r'(?<![A-Za-z0-9_])V(\d+)(?![\d])')
REF_M = re.compile(r'(?<![A-Za-z0-9_])M(\d+)(?![\d])')
REF_K = re.compile(r'(?<![A-Za-z0-9_])K(\d+)(?![\d])')
SEG_POINTS = re.compile(r'(?<![A-Za-z0-9_])P(\d+)(?![\d-])\s*([a-z](?:\s*[、,，]\s*[a-z])*)?')
POINT = re.compile(r'([a-z])\.\s*(.*)', re.S)
SHARED = re.compile(r'[（(]([^（）()]*?)\s*也用[）)]')
SHARED_REF = re.compile(r'P(\d+)\s*([a-z](?:\s*[、,，]\s*[a-z])*)?')
CONFIRM_LINE = re.compile(r'\s*[-*]\s.*?(效果|框架|局部)(?:[（(][^）)]*[）)])?[：:]')
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


def check_rows(r, pmap, sec, names, head):
    """需求、效果、形式表：表头含 head，项要正好是 names → 行列表"""
    t = find_table(pmap.get(sec, []), head)
    if sec in pmap and not t:
        r.err(f'plan.md:{sec}', f'找不到{sec}表（表头：' + ' | '.join(head) + '）')
        return []
    if t and [row['项'] for row in t[1]] != names:
        r.err(f'plan.md:{sec}', f'{sec}要正好是这{len(names)}项：' + '、'.join(names) + '；现在是 ' + '、'.join(row['项'] for row in t[1]))
    return t[1] if t else []


def circled(cell):
    return [c for c in cell if c in CIRCLED]


def seg_points(cell):
    """「P1 a、b；P3 c」→ [(段号, [字母])]"""
    return [(f'P{m.group(1)}', re.findall(r'[a-z]', m.group(2) or '')) for m in SEG_POINTS.finditer(cell)]


def value_of(cell):
    """「裁后用：裁掉顶部」→「裁后用」"""
    return re.split(r'[：:]', cell, maxsplit=1)[0].strip()


def id_table(r, where, lines, head, prefix, what):
    """受众、素材、约束这类带编号的表 → {编号: 行}；表头错、编号格式不对、重复都报"""
    out = {}
    if lines is None:   # 第 1 步还没建 content.md
        return out
    t = find_table(lines, head)
    if not t:
        if tables(lines):
            r.err(where, f'{what}表的表头要是「' + ' | '.join(head) + '」')
        else:
            r.err(where, f'找不到{what}表（表头：' + ' | '.join(head) + '，没有内容也留表头）')
        return out
    for row in t[1] if t else []:
        i = row['#']
        if not re.fullmatch(rf'{prefix}\d+', i):
            r.err(where, f'编号格式不对：{i or "（空）"}（写 {prefix}1、{prefix}2）')
            continue
        if i in out:
            r.err(where, f'编号重复：{i}')
        out[i] = row
    return out


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

    # ---------- plan.md：格式、节、状态、确认记录 ----------
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
        hint = f'；这是旧格式，按本 Skill 的 CHANGELOG.md 转成格式 {FORMAT[-1]}' if m.group(1) in OLD_FORMATS else ''
        r.err('plan.md', f'格式是「{m.group(1)}」，本脚本只认 {FORMAT}{hint}')
        return r
    for s_ in PLAN_SECTIONS:
        if s_ not in pmap:
            r.err(f'plan.md:{s_}', '缺这一节')

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
            r.err('plan.md:确认记录', f'这一行认不出是哪种确认（写「日期 效果：」「框架：」或「局部：」）：{line.strip()[:30]}')

    # ---------- 需求、效果、形式 ----------
    need_rows = check_rows(r, pmap, '需求', NEED_ROWS, ['项', '内容', '来源'])
    effect_rows = check_rows(r, pmap, '效果', EFFECT_ROWS, ['项', '内容', '依据', '来源'])
    form_rows = check_rows(r, pmap, '形式', FORM_ROWS, ['项', '内容', '由哪条效果推出', '来源'])
    effect = {row['项']: row for row in effect_rows}
    form = {row['项']: row for row in form_rows}
    blocks = []   # 阻力编号
    if '阻力' in effect and not is_placeholder(effect['阻力']['内容']):
        blocks = circled(effect['阻力']['内容'])
        if not blocks:
            r.err('plan.md:效果', '阻力要按强弱编号：① ……<br>② ……')
        elif len(set(blocks)) != len(blocks):
            r.err('plan.md:效果', '阻力的编号重复：' + ''.join(blocks))
    for row in effect_rows:
        hit = [w for w in EMPTY_WORDS if w in row['内容']]
        if hit:
            r.note('plan.md:效果', f'「{row["项"]}」写了「{hit[0]}」：效果要写成具体的念头或能看见的动作')
    for name in FORM_NEED_BASIS:
        if name in form and not form[name]['由哪条效果推出'].strip() and not is_placeholder(form[name]['内容']):
            r.err('plan.md:形式', f'「{name}」的「由哪条效果推出」空着：形式要从效果推出来')
    spin_form = form.get('衍生', {}).get('内容', '')
    spin_none = spin_form.strip() == NONE
    spin_known = bool(spin_form.strip()) and not is_placeholder(spin_form)

    def bad_blocks(cell, where, what):
        for c in circled(cell):
            if blocks and c not in blocks:
                r.err(where, f'{what}写了「{c}」，效果的阻力里没有这一条')

    # ---------- 立意：主线、打法 ----------
    sec = '立意'
    if sec in pmap:
        if not any(re.match(r'\s*一句话主线[：:]', line) for line in pmap[sec]):
            r.err(f'plan.md:{sec}', '缺「一句话主线：」一行')
        t = find_table(pmap[sec], ['打法'])
        if not t:
            r.err(f'plan.md:{sec}', '找不到打法表（表头：' + ' | '.join(PLAY_HEAD) + '）')
        elif t[0] != PLAY_HEAD:
            r.err(f'plan.md:{sec}', '打法表表头要正好是「' + ' | '.join(PLAY_HEAD) + f'」，现在是「{" | ".join(t[0])}」')
        else:
            rows = t[1]
            if not 1 <= len(rows) <= 3:
                r.err(f'plan.md:{sec}', f'打法要有 1–3 个，现在 {len(rows)} 个')
            picks = [row for row in rows if row['选'] == '选']
            if not all(is_placeholder(row['选']) for row in rows):
                if len(picks) != 1:
                    r.err(f'plan.md:{sec}', f'打法表要正好一行「选」写「选」，现在 {len(picks)} 行')
                bad = [row['选'] for row in rows if row['选'] not in ('选', '')]
                if bad:
                    r.err(f'plan.md:{sec}', f'「选」一列只写「选」或空着：{bad[0]}')
            if len(rows) == 1:
                r.note(f'plan.md:{sec}', '只有一个打法：用户给了结构时可以，否则给 2–3 个让用户选')
            for row in rows:
                bad_blocks(row['抓哪条阻力'], f'plan.md:{sec}', f'打法「{row["打法"]}」')

    # ---------- 框架 ----------
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
            for row in seg_rows:
                p, aud = row['段'], row['受众：从 → 到']
                if not is_placeholder(aud):
                    if '→' not in aud:
                        r.err(f'plan.md:{sec}', f'{p} 的受众要写「原来的念头 → 看完这段的念头或动作」，现在没有「→」')
                    else:
                        to = aud.rsplit('→', 1)[1].strip().lstrip('「“"\'')
                        if to.startswith(INFO_TO):
                            r.note(f'plan.md:{sec}', f'{p} 的受众「到」以「{to[:3]}」开头：写成具体的念头或动作，别停在知道了什么')
                    hit = [w for w in EMPTY_WORDS if w in aud]
                    if hit:
                        r.note(f'plan.md:{sec}', f'{p} 的受众写了「{hit[0]}」：写成具体的念头或动作')
                if not row['怎么证明'].strip():
                    r.err(f'plan.md:{sec}', f'{p} 的「怎么证明」空着：写用什么让人信或有感受')

    def bad_points(where, cell, what):
        """「P1 a、b」里的段和字母要在框架里"""
        found = seg_points(cell)
        if not found:
            r.err(where, f'{what}「{cell}」要写成「P1 a」「P1 a、b」')
        for sp, sl in found:
            if segs and sp not in segs:
                r.err(where, f'{what}「{cell}」的段 {sp} 在框架里没有')
            for x in sl:
                if sp in points and x not in points[sp]:
                    r.err(where, f'{what}「{cell}」的「{x}」不在 {sp} 的要讲的点里')
        return found

    # ---------- 效果自查 ----------
    self_rows = []
    sec = '效果自查'
    if sec in pmap:
        t = find_table(pmap[sec], ['查什么', '结果'])
        if not t:
            r.err(f'plan.md:{sec}', '找不到效果自查表（表头：查什么 | 结果）')
        else:
            self_rows = t[1]
            if [row['查什么'] for row in self_rows] != SELF_ROWS:
                r.err(f'plan.md:{sec}', '效果自查要正好是这5项：' + '、'.join(SELF_ROWS) + '；现在是 ' + '、'.join(row['查什么'] for row in self_rows))
            got = {row['查什么']: row['结果'] for row in self_rows}
            res = got.get('阻力', '')
            if res and not is_placeholder(res):
                miss = [c for c in blocks if c not in res]
                if miss:
                    r.err(f'plan.md:{sec}', '阻力' + ''.join(miss) + ' 没写由哪段回应')
                bad_blocks(res, f'plan.md:{sec}', '阻力一行')
            end_ = got.get('终点', '')
            if end_ and not is_placeholder(end_) and not REF_SEG.search(end_):
                r.err(f'plan.md:{sec}', '终点一行要写落在哪段（段号）')

    # ---------- 说法 ----------
    say_rows = []
    sec = '说法'
    if sec in pmap:
        t = find_table(pmap[sec], ['点'])
        if not t:
            r.err(f'plan.md:{sec}', '找不到说法表（表头：' + ' | '.join(SAY_HEAD) + '）')
        elif t[0] != SAY_HEAD:
            r.err(f'plan.md:{sec}', '说法表表头要正好是「' + ' | '.join(SAY_HEAD) + f'」，现在是「{" | ".join(t[0])}」')
        else:
            say_rows = t[1]
            for row in say_rows:
                if not is_placeholder(row['点']):
                    bad_points(f'plan.md:{sec}', row['点'], '点')

    # ---------- 衍生 ----------
    spin_rows = []
    sec = '衍生'
    if sec in pmap:
        t = find_table(pmap[sec], ['条'])
        body = [x.strip() for x in pmap[sec] if x.strip() and not x.strip().startswith('>')]
        if t:
            if t[0] != SPIN_HEAD:
                r.err(f'plan.md:{sec}', '衍生表表头要正好是「' + ' | '.join(SPIN_HEAD) + f'」，现在是「{" | ".join(t[0])}」')
            else:
                spin_rows = t[1]
                seen = set()
                for row in spin_rows:
                    i = row['条']
                    if not re.fullmatch(r'D\d+', i):
                        r.err(f'plan.md:{sec}', f'编号格式不对：{i or "（空）"}（写 D1、D2）')
                    elif i in seen:
                        r.err(f'plan.md:{sec}', f'编号重复：{i}')
                    seen.add(i)
                    if not is_placeholder(row['用哪些点']):
                        bad_points(f'plan.md:{sec}', row['用哪些点'], f'{i} 的用哪些点')
            if spin_none and spin_rows:
                r.err(f'plan.md:{sec}', '形式的衍生写了「无」，这一节就只写「无」')
        elif body != [NONE]:
            r.err(f'plan.md:{sec}', f'没有衍生就只写一行「{NONE}」；有就用表（表头：' + ' | '.join(SPIN_HEAD) + '）')
        elif spin_known and not spin_none:
            r.err(f'plan.md:{sec}', f'形式的衍生是「{spin_form[:20]}」，这一节不能写「无」')

    # ---------- 缺口 ----------
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
    for s_ in CONTENT_SECTIONS:
        if s_ not in cmap:
            r.err(f'content.md:{s_}', '缺这一节')

    voices = id_table(r, 'content.md:受众', None if stub else cmap.get('受众'), VOICE_HEAD, 'V', '受众') if '受众' in cmap else {}
    assets = id_table(r, 'content.md:素材', None if stub else cmap.get('素材'), ASSET_HEAD, 'M', '素材') if '素材' in cmap else {}
    rules = id_table(r, 'content.md:约束', None if stub else cmap.get('约束'), RULE_HEAD, 'K', '约束') if '约束' in cmap else {}
    for i, row in voices.items():
        if not is_placeholder(row['内容']):
            if row['状态'] not in DATA_STATES:
                r.err('content.md:受众', f'{i} 的状态「{row["状态"]}」不在 ' + ' / '.join(sorted(DATA_STATES)) + ' 里')
            if row['对应哪条阻力'] != NONE and not is_placeholder(row['对应哪条阻力']):
                if not circled(row['对应哪条阻力']):
                    r.err('content.md:受众', f'{i} 的「对应哪条阻力」写阻力的编号（①），不对应写「{NONE}」')
                bad_blocks(row['对应哪条阻力'], 'content.md:受众', f'{i} 的对应哪条阻力')
    for i, row in assets.items():
        for col, allowed in (('能怎么用', ASSET_USES), ('能不能送生成', ASSET_GEN)):
            v = row[col]
            if not is_placeholder(v) or v.startswith('〔待核实〕'):
                if value_of(v) not in allowed:
                    r.err('content.md:素材', f'{i} 的{col}「{v}」要取 ' + ' / '.join(sorted(allowed)) + '（后面可以加「：说明」）')
    for i, row in rules.items():
        if not is_placeholder(row['必须守的样子']) and row['状态'] not in RULE_STATES:
            r.err('content.md:约束', f'{i} 的状态「{row["状态"]}」要取 ' + ' / '.join(sorted(RULE_STATES)))

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
    pools = {'P': (REF_SEG, segs, '引用的段 {} 在框架里没有'), 'D': (REF_DATA, data, '引用的 {} 在 content.md 里没有'),
             'M': (REF_M, assets, '引用的 {} 在 content.md 的素材表里没有'), 'K': (REF_K, rules, '引用的 {} 在 content.md 的约束表里没有'),
             'Q': (REF_GAP, gaps, '引用的 {} 在缺口表里没有')}
    cells = []   # (位置, 格子内容, 查哪几种编号)
    for row in seg_rows:
        cells += [('plan.md:框架', row['作用'], 'P'), ('plan.md:框架', row['怎么证明'], 'MK')]
    for row in self_rows:
        cells.append(('plan.md:效果自查', row['结果'], 'P'))
    for row in say_rows:
        cells.append(('plan.md:说法', row['不能丢的'], 'PDMKQ'))
    for row in gap_rows:
        cells += [('plan.md:缺口', row['段'], 'P'), ('plan.md:缺口', row['怎么解决的'], 'D')]
    for row in assets.values():
        cells.append(('content.md:素材', row['用到哪段'], 'P'))
    for row in rules.values():
        cells.append(('content.md:约束', row['依据'], 'DM'))
    for row in data.values():
        cells.append(('content.md', row['来源'], 'M'))
    reported = set()
    for where, cell, kinds in cells:
        if is_placeholder(cell):
            continue
        for k in kinds:
            if stub and k in 'DMK':
                continue
            rx, pool, msg = pools[k]
            for x in rx.finditer(cell):
                ref = x.group(0)
                if ref not in pool and (where, ref) not in reported:
                    reported.add((where, ref))
                    r.err(where, msg.format(ref))

    # 篇幅合计和目标比：单位一致才比
    target = None
    if '篇幅和注意力' in form:
        m = EXT_FIND.search(PLACEHOLDER.sub('', form['篇幅和注意力']['内容']))
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
    for fname in ('plan.md',) + (() if stub else ('content.md',)):
        title, secs = parse_md(texts[fname])
        for name, lines in [('标题', [title])] + secs:
            n = count('\n'.join([name] + lines))
            if n:
                (r.err if handoff else r.note)(f'{fname}:{name or "开头"}', f'还有 {n} 处〔〕占位没填')

    if not handoff:
        return r

    # ---------- 交接（SKILL.md「交接」1–4、6、7 条） ----------
    for kind in ('效果', '框架'):
        if kind not in confirms:
            r.err('plan.md:确认记录', f'没有「{kind}」一行：{kind}还没确认（或没写「自动，未问用户」），不能交接')
    for sec, rows in (('需求', need_rows), ('效果', effect_rows), ('形式', form_rows)):
        for row in rows:
            if TBD in row['内容'] or TBD in row.get('来源', ''):
                r.err(f'plan.md:{sec}', f'「{row["项"]}」还是「{TBD}」，用户定了才能交接')
    for row in gap_rows:
        if row['归谁'] == '策划' and row['状态'] == '待补':
            r.err('plan.md:缺口', f'{row["编号"]} 归策划、还待补，补完或改内容关闭后才能交接')
        if row['归谁'] == '下游':
            if not row['缺什么'] or not (REF_SEG.search(row['段']) or row['段'] == '全部'):
                r.err('plan.md:缺口', f'{row["编号"]} 归下游，要写清缺什么、哪段（段号，或「全部」）')
    said = set()
    for row in say_rows:
        for sp, _ in seg_points(row['点']):
            said.add(sp)
        for col in ('要的效果', '参考说法', '不能丢的'):
            if not row[col].strip():
                r.err('plan.md:说法', f'「{row["点"]}」的{col}空着（不能丢的没有就写「{NONE}」）')
    for row in seg_rows:
        p = row['段']
        if p not in said:
            r.err('plan.md:说法', f'{p} 没有说法：每段至少一行')
        for x in points.get(p, {}):
            ids = covered.get((p, x), [])
            if not ids:
                r.err('content.md', f'{p} 的「{x}」在 content.md 里没有对应的信息')
            for d in ids:
                st = data[d]['状态']
                if st in ('〔待核实〕', '有冲突'):
                    r.err(f'content.md:{p}', f'{p} 的「{x}」用了 {d}，它还是「{st}」')
    for i, row in rules.items():
        if row['状态'] not in ('已核实', '设定'):
            r.err('content.md:约束', f'{i} 还是「{row["状态"]}」：约束要已核实或是设定才能交接')
    for i, row in assets.items():
        if row['能不能送生成'].startswith('〔待核实〕'):
            r.note('content.md:素材', f'{i} 能不能送生成还没核实，下游按「不能」处理')
    if spin_known and not spin_none and not spin_rows:
        r.err('plan.md:衍生', '形式写了衍生，衍生节还没有行')
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
