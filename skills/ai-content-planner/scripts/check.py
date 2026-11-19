#!/usr/bin/env python3
"""检查 plans/<短名>/ 下的 plan.md、content.md 是否符合模板（格式 ai-content-planner/5），交接前加 --handoff。

用法：python3 -I <本 Skill 目录>/scripts/check.py <plans/短名 目录> [--handoff]

只用标准库。按 Markdown 标题找节、按表头找表，不依赖行号。
输出每个问题一行「文件:节: 问题」，最后一行「通过」或「N 个错、M 个提示」。
有错退出码 1，只有提示退出码 0。
格式 5：content.md 是给下游的唯一交付物（格式行、状态行在它头两行）；plan.md 只给用户看。
"""
import argparse
import os
import re
import sys

FORMAT = 'ai-content-planner/5'
OLD_FORMATS = {'ai-content-planner/1', 'ai-content-planner/2', 'ai-content-planner/3', 'ai-content-planner/4'}
PLAN_LINE = '格式和状态见 content.md'
PLAN_SECTIONS = ['确认记录', '需求', '效果', '立意', '效果自查', '取舍', '缺口', '受众', '待核实和有冲突', '检索记录']
CONTENT_HEAD = ['总则', '红线', '约束']              # 每段一节之前
CONTENT_TAIL = ['素材', '资料清单', '衍生', '下游回报']   # 每段一节之后；素材可以没有
OPTIONAL = {'素材'}
SEG_SUBS = ['念什么', '看什么', '信息']
NEED_ROWS = ['用途和场景', '必须有', '不要', '已有材料', '品牌与风格']
EFFECT_ROWS = ['接触时刻', '起点', '阻力', '终点', '衡量', '杠杆']
GENERAL_ROWS = ['输出形式和规格', '篇幅', '注意力预算', '结构', '声音', '语速', '证明方式', '制作条件',
                '基调', '张力', '钩子', '句式和节奏', '情绪曲线']
GENERAL_NEED_BASIS = ['注意力预算', '结构', '声音', '证明方式', '基调', '张力', '钩子']   # 「依据」不能空
RATES = {'慢': 4, '中': 4.5, '快': 5}   # 语速档 → 每秒几字（不含标点）；只用来估算，不做硬约束
TONES = ('冷静播报', '讲透型', '老友唠嗑', '娓娓道来', '悬念反转', '走心共鸣', '热血燃', '犀利点评', '段子手',
         '直播间促单', '权威专家', '治愈陪伴', '童趣', '文艺诗意')   # tone.md 的 14 档；另有「自定：」
TONE_EMPTY = ('要有张力', '口语化', '情绪饱满', '有感染力', '接地气')
SELF_ROWS = ['阻力', '终点', '注意力预算', '换题测试', '表达', '衍生']
PLAY_HEAD = ['打法', '抓哪条阻力', '用哪个杠杆', '开头', '代价', '选']
SEG_ROWS = ['作用', '从 → 到', '要讲的点', '篇幅', '情绪', '节奏']
MOODS = ('紧', '松', '稳', '扬')
PACES = ('快', '中', '慢')
LINE_HEAD = ['#', '不许', '怎么查', '依据']
HOW = ('词', '条件', '人工')
SAY_HEAD = ['#', '点', '句', '级', '依据']
SAY_WORDS = ('比喻', '观点', '过渡')
ORIGINAL, MUST = '原句', '必讲'
VIEW_HEAD = ['#', '要看到什么', '来源', '主角', '最大的字', '上屏的字', '配哪句', '用到']
LEADS = ('一个数', '两数对比', '走势', '构成', '排名', '表格', '流程', '清单', '一句话', '问答', '地图',
         '实物', '人', '场景', '界面')
LEAD_PICTURE = {'实物', '人', '场景', '界面'}   # 画面本身是重点，最大的字可以写「无」
DATA_HEAD = ['#', '讲哪一点', '内容', '种类', '来源', '必须写清的', '状态', '去向']
SPIN_HEAD = ['条', '用哪些点', '第一句', '放在哪']
TRADE_HEAD = ['内容', '处理', '落在', '理由']
TRADE_DO = {'保留', '合并', '延后', '删除'}
GAP_HEAD = ['编号', '段', '缺什么', '归谁', '提出于', '状态', '怎么解决的']
OPEN_HEAD = ['编号', '卡在哪', '打算怎么办', '状态', '落在']
OPEN_STATES = {'待处理', '已处理'}
SRC_HEAD = ['资料', '位置', '读到哪', '用途', '能不能公开', '用到哪些编号']
VOICE_HEAD = ['#', '内容', '种类', '来源', '对应哪条阻力', '状态']
ASSET_HEAD = ['#', '文件', '内容', '字、标志、水印、人脸', '能怎么用', '能不能送生成', '用到哪段']
RULE_HEAD = ['#', '必须守的样子', '依据', '状态']
BACK_HEAD = ['#', '段', '类型', '对象', '说明', '归谁', '状态', '怎么解决的']
BACK_TYPES = {'删减', '压缩', '偏离', '缺内容', '缺素材', '冲突'}
BACK_STATES = {'待补', '已补', '已知悉', '改内容关闭'}
SOURCES = ('代码画', '照片', '录像', '录屏', '数据', '三维模型', '生图', '生视频')
REAL = {'照片', '录像', '录屏', '三维模型'}   # 「用到」要有 M，或归下游的 Q
GENERATED = {'生图', '生视频'}               # 「用到」要有 K；用到的 M 要能送生成

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
INFO_TO = ('知道', '了解', '感受到', '认识到')            # 「到」这样开头是信息收益，提示
EMPTY_WORDS = ('引发共鸣', '提升好感', '增强信任', '提升认知', '加深印象')
CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩'
LEVEL = re.compile(rf'原句|必讲|可删[{CIRCLED}]')
NO_NARRATION = re.compile(r'(无|没有|不要|不用|不说话)旁白|不说话')
PAREN = re.compile(r'（[^（）]*(?:（[^（）]*）[^（）]*)*）|\([^()]*\)')   # 括号连同里面的字，括号里可以再套一层
MUST_SHARE, ALL_SHARE = 0.85, 1.15   # 原句 + 必讲 ≤ 上限的 85%；全部 ≤ 115%
LONG_SENTENCE = 40
HAS_NUMBER = re.compile(r'\d|[一二两三四五六七八九十百千]+[万亿]|百分之')

PLACEHOLDER = re.compile(r'〔[^〕]*〕')
REF_DATA = re.compile(r'(?<![A-Za-z0-9_])P(\d+)-(\d+)(?![\d])')
REF_SEG = re.compile(r'(?<![A-Za-z0-9_])P(\d+)(?![\d-])')


def ref_re(letter):
    return re.compile(rf'(?<![A-Za-z0-9_]){letter}(\d+)(?![\d])')


REF_GAP, REF_M, REF_K, REF_S, REF_H, REF_B, REF_X = (ref_re(x) for x in 'QMKSHBX')
S_RANGE = re.compile(r'(?<![A-Za-z0-9_])S(\d+)\s*[–\-~—至到]\s*S?(\d+)(?![\d])')
SEG_POINTS = re.compile(r'(?<![A-Za-z0-9_])P(\d+)(?![\d-])\s*([a-z](?:\s*[、,，]\s*[a-z])*)?')
POINT = re.compile(r'([a-z])\.\s*(.*)', re.S)
SHARED = re.compile(r'[（(]([^（）()]*?)\s*也用[）)]')
SHARED_REF = re.compile(r'P(\d+)\s*([a-z](?:\s*[、,，]\s*[a-z])*)?')
CONFIRM_LINE = re.compile(r'\s*[-*]\s.*?(效果|框架|局部)(?:[（(][^）)]*[）)])?[：:]')
LOCAL_PATH = re.compile(r'(?<![\w/.-])((?:source|plans)/[^\s`）)，、；;]+)')
NUM = r'\d+(?:\.\d+)?'
UNITS = {'秒': ('时间', 1), 's': ('时间', 1), '分钟': ('时间', 60), '分': ('时间', 60), 'min': ('时间', 60),
         '页': ('页', 1), '千字': ('字', 1000), '万字': ('字', 10000), '字': ('字', 1)}
UNIT_RE = '千字|万字|分钟|min|秒|分|页|字|s'
EXT_FIND = re.compile(rf'{NUM}\s*分钟?\s*{NUM}\s*秒|{NUM}\s*(?:[–\-~—至到]\s*{NUM}\s*)?(?:{UNIT_RE})(?![A-Za-z])')
BARE_RANGE = re.compile(rf'({NUM})\s*[–\-~—至到]\s*({NUM})(?![\d.])\s*({UNIT_RE})?')
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


def parse_target(cell):
    """总则「篇幅」「90 秒，80–105」→ (类, 目标下限, 目标上限, 区间下限, 区间上限)；没写区间的，区间就是目标；解析不了返回 None"""
    text = PLACEHOLDER.sub('', cell)
    m = EXT_FIND.search(text)
    t = parse_extent(m.group(0)) if m else None
    if not t:
        return None
    lo, hi = t[1], t[2]
    rm = BARE_RANGE.search(text[m.end():])
    if rm:
        unit = rm.group(3) or re.findall(UNIT_RE, m.group(0))[-1]
        kind, k = UNITS[unit]
        a, b = float(rm.group(1)) * k, float(rm.group(2)) * k
        if kind == t[0] and a <= b:
            lo, hi = min(lo, a), max(hi, b)
    return t[0], t[1], t[2], lo, hi


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
    """讲哪一点「a、b（P3 b 也用）」→ (字母列表, [(段号, 字母列表)])"""
    shared = []
    for m in SHARED.finditer(cell):
        for r in SHARED_REF.finditer(m.group(1)):
            shared.append((f'P{r.group(1)}', re.findall(r'[a-z]', r.group(2) or '')))
    rest = SHARED.sub('', cell).strip()
    if rest == NOT_USED:
        return None, shared
    return [x.strip() for x in re.split(r'[、,，]', rest) if x.strip()], shared


def parse_to(cell):
    """信息的去向「念 S3–S5；上屏 H3；依据：S7；不讲：理由」→ {'念': [S], '上屏': [H], '依据': [S], '不讲': 理由}，认不出的部分放 'bad'"""
    out = {'念': [], '上屏': [], '依据': [], '不讲': None, 'bad': []}
    for part in re.split(r'[；;]', cell):
        p = part.strip()
        if not p:
            continue
        if p.startswith('不讲'):
            reason = re.sub(r'^不讲\s*[：:]?', '', p).strip()
            out['不讲'] = reason
        elif p.startswith('上屏'):
            hs = [m.group(0) for m in REF_H.finditer(p)]
            out['上屏'] += hs
            if not hs:
                out['bad'].append(p)
        elif p.startswith(('念', '依据')):
            key = '念' if p.startswith('念') else '依据'
            ss = s_ids(p)
            out[key] += ss
            if not ss:
                out['bad'].append(p)
        else:
            out['bad'].append(p)
    return out


def s_ids(cell):
    """「S1–S3、S5」→ ['S1', 'S2', 'S3', 'S5']"""
    out = []
    for m in S_RANGE.finditer(cell):
        a, b = int(m.group(1)), int(m.group(2))
        out += [f'S{i}' for i in range(a, b + 1)] if a <= b else []
    out += [m.group(0) for m in REF_S.finditer(S_RANGE.sub('', cell))]
    return out


def spoken(cell):
    """句里要念的字：有「」的只算「」里的，没有就算整格"""
    quoted = re.findall(r'「(.*?)」', cell)
    return '；'.join(quoted) if quoted else cell


def char_count(text):
    """按念的算：一个汉字、一个数字、一个英文词各算 1；标点不算"""
    return len(re.findall(r'[一-鿿]|\d|[A-Za-z]+', text))


def value_of(cell):
    """「裁后用：裁掉顶部」→「裁后用」"""
    return re.split(r'[：:]', cell, maxsplit=1)[0].strip()


def make_terms(cell):
    """制作条件「能用：……；不能用：……」→ (能用的来源名, 不能用的来源名)；写法不对返回 None"""
    m = re.fullmatch(r'\s*能用[：:](.*?)[；;]\s*不能用[：:](.*?)[。.]?\s*', cell, re.S)
    if not m:
        return None
    names = lambda part: {value_of(x) for x in re.split(r'[、，,]', PAREN.sub('', part)) if x.strip()}   # 限制写在括号里，括号里能有逗号
    return names(m.group(1)), names(m.group(2))


def red_words(cell):
    """红线「词：「收益」「回报」；……除外」→ ['收益', '回报']（只取第一个「；」之前的）"""
    m = re.match(r'\s*词\s*[：:](.*)', cell, re.S)
    return re.findall(r'「(.*?)」', re.split(r'[；;]', m.group(1))[0]) if m else []


def split_row(line):
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [c.strip() for c in s.split('|')]


def parse_md(text, level=2):
    """→ (标题, [(节名, 行列表)])；按 level 级标题切节，第一个标题之前的行归在节名 '' 下"""
    mark = '#' * level + ' '
    title, cur = '', ('', [])
    sections = [cur]
    for line in text.split('\n'):
        if level == 2 and line.startswith('# ') and not title:
            title = line[2:].strip()
        elif line.startswith(mark):
            cur = (line[len(mark):].strip(), [])
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
    for head, rows in tables(lines or []):
        if all(c in head for c in need):
            return head, rows
    return None


def segments(text):
    """content.md → [(段号或 None, 节名, {'': 段头的行, '念什么': 行, '看什么': 行, '信息': 行})]，只收 P 开头、不是固定节的"""
    out = []
    for name, lines in parse_md(text)[1]:
        if not re.match(r'P\S*', name) or name in CONTENT_HEAD + CONTENT_TAIL:
            continue
        m = re.match(r'(P\d+)(?=\s|$)', name)
        subs = {}
        for sub, ls in parse_md('\n'.join(lines), level=3)[1]:
            subs.setdefault(sub, ls)
        out.append((m.group(1) if m else None, name, subs))
    return out


def status_of(text):
    m = re.search(r'^状态[：:]\s*([^（(\n]*)', text, re.M)
    return m.group(1).strip().rstrip('。.') if m else None


class Report:
    def __init__(self):
        self.errors, self.notes = [], []

    def err(self, where, msg):
        self.errors.append(f'{where}: {msg}')

    def note(self, where, msg):
        self.notes.append(f'{where}: {msg}')


def circled(cell):
    return [c for c in cell if c in CIRCLED]


def seg_points(cell):
    """「P1 a、b；P3 c」→ [(段号, [字母])]"""
    return [(f'P{m.group(1)}', re.findall(r'[a-z]', m.group(2) or '')) for m in SEG_POINTS.finditer(cell)]


def letters_of(cell):
    return [x.strip() for x in re.split(r'[、,，\s]+', cell) if x.strip()]


def check_order(r, where, names, want, optional=()):
    """节要按 want 的顺序出现；缺的报「缺这一节」"""
    got = [n for n in names if n in want]
    for w in want:
        if w not in got and w not in optional:
            r.err(f'{where}:{w}', '缺这一节')
    seen = [w for w in want if w in got]
    if [n for n in dict.fromkeys(got)] != seen:
        r.err(where, '节的顺序要是 ' + '、'.join(want))


def fixed_rows(r, where, lines, names, head, what):
    """固定行的表：表头含 head，第一列要正好是 names → {项: 行}"""
    t = find_table(lines, head)
    if lines is not None and not t:
        r.err(where, f'找不到{what}表（表头：' + ' | '.join(head) + '）')
        return {}
    if not t:
        return {}
    got = [row[head[0]] for row in t[1]]
    if got != names:
        r.err(where, f'{what}要正好是这{len(names)}项：' + '、'.join(names) + '；现在是 ' + '、'.join(got))
    return {row[head[0]]: row for row in t[1]}


def exact_table(r, where, lines, head, what, need_rows=False):
    """表头要正好是 head → 行列表；没有这张表报错"""
    t = find_table(lines, head[:1])
    if not t:
        r.err(where, f'找不到{what}表（表头：' + ' | '.join(head) + '）')
        return None
    if t[0] != head:
        r.err(where, f'{what}表表头要正好是「' + ' | '.join(head) + f'」，现在是「{" | ".join(t[0])}」')
        return None
    return t[1]


def id_rows(r, where, rows, prefix, pool, col='#'):
    """带编号的行：编号格式、全局不重复 → [(编号, 行)]"""
    out = []
    for row in rows or []:
        i = row[col]
        if is_placeholder(i):
            continue
        if not re.fullmatch(rf'{prefix}\d+', i):
            r.err(where, f'编号格式不对：{i or "（空）"}（写 {prefix}1、{prefix}2）')
            continue
        if i in pool:
            r.err(where, f'编号重复：{i}')
        pool[i] = row
        out.append((i, row))
    return out


def check(folder, handoff=False):
    r = Report()
    texts = {}
    for name in ('plan.md', 'content.md'):
        p = os.path.join(folder, name)
        if os.path.isfile(p):
            with open(p, encoding='utf-8') as f:
                texts[name] = f.read()
        else:
            hint = '（格式 1 的 research.md 改名 content.md，按 CHANGELOG 转）' if name == 'content.md' and os.path.isfile(os.path.join(folder, 'research.md')) else ''
            r.err(name, '文件不存在' + hint)
    if len(texts) < 2:
        return r
    soft = r.err if handoff else r.note   # 交接时是错、平时是提示

    # ---------- 格式、状态 ----------
    ctext, ptext = texts['content.md'], texts['plan.md']
    old = re.search(r'^格式[：:]\s*(\S+)', ptext, re.M)
    m = re.search(r'^格式[：:]\s*(\S+)', ctext, re.M)
    got = m.group(1) if m else (old.group(1) if old else None)
    if got != FORMAT:
        if got == 'ai-content-planner/4':
            r.err('content.md', f'格式是「{got}」，本脚本只认 {FORMAT}；照本 Skill 的 handoff.md 第 7 节转成格式 5')
        elif got in OLD_FORMATS:
            r.err('content.md', f'格式是「{got}」，本脚本只认 {FORMAT}；按本 Skill 的 CHANGELOG.md 一版一版转成格式 5')
        elif got:
            r.err('content.md', f'格式是「{got}」，本脚本只认 {FORMAT}')
        else:
            r.err('content.md', f'找不到格式行（标题下第一行写「格式：{FORMAT}」）')
        return r
    if old:
        r.err('plan.md', f'格式行只写在 content.md；plan.md 第二行写「{PLAN_LINE}」')
    status = status_of(ctext)
    if status is None:
        r.err('content.md', '找不到状态行（格式行下一行「状态：……（日期）」）')
        status = ''
    elif status not in STATUSES and not is_placeholder(status):
        r.err('content.md', f'状态「{status}」要取 ' + ' / '.join(sorted(STATUSES)))
    if status_of(ptext) is not None:
        r.err('plan.md', f'状态行只写在 content.md；plan.md 第二行写「{PLAN_LINE}」')
    elif not re.search(rf'^{PLAN_LINE}\s*$', ptext, re.M):
        r.err('plan.md', f'标题下第一行写「{PLAN_LINE}」')

    ptitle, psecs = parse_md(ptext)
    ctitle, csecs = parse_md(ctext)
    pmap, cmap = {}, {}
    for name, lines in psecs:
        pmap.setdefault(name, lines)
    for name, lines in csecs:
        cmap.setdefault(name, lines)
    if not ptitle.startswith('内容策划'):
        r.err('plan.md', '第一行标题要是「# 内容策划：题目」')
    if not ctitle.startswith('内容'):
        r.err('content.md', '第一行标题要是「# 内容：题目」')
    check_order(r, 'plan.md', [n for n, _ in psecs], PLAN_SECTIONS)
    segs_list = segments(ctext)
    cnames = []
    for n, _ in csecs:
        cnames.append('（每段）' if any(n == s[1] for s in segs_list) else n)
    want = CONTENT_HEAD + ['（每段）'] + CONTENT_TAIL
    check_order(r, 'content.md', cnames, want, optional=OPTIONAL | {'（每段）'})

    # ---------- plan.md：确认记录、需求、效果 ----------
    confirms = []
    for line in pmap.get('确认记录', []):
        if not re.match(r'\s*[-*]\s', line):
            continue
        cm = CONFIRM_LINE.match(line)
        if cm:
            confirms.append(cm.group(1))
        else:
            r.err('plan.md:确认记录', f'这一行认不出是哪种确认（写「日期 效果：」「框架：」或「局部：」）：{line.strip()[:30]}')
    need = fixed_rows(r, 'plan.md:需求', pmap.get('需求'), NEED_ROWS, ['项', '内容', '来源'], '需求') if '需求' in pmap else {}
    effect = fixed_rows(r, 'plan.md:效果', pmap.get('效果'), EFFECT_ROWS, ['项', '内容', '依据', '来源'], '效果') if '效果' in pmap else {}
    blocks = []   # 阻力编号
    if '阻力' in effect and not is_placeholder(effect['阻力']['内容']):
        blocks = circled(effect['阻力']['内容'])
        if not blocks:
            r.err('plan.md:效果', '阻力要按强弱编号：① ……<br>② ……')
        elif len(set(blocks)) != len(blocks):
            r.err('plan.md:效果', '阻力的编号重复：' + ''.join(blocks))
    for row in effect.values():
        hit = [w for w in EMPTY_WORDS if w in row['内容']]
        if hit:
            r.note('plan.md:效果', f'「{row["项"]}」写了「{hit[0]}」：效果要写成具体的念头或能看见的动作')

    def bad_blocks(cell, where, what):
        for c in circled(cell):
            if blocks and c not in blocks:
                r.err(where, f'{what}写了「{c}」，效果的阻力里没有这一条')

    # ---------- content.md：总则 ----------
    general = fixed_rows(r, 'content.md:总则', cmap.get('总则'), GENERAL_ROWS, ['项', '内容', '依据'], '总则') if '总则' in cmap else {}
    gv = lambda k: general.get(k, {}).get('内容', '')
    for name in GENERAL_NEED_BASIS:
        if name in general and not general[name]['依据'].strip() and not is_placeholder(gv(name)):
            r.err('content.md:总则', f'「{name}」的「依据」空着：要写由哪条效果推出')
    make = None   # (能用, 不能用)
    if gv('制作条件') and not is_placeholder(gv('制作条件')):
        make = make_terms(gv('制作条件'))
        if make is None:
            r.err('content.md:总则', '「制作条件」要写成「能用：……；不能用：……」，用画面来源的名字（' + '、'.join(SOURCES) + '）')
        else:
            for name in sorted((make[0] | make[1]) - set(SOURCES) - {NONE}):
                r.note('content.md:总则', f'「制作条件」里的「{name}」不是画面来源的名字（' + '、'.join(SOURCES) + '）：限制写进括号，如「生图（只出手）」')
    v = gv('基调').strip()
    if v and not is_placeholder(v) and not (v.startswith(TONES) or re.match(r'自定[：:]', v)):
        r.err('content.md:总则', f'基调「{v[:12]}」要以 tone.md 的一档开头（' + '、'.join(TONES) + '），或写「自定：……」')
    v = gv('张力')
    if v and not is_placeholder(v) and not re.match(r'\s*[123](?!\d)', v):
        r.err('content.md:总则', '张力要以 1、2、3 开头（1 克制、2 有起伏、3 强刺激），再写为什么')
    for row in general.values():
        hit = [w for w in TONE_EMPTY if w in row['内容']]
        if hit:
            r.note('content.md:总则', f'「{row["项"]}」写了「{hit[0]}」：写成能检查的样子（哪一档、哪种钩子、几个感叹号）')
    out_form, voice = gv('输出形式和规格'), gv('声音')
    is_video = out_form.strip().startswith('视频')
    narrated = is_video and '旁白' in voice and not NO_NARRATION.search(voice)
    captioned = is_video and ('上字' in voice or '字幕' in out_form + voice)
    rate = None
    v = gv('语速').strip()
    if v and not is_placeholder(v):
        first = v[:1]
        if first in RATES:
            rate = RATES[first]
        elif not v.startswith(NONE):
            r.err('content.md:总则', '语速写 慢 / 中 / 快（每秒 4、4.5、5 字），没有旁白写「无」')
        if narrated and v.startswith(NONE):
            r.err('content.md:总则', '声音有旁白，语速要写 慢 / 中 / 快，拿不准写「中」')
    target = parse_target(gv('篇幅')) if gv('篇幅') and not is_placeholder(gv('篇幅')) else None
    if gv('篇幅') and not is_placeholder(gv('篇幅')) and target is None:
        r.err('content.md:总则', f'篇幅「{gv("篇幅")[:20]}」解析不出（写「90 秒，80–105」「12 页」「3000 字」）')

    # ---------- 红线、约束、素材 ----------
    lines_ = {}
    if '红线' in cmap:
        rows = exact_table(r, 'content.md:红线', cmap['红线'], LINE_HEAD, '红线')
        for i, row in id_rows(r, 'content.md:红线', rows, 'B', lines_):
            how = row['怎么查']
            if is_placeholder(how):
                continue
            if not re.match(r'\s*(' + '|'.join(HOW) + r')\s*[：:]', how):
                r.err('content.md:红线', f'{i} 的「怎么查」要以「词：」「条件：」「人工：」开头')
            elif how.lstrip().startswith('词') and not red_words(how):
                r.err('content.md:红线', f'{i} 写了「词：」，后面要用「」列出词')
    rules, assets = {}, {}
    if '约束' in cmap:
        rows = exact_table(r, 'content.md:约束', cmap['约束'], RULE_HEAD, '约束')
        for i, row in id_rows(r, 'content.md:约束', rows, 'K', rules):
            if not is_placeholder(row['必须守的样子']) and row['状态'] not in RULE_STATES:
                r.err('content.md:约束', f'{i} 的状态「{row["状态"]}」要取 ' + ' / '.join(sorted(RULE_STATES)))
    if '素材' in cmap:
        rows = exact_table(r, 'content.md:素材', cmap['素材'], ASSET_HEAD, '素材')
        for i, row in id_rows(r, 'content.md:素材', rows, 'M', assets):
            for col, allowed in (('能怎么用', ASSET_USES), ('能不能送生成', ASSET_GEN)):
                v = row[col]
                if not is_placeholder(v) or v.startswith('〔待核实〕'):
                    if value_of(v) not in allowed:
                        r.err('content.md:素材', f'{i} 的{col}「{v}」要取 ' + ' / '.join(sorted(allowed)) + '（后面可以加「：说明」）')
        if not assets and not handoff:
            r.note('content.md:素材', '素材节只在有真实文件时写；没有就删掉这一节')
        elif not assets:
            r.err('content.md:素材', '素材节没有行：没有真实文件就删掉这一节')

    # ---------- 每段一节 ----------
    segs, points, heads = [], {}, {}     # 段号顺序；'P1' → {'a': 这一点}；'P1' → 段头
    says, views, data = {}, {}, {}       # 'S1' / 'H1' / 'P1-1' → 行
    seg_of = {}                          # 编号 → 段号
    say_order = []                       # S 按文件里的顺序
    covered = {}                         # ('P1', 'a') → [信息编号]（去向不是只有「不讲」的）
    said_pts = set()                     # ('P1', 'a')：有一句念它
    data_seg = {}                        # 信息 → 它在哪一节
    for pid, name, subs in segs_list:
        where = f'content.md:{name}'
        if not pid:
            r.err(where, f'节名的段号格式不对：{name.split()[0]}（写「## P1 段的作用」）')
            continue
        if pid in heads:
            r.err(where, f'段 {pid} 有两节')
            continue
        segs.append(pid)
        where = f'content.md:{pid}'
        head = fixed_rows(r, where, subs.get(''), SEG_ROWS, ['项', '内容'], '段头')
        heads[pid] = head
        cell = head.get('要讲的点', {}).get('内容', '')
        pts = parse_points(cell) if cell else []
        letters = [x[0] for x in pts or []]
        if pts is None or (head and not cell.strip()):
            r.err(where, f'{pid} 的要讲的点要按「a. 一点一句<br>b. ……」写')
        elif letters != [chr(ord('a') + i) for i in range(len(letters))]:
            r.err(where, f'{pid} 的要讲的点要从 a 起按顺序编：现在是 ' + '、'.join(letters))
        points[pid] = dict(pts or [])
        d = head.get('篇幅', {}).get('内容', '')
        if d and not is_placeholder(d) and parse_extent(d) is None:
            r.err(where, f'{pid} 的篇幅「{d}」解析不出（写「N 秒」「N 页」「N 字」、区间，或「不限」）')
        v = head.get('情绪', {}).get('内容', '').strip()
        if head and not is_placeholder(v) and not v.startswith(MOODS):
            r.err(where, f'{pid} 的情绪要以 紧 / 松 / 稳 / 扬 开头（后面可以带局部档）')
        v = head.get('节奏', {}).get('内容', '').strip()
        if head and not is_placeholder(v) and not v.startswith(PACES):
            r.err(where, f'{pid} 的节奏要以 快 / 中 / 慢 开头')
        aud = head.get('从 → 到', {}).get('内容', '')
        if aud and not is_placeholder(aud):
            if '→' not in aud:
                r.err(where, f'{pid} 的「从 → 到」要写「原来的念头 → 看完这段的念头或动作」，现在没有「→」')
            else:
                to = aud.rsplit('→', 1)[1].strip().lstrip('「“"\'')
                if to.startswith(INFO_TO):
                    r.note(where, f'{pid} 的「到」以「{to[:3]}」开头：写成具体的念头或动作，别停在知道了什么')
            hit = [w for w in EMPTY_WORDS if w in aud]
            if hit:
                r.note(where, f'{pid} 的「从 → 到」写了「{hit[0]}」：写成具体的念头或动作')
        for sub in SEG_SUBS:
            if sub not in subs:
                r.err(where, f'缺「### {sub}」')
        rows = exact_table(r, f'{where}:念什么', subs['念什么'], SAY_HEAD, '念什么') if '念什么' in subs else None
        for i, row in id_rows(r, f'{where}:念什么', rows, 'S', says):
            seg_of[i] = pid
            say_order.append(i)
            if is_placeholder(row['句']):
                continue
            if not LEVEL.fullmatch(row['级'].strip()) and not is_placeholder(row['级']):
                r.err(f'{where}:念什么', f'{i} 的级「{row["级"]}」要取 原句 / 必讲 / 可删①（圈号是删的顺序）')
            ls = letters_of(row['点'])
            if not ls:
                r.err(f'{where}:念什么', f'{i} 的点空着：写本段要讲的点的字母')
            for x in ls:
                if x not in points[pid]:
                    r.err(f'{where}:念什么', f'{i} 的点「{x}」不在 {pid} 的要讲的点里')
                said_pts.add((pid, x))
            basis = row['依据']
            if not is_placeholder(basis):
                refs = REF_DATA.search(basis) or REF_K.search(basis) or REF_B.search(basis)
                if not (refs or any(w in basis for w in SAY_WORDS)):
                    r.err(f'{where}:念什么', f'{i} 的依据要写信息、约束、红线编号（P1-1、K1、B1），不说事实的写 比喻 / 观点 / 过渡')
                elif HAS_NUMBER.search(spoken(row['句'])) and not REF_DATA.search(basis):
                    r.err(f'{where}:念什么', f'{i} 说了数字，依据要有信息编号（P1-1）')
        rows = exact_table(r, f'{where}:看什么', subs['看什么'], VIEW_HEAD, '看什么') if '看什么' in subs else None
        for i, row in id_rows(r, f'{where}:看什么', rows, 'H', views):
            seg_of[i] = pid
        rows = exact_table(r, f'{where}:信息', subs['信息'], DATA_HEAD, '信息') if '信息' in subs else None
        for row in rows or []:
            did = row['#']
            if is_placeholder(did):
                continue
            if not re.fullmatch(rf'{pid}-\d+', did):
                r.err(f'{where}:信息', f'编号格式不对：{did or "（空）"}（这一节写 {pid}-1、{pid}-2）')
                continue
            if did in data:
                r.err(f'{where}:信息', f'编号重复：{did}')
            data[did] = row
            data_seg[did] = pid

    # 信息：状态、讲哪一点、去向（每段的字母要等所有段头读完才查得了「也用」）
    tos = {}
    for did, row in data.items():
        pid, where = data_seg[did], f'content.md:{data_seg[did]}:信息'
        if is_placeholder(row['内容']):
            continue
        st = row['状态']
        if st not in DATA_STATES:
            r.err(where, f'{did} 的状态「{st}」不在 ' + ' / '.join(sorted(DATA_STATES)) + ' 里')
        to = parse_to(row['去向']) if row['去向'].strip() and not is_placeholder(row['去向']) else None
        tos[did] = to
        if not row['去向'].strip():
            r.err(where, f'{did} 的去向空着：写 念 S3 / 上屏 H3 / 依据：S7 / 不讲：理由')
        elif to:
            for b in to['bad']:
                r.err(where, f'{did} 的去向「{b[:16]}」认不出：写 念 S3 / 上屏 H3 / 依据：S7 / 不讲：理由，用「；」隔开')
            if to['不讲'] is not None and not to['不讲']:
                r.err(where, f'{did} 写了「不讲」，后面要写理由（不讲：……）')
            if to['不讲'] is not None and (to['念'] or to['上屏'] or to['依据']):
                r.err(where, f'{did} 的去向写了「不讲」，就不能再念、上屏或作依据')
        used = not (to and to['不讲'] is not None)
        letters, shared = parse_which(row['讲哪一点'])
        if letters is None:
            r.err(where, f'{did} 的「讲哪一点」写了「{NOT_USED}」：格式 5 改成写字母，去向写「不讲：理由」')
            letters = []
        elif not letters:
            r.err(where, f'{did} 的「讲哪一点」空着（写这段要讲的点的字母）')
        for x in letters:
            if x not in points.get(pid, {}):
                r.err(where, f'{did} 讲的「{x}」不在 {pid} 的要讲的点里')
            if used:
                covered.setdefault((pid, x), []).append(did)
        for sp, sl in shared:
            if sp == pid or sp not in points:
                r.err(where, f'{did} 写了「{sp} 也用」，{sp} ' + ('就是本段' if sp == pid else '在 content.md 里没有这一段'))
                continue
            for x in sl:
                if x not in points[sp]:
                    r.err(where, f'{did} 写了「{sp} {x} 也用」，「{x}」不在 {sp} 的要讲的点里')
                if used:
                    covered.setdefault((sp, x), []).append(did)

    # 去向和念什么的依据、看什么的用到两边对得上
    for did, to in tos.items():
        if not to:
            continue
        where = f'content.md:{data_seg[did]}:信息'
        for s in to['念'] + to['依据']:
            if s not in says:
                r.err(where, f'{did} 的去向写了 {s}，念什么里没有这一句')
            elif not is_placeholder(says[s]['依据']) and did not in data_refs(says[s]['依据']):
                r.err(where, f'{did} 的去向写了 {s}，{s} 的依据里却没有 {did}')
        for h in to['上屏']:
            if h not in views:
                r.err(where, f'{did} 的去向写了上屏 {h}，看什么里没有这一格')
            elif not is_placeholder(views[h]['用到']) and did not in data_refs(views[h]['用到']):
                r.err(where, f'{did} 的去向写了上屏 {h}，{h} 的用到里却没有 {did}')
    for s, row in says.items():
        if is_placeholder(row['依据']):
            continue
        for did in data_refs(row['依据']):
            to = tos.get(did)
            if did in data and to is not None and s not in to['念'] + to['依据']:
                r.err(f'content.md:{seg_of[s]}:念什么', f'{s} 的依据写了 {did}，{did} 的去向没有「念 {s}」或「依据：{s}」')
    for h, row in views.items():
        if is_placeholder(row['用到']):
            continue
        for did in data_refs(row['用到']):
            to = tos.get(did)
            if did in data and to is not None and h not in to['上屏']:
                r.err(f'content.md:{seg_of[h]}:看什么', f'{h} 的用到写了 {did}，{did} 的去向没有「上屏 {h}」')

    # ---------- 看什么：来源、主角、最大的字、配哪句、着落 ----------
    gaps, gap_rows, owner = {}, [], {}
    if '缺口' in pmap:
        gap_rows = exact_table(r, 'plan.md:缺口', pmap['缺口'], GAP_HEAD, '缺口') or []
        for q, row in id_rows(r, 'plan.md:缺口', gap_rows, 'Q', gaps, col='编号'):
            for col, allowed in (('归谁', OWNERS), ('提出于', RAISED), ('状态', GAP_STATES)):
                v = row[col]
                if v not in allowed and not is_placeholder(v):
                    r.err('plan.md:缺口', f'{q} 的{col}「{v}」要取 ' + ' / '.join(sorted(allowed)))
            how = row['怎么解决的']
            if row['状态'] == '改内容关闭' and (not how or is_placeholder(how)):
                r.err('plan.md:缺口', f'{q} 是「改内容关闭」，「怎么解决的」要写删了、收窄了或改了什么')
            owner[q] = row['归谁']
    shot_ms, shot_segs = set(), set()
    for h, row in views.items():
        pid = seg_of[h]
        where = f'content.md:{pid}:看什么'
        if is_placeholder(row['要看到什么']):
            continue
        shot_segs.add(pid)
        src = row['来源']
        if not is_placeholder(src):
            if src not in SOURCES:
                r.err(where, f'{h} 的来源「{src}」要取 ' + ' / '.join(SOURCES))
            elif make and src in make[1]:
                r.err(where, f'{h} 的来源是「{src}」，总则的制作条件写了不能用')
        lead = row['主角'].strip()
        if not is_placeholder(lead):
            if re.match(r'其他[：:]\s*\S', lead):
                r.note(where, f'{h} 的主角写了「其他」：下游没有现成的查表，能归进 15 个之一的就归')
            elif lead not in LEADS:
                r.err(where, f'{h} 的主角「{lead}」要取 ' + '、'.join(LEADS) + '，或「其他：……」')
        big = row['最大的字'].strip()
        if not big:
            r.err(where, f'{h} 的最大的字空着：写这一格字号最大的那几个字，画面本身是重点的写「{NONE}」')
        elif big == NONE and lead in LEADS and lead not in LEAD_PICTURE:
            r.note(where, f'{h} 的主角是「{lead}」，最大的字却写了「{NONE}」')
        if not row['上屏的字'].strip():
            r.err(where, f'{h} 的上屏的字空着：照原文写全，没有写「{NONE}」')
        pair = row['配哪句'].strip()
        if pair and pair != NONE and not is_placeholder(pair):
            ss = s_ids(pair)
            if not ss:
                r.err(where, f'{h} 的配哪句写 S 编号或「{NONE}」')
            for s in ss:
                if s not in says:
                    r.err(where, f'{h} 配的 {s} 在念什么里没有')
                elif seg_of[s] != pid:
                    r.err(where, f'{h} 配的 {s} 在 {seg_of[s]}，要配本段的句')
            if big and big != NONE and not is_placeholder(big) and ss:
                hay = row['上屏的字'] + ''.join(spoken(says[s]['句']) for s in ss if s in says)
                if big.strip('「」') not in hay:
                    r.note(where, f'{h} 的最大的字「{big}」不在上屏的字里，也不在配的那句里')
        elif not pair:
            r.err(where, f'{h} 的配哪句空着：写 S 编号，不配某句写「{NONE}」')
        use = row['用到']
        if is_placeholder(use):
            continue
        found = seg_points(use)
        for sp, sl in found:
            for x in sl:
                if sp in points and x not in points[sp]:
                    r.err(where, f'{h} 用到「{sp} {x}」，「{x}」不在 {sp} 的要讲的点里')
        ms = [x.group(0) for x in REF_M.finditer(use)]
        shot_ms.update(ms)
        ds = data_refs(use)
        qs_down = [x.group(0) for x in REF_GAP.finditer(use) if owner.get(x.group(0)) == '下游']
        ks = [x.group(0) for x in REF_K.finditer(use)]
        if not (ds or ms or found or ks or REF_GAP.search(use)):
            r.err(where, f'{h} 的「用到」要写编号（P1-1、P1 a、M1、K1、Q1）')
        elif src == '代码画' and not (ds or any(sl for _, sl in found)):
            r.err(where, f'{h} 是代码画，「用到」要有它画的信息（P1-1）或上屏的点（P1 a）')
        elif src in REAL and not (ms or qs_down):
            r.err(where, f'{h} 是{src}，「用到」要有素材 M，或归下游的缺口 Q')
        elif src == '数据' and not (ds or ms):
            r.err(where, f'{h} 是数据，「用到」要有数据本身（P1-1）或数据文件（M1）')
        elif src in GENERATED and not ks:
            r.err(where, f'{h} 是{src}，「用到」至少要有一条约束 K')
        if src in GENERATED:
            for m_ in ms:
                gen = assets.get(m_, {}).get('能不能送生成', '')
                if value_of(gen) == '不能':
                    r.err(where, f'{h} 是{src}，用到的 {m_} 不能送生成')
                elif gen.startswith('〔待核实〕'):
                    r.note(where, f'{h} 是{src}，用到的 {m_} 能不能送生成还没核实')
    for i, row in assets.items():
        if row['用到哪段'].strip() != NOT_USED and not is_placeholder(row['用到哪段']) and i not in shot_ms:
            r.note('content.md:素材', f'{i} 要用（{row["用到哪段"]}），但看什么没有一格用到它')

    # ---------- 红线的词出现在念什么里 ----------
    for b, row in lines_.items():
        for w in red_words(row['怎么查']):
            for s, srow in says.items():
                if w and w in spoken(srow['句']):
                    r.note(f'content.md:{seg_of[s]}:念什么', f'{s} 用了红线 {b} 的词「{w}」（引述原话可以；原句撞红线要在交接前改掉）')

    # ---------- 字数（估算，不做硬约束）、长句、原句、可删 ----------
    if narrated:
        for s, row in says.items():
            n = char_count(spoken(row['句']))
            if n > LONG_SENTENCE and not is_placeholder(row['句']):
                r.note(f'content.md:{seg_of[s]}:念什么', f'{s} 有 {n} 字，口播单句不超过 {LONG_SENTENCE} 字')
    for pid in segs:
        rows_ = [says[s] for s in say_order if seg_of[s] == pid and not is_placeholder(says[s]['句'])]
        if not rows_:
            continue
        lv = [x['级'].strip() for x in rows_]
        if narrated and not any(x.startswith('可删') for x in lv) and any(x != ORIGINAL for x in lv):
            soft(f'content.md:{pid}:念什么', f'{pid} 没有「可删」：每段至少一句，留给下游删减（只有原句的段除外）')
        e = parse_extent(heads[pid].get('篇幅', {}).get('内容', ''))
        if narrated and rate and e and e[0] == '时间':
            limit = (e[1] + e[2]) / 2 * rate
            must = sum(char_count(spoken(x['句'])) for x in rows_ if x['级'].strip() in (ORIGINAL, MUST))
            total = sum(char_count(spoken(x['句'])) for x in rows_)
            if must > limit * MUST_SHARE:
                r.note(f'content.md:{pid}:念什么', f'{pid} 原句加必讲 {must} 字，超过上限 {limit:g} 字的 85%（{limit * MUST_SHARE:.0f} 字）：留给下游删的余量不够（估算，以配音实测为准）')
            if total > limit * ALL_SHARE:
                r.note(f'content.md:{pid}:念什么', f'{pid} 全部 {total} 字，超过上限 {limit:g} 字的 115%（{limit * ALL_SHARE:.0f} 字）（估算，以配音实测为准）')
    self_rows = {}
    if '效果自查' in pmap:
        self_rows = fixed_rows(r, 'plan.md:效果自查', pmap['效果自查'], SELF_ROWS, ['查什么', '结果'], '效果自查')
        res = self_rows.get('阻力', {}).get('结果', '')
        if res and not is_placeholder(res):
            miss = [c for c in blocks if c not in res]
            if miss:
                r.err('plan.md:效果自查', '阻力' + ''.join(miss) + ' 没写由哪段回应')
            bad_blocks(res, 'plan.md:效果自查', '阻力一行')
        end_ = self_rows.get('终点', {}).get('结果', '')
        if end_ and not is_placeholder(end_) and not REF_SEG.search(end_):
            r.err('plan.md:效果自查', '终点一行要写落在哪段（段号）')
    if (narrated or captioned) and say_order:
        first = says[say_order[0]]
        if not is_placeholder(first['句']) and first['级'].strip() != ORIGINAL:
            soft(f'content.md:{seg_of[say_order[0]]}:念什么', f'全片第一句 {say_order[0]}（钩子句）的级要是「{ORIGINAL}」')
        m = REF_SEG.search(self_rows.get('终点', {}).get('结果', ''))
        end_seg = m.group(0) if m else None
        end_rows = [says[s] for s in say_order if seg_of[s] == end_seg]
        if end_rows and not any(x['级'].strip() == ORIGINAL for x in end_rows):
            soft(f'content.md:{end_seg}:念什么', f'终点 {end_seg} 那段要有一句「{ORIGINAL}」')

    # 篇幅合计和总则比：单位一致才比
    exts = [parse_extent(heads[p].get('篇幅', {}).get('内容', '')) for p in segs if heads[p]]
    if exts and all(exts) and target:
        kinds = {e[0] for e in exts} - {'不限'}
        if len(kinds) > 1:
            r.note('content.md', '各段篇幅单位不一致：' + ' / '.join(sorted(kinds)))
        elif kinds == {target[0]}:
            lo = sum(e[1] for e in exts if e[0] != '不限')
            hi = sum(e[2] for e in exts if e[0] != '不限')
            if target[3] == target[1] and target[4] == target[2]:
                lo_ok, hi_ok = target[1] * 0.85, target[2] * 1.15
            else:
                lo_ok, hi_ok = target[3], target[4]
            if hi < lo_ok or lo > hi_ok:
                u = SHOW[target[0]]
                fmt = lambda a, b: f'{a:g} {u}' if a == b else f'{a:g}–{b:g} {u}'
                r.note('content.md', f'各段篇幅合计 {fmt(lo, hi)}，不在总则篇幅的区间 {fmt(lo_ok, hi_ok)} 里')

    # ---------- plan.md：立意、取舍、受众、待核实 ----------
    sec = '立意'
    if sec in pmap:
        if not any(re.match(r'\s*一句话主线[：:]', line) for line in pmap[sec]):
            r.err(f'plan.md:{sec}', '缺「一句话主线：」一行')
        if not any(re.match(r'\s*内容流程[：:]', line) for line in pmap[sec]):
            r.err(f'plan.md:{sec}', '缺「内容流程：」一行（打法表后面，P1 → P2 → P3 的逻辑线）')
        rows = exact_table(r, f'plan.md:{sec}', pmap[sec], PLAY_HEAD, '打法')
        if rows is not None:
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
    trades = []
    if '取舍' in pmap:
        trades = exact_table(r, 'plan.md:取舍', pmap['取舍'], TRADE_HEAD, '取舍') or []
        for row in trades:
            do, land = row['处理'], row['落在']
            if not row['内容'].strip() or is_placeholder(do):
                continue
            if do not in TRADE_DO:
                r.err('plan.md:取舍', f'「{row["内容"][:12]}」的处理「{do}」要取 ' + ' / '.join(sorted(TRADE_DO)))
            elif do in ('保留', '合并') and not any(rx.search(land) for rx in (REF_S, REF_H, REF_B, REF_K)):
                r.err('plan.md:取舍', f'「{row["内容"][:12]}」是「{do}」，「落在」要写落在哪句、哪格、哪条红线或约束（S、H、B、K 编号）')
    voices = {}
    if '受众' in pmap:
        rows = exact_table(r, 'plan.md:受众', pmap['受众'], VOICE_HEAD, '受众')
        for i, row in id_rows(r, 'plan.md:受众', rows, 'V', voices):
            if is_placeholder(row['内容']):
                continue
            if row['状态'] not in DATA_STATES:
                r.err('plan.md:受众', f'{i} 的状态「{row["状态"]}」不在 ' + ' / '.join(sorted(DATA_STATES)) + ' 里')
            if row['对应哪条阻力'] != NONE and not is_placeholder(row['对应哪条阻力']):
                if not circled(row['对应哪条阻力']):
                    r.err('plan.md:受众', f'{i} 的「对应哪条阻力」写阻力的编号（①），不对应写「{NONE}」')
                bad_blocks(row['对应哪条阻力'], 'plan.md:受众', f'{i} 的对应哪条阻力')
    opens = []
    if '待核实和有冲突' in pmap:
        opens = exact_table(r, 'plan.md:待核实和有冲突', pmap['待核实和有冲突'], OPEN_HEAD, '待核实和有冲突') or []
        for row in opens:
            if is_placeholder(row['编号']) or not row['编号']:
                continue
            st = row['状态']
            if st not in OPEN_STATES and not is_placeholder(st):
                r.err('plan.md:待核实和有冲突', f'{row["编号"]} 的状态「{st}」要取 待处理 / 已处理')
            if st == '待处理':
                soft('plan.md:待核实和有冲突', f'{row["编号"]} 还「待处理」：交接前处理完，结果写进「落在」')
            elif not row['落在'].strip():
                soft('plan.md:待核实和有冲突', f'{row["编号"]} 的「落在」空着：写处理结果落在哪（S、B、信息编号），或「无：理由」')

    # ---------- 资料清单、衍生、下游回报 ----------
    sec = '资料清单'
    if sec in cmap:
        rows = exact_table(r, f'content.md:{sec}', cmap[sec], SRC_HEAD, '资料')
        short = os.path.basename(os.path.normpath(folder))
        for row in rows or []:
            use = row['用途']
            if not is_placeholder(use) and row['资料'].strip():
                bad = [u for u in re.split(r'、', use) if u.strip() not in USES]
                if not use or bad:
                    r.err(f'content.md:{sec}', f'「{row["资料"]}」的用途「{use}」要取 ' + ' / '.join(sorted(USES)) + '，多个用「、」隔开；补充说明写进「读到哪」或「能不能公开」')
            if is_placeholder(row['位置']):
                continue
            for pm in LOCAL_PATH.finditer(row['位置']):
                path = pm.group(1)
                parts = path.split('/')
                if parts[0] == 'plans' and len(parts) > 1 and parts[1] != short:
                    soft(f'content.md:{sec}', f'「{row["资料"][:16]}」指到别的策划目录 {path}：拷进本目录的 source/，位置改写本目录的路径')
                    continue
                rel = '/'.join(parts[2:]) if parts[0] == 'plans' else path
                if not os.path.exists(os.path.join(folder, rel)):
                    soft(f'content.md:{sec}', f'「{row["资料"][:16]}」的位置 {path} 不存在')
    spins = {}
    sec = '衍生'
    if sec in cmap:
        t = find_table(cmap[sec], ['条'])
        body = [x.strip() for x in cmap[sec] if x.strip() and not x.strip().startswith('>')]
        if t:
            rows = exact_table(r, f'content.md:{sec}', cmap[sec], SPIN_HEAD, '衍生')
            for i, row in id_rows(r, f'content.md:{sec}', rows, 'D', spins, col='条'):
                if not is_placeholder(row['用哪些点']):
                    found = seg_points(row['用哪些点'])
                    if not found:
                        r.err(f'content.md:{sec}', f'{i} 的用哪些点要写成「P1 a」「P1 a、b」')
                    for sp, sl in found:
                        if sp not in points:
                            r.err(f'content.md:{sec}', f'{i} 用到的段 {sp} 在 content.md 里没有')
                        for x in sl:
                            if sp in points and x not in points[sp]:
                                r.err(f'content.md:{sec}', f'{i} 用到「{sp} {x}」，「{x}」不在 {sp} 的要讲的点里')
            if handoff and not spins:
                r.err(f'content.md:{sec}', f'衍生表没有行：没有衍生就只写一行「{NONE}」')
        elif body != [NONE]:
            r.err(f'content.md:{sec}', f'没有衍生就只写一行「{NONE}」；有就用表（表头：' + ' | '.join(SPIN_HEAD) + '）')
    backs = {}
    sec = '下游回报'
    if sec in cmap:
        rows = exact_table(r, f'content.md:{sec}', cmap[sec], BACK_HEAD, '下游回报')
        for i, row in id_rows(r, f'content.md:{sec}', rows, 'X', backs):
            where = f'content.md:{sec}'
            if row['段'] != '全部' and not all(p in points for p in [m.group(0) for m in REF_SEG.finditer(row['段'])] or ['?']):
                r.err(where, f'{i} 的段「{row["段"]}」写段号（P1）或「全部」')
            for col, allowed in (('类型', BACK_TYPES), ('归谁', OWNERS), ('状态', BACK_STATES)):
                if row[col] not in allowed:
                    r.err(where, f'{i} 的{col}「{row[col]}」要取 ' + ' / '.join(sorted(allowed)))
            if row['状态'] == '待补':
                soft(where, f'{i} 还「待补」：回流没处理完，处理后写「怎么解决的」')
                if row['归谁'] == '策划' and status != '回流中':
                    r.note('content.md', f'{i} 归策划、还待补，状态行该是「回流中」')
            if row['状态'] == '改内容关闭' and not row['怎么解决的'].strip():
                r.err(where, f'{i} 是「改内容关闭」，「怎么解决的」要写改了什么')

    # ---------- 引用都要存在：只查规定写编号的那几格 ----------
    pools = {'P': (REF_SEG, points, '引用的段 {} 在 content.md 里没有'), 'D': (REF_DATA, data, '引用的 {} 在 content.md 里没有'),
             'M': (REF_M, assets, '引用的 {} 在 content.md 的素材表里没有'), 'K': (REF_K, rules, '引用的 {} 在 content.md 的约束表里没有'),
             'Q': (REF_GAP, gaps, '引用的 {} 在缺口表里没有'), 'S': (REF_S, says, '引用的 {} 在念什么里没有'),
             'H': (REF_H, views, '引用的 {} 在看什么里没有'), 'B': (REF_B, lines_, '引用的 {} 在红线里没有')}
    cells = []   # (位置, 格子内容, 查哪几种编号)
    for pid in segs:
        cells.append((f'content.md:{pid}', heads[pid].get('作用', {}).get('内容', ''), 'P'))
    for row in self_rows.values():
        cells.append(('plan.md:效果自查', row['结果'], 'PS'))
    cells.append(('content.md:总则', gv('基调'), 'P'))
    cells.append(('content.md:总则', gv('钩子'), 'S'))
    for h, row in views.items():
        cells.append((f'content.md:{seg_of[h]}:看什么', row['用到'], 'PDMKQ'))
    for s, row in says.items():
        cells.append((f'content.md:{seg_of[s]}:念什么', row['依据'], 'DKB'))
    for row in gap_rows:
        cells += [('plan.md:缺口', row['段'], 'P'), ('plan.md:缺口', row['怎么解决的'], 'D')]
    for row in assets.values():
        cells.append(('content.md:素材', row['用到哪段'], 'P'))
    for row in rules.values():
        cells.append(('content.md:约束', row['依据'], 'DM'))
    for did, row in data.items():
        cells.append((f'content.md:{data_seg[did]}:信息', row['来源'], 'M'))
    for row in trades:
        cells.append(('plan.md:取舍', row['落在'], 'SHBK'))
    for row in opens:
        cells.append(('plan.md:待核实和有冲突', row['落在'], 'SHBKD'))
    for row in backs.values():
        cells.append(('content.md:下游回报', row['对象'], 'SHDBKM'))
    reported = set()
    for where, cell, kinds in cells:
        if is_placeholder(cell):
            continue
        for k in kinds:
            rx, pool, msg = pools[k]
            for x in rx.finditer(cell):
                ref = x.group(0)
                if ref not in pool and (where, ref) not in reported:
                    reported.add((where, ref))
                    r.err(where, msg.format(ref))

    # 占位（〔待核实〕是状态，不算）
    count = lambda t: sum(1 for x in PLACEHOLDER.finditer(t) if x.group(0) != '〔待核实〕')
    for fname in ('plan.md', 'content.md'):
        title, secs = parse_md(texts[fname])
        for name, lines in [('标题', [title])] + secs:
            n = count('\n'.join([name] + [x for x in lines if not x.lstrip().startswith('>')]))
            if n:
                soft(f'{fname}:{name or "开头"}', f'还有 {n} 处〔〕占位没填')
    for pid in segs:
        if pid not in shot_segs and heads[pid]:
            soft(f'content.md:{pid}:看什么', f'{pid} 没有看什么：每段至少一行')

    if not handoff:
        return r

    # ---------- 交接（SPEC-5-P 第 7 节） ----------
    for kind in ('效果', '框架'):
        if kind not in confirms:
            r.err('plan.md:确认记录', f'没有「{kind}」一行：{kind}还没确认（或没写「自动，未问用户」），不能交接')
    for sec, rows in (('plan.md:需求', need), ('plan.md:效果', effect)):
        for row in rows.values():
            if TBD in row['内容'] or TBD in row.get('来源', ''):
                r.err(sec, f'「{row["项"]}」还是「{TBD}」，用户定了才能交接')
    for row in general.values():
        if TBD in row['内容'] + row['依据']:
            r.err('content.md:总则', f'「{row["项"]}」还是「{TBD}」，用户定了才能交接')
        elif not row['内容'].strip():
            r.err('content.md:总则', f'「{row["项"]}」空着：总则各行都写了才能交接')
    if not segs:
        r.err('content.md', '没有段：每段一节（## P1 段的作用）')
    for row in gap_rows:
        if row['归谁'] == '策划' and row['状态'] == '待补':
            r.err('plan.md:缺口', f'{row["编号"]} 归策划、还待补，补完或改内容关闭后才能交接')
        if row['归谁'] == '下游':
            if not row['缺什么'] or not (REF_SEG.search(row['段']) or row['段'] == '全部'):
                r.err('plan.md:缺口', f'{row["编号"]} 归下游，要写清缺什么、哪段（段号，或「全部」）')
    for pid in segs:
        if not any(seg_of[s] == pid for s in says):
            r.err(f'content.md:{pid}:念什么', f'{pid} 没有念什么：每段至少一句')
        for x in points.get(pid, {}):
            if not covered.get((pid, x)):
                r.err(f'content.md:{pid}', f'{pid} 的「{x}」没有对应的信息（去向不是「不讲」的）')
            if (pid, x) not in said_pts:
                r.err(f'content.md:{pid}:念什么', f'{pid} 的「{x}」没有一句念它')
    for did, to in tos.items():
        if to and to['不讲'] is None and data[did]['状态'] not in ('已核实', '设定'):
            r.err(f'content.md:{data_seg[did]}:信息', f'{did} 要用（去向不是「不讲」），它还是「{data[did]["状态"]}」')
    for i, row in rules.items():
        if row['状态'] not in ('已核实', '设定'):
            r.err('content.md:约束', f'{i} 还是「{row["状态"]}」：约束要已核实或是设定才能交接')
    for i, row in assets.items():
        if row['能不能送生成'].startswith('〔待核实〕'):
            r.note('content.md:素材', f'{i} 能不能送生成还没核实，下游按「不能」处理')
    if status not in HANDOFF_STATES:
        r.note('content.md', f'状态是「{status}」，交接时改成「已交接」')
    return r


def data_refs(cell):
    return [m.group(0) for m in REF_DATA.finditer(cell)]


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
