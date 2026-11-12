"""check.py 的离线测试。运行：python3 -m unittest discover -s skills/ai-content-planner/scripts/tests

fixtures/ok/ 是一份全通过的；其余每个夹具目录只放改过的文件，测试时叠在 ok/ 上。
"""
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import check  # noqa: E402

FIX = os.path.join(HERE, 'fixtures')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def run(folder, handoff=False):
    out = io.StringIO()
    with redirect_stdout(out):
        code = check.main([folder] + (['--handoff'] if handoff else []))
    return code, out.getvalue()


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def case(self, name):
        """ok/ 叠上 fixtures/<name>/ → 临时目录"""
        for src in (os.path.join(FIX, 'ok'), os.path.join(FIX, name)):
            for f in os.listdir(src):
                shutil.copy(os.path.join(src, f), self.tmp)
        return self.tmp

    def assertFails(self, name, pattern, handoff=True):
        code, out = run(self.case(name), handoff)
        self.assertEqual(code, 1, out)
        self.assertRegex(out, pattern)

    def test_ok(self):
        for handoff in (False, True):
            code, out = run(os.path.join(FIX, 'ok'), handoff)
            self.assertEqual((code, out.strip()), (0, '通过'))

    def test_bad_columns(self):
        code, out = run(self.case('bad_columns'))
        self.assertEqual(code, 1)
        self.assertIn('段落表表头要正好是', out)
        self.assertNotIn('引用的段', out)   # 表头错了不连带报引用

    def test_missing_ref(self):
        self.assertFails('missing_ref', r'plan.md:缺口: 引用的 P2-9 在 content.md 里没有', handoff=False)

    def test_open_gap(self):
        self.assertEqual(run(self.case('open_gap'))[0], 0)   # 普通检查只看格式
        self.assertFails('open_gap', r'Q2 归策划、还待补')

    def test_closed_no_reason(self):
        self.assertFails('closed_no_reason', r'Q3 是「改内容关闭」', handoff=False)

    def test_unverified(self):
        """「不用」的〔待核实〕不挡交接；改成讲 a 就挡"""
        self.assertEqual(run(self.case('unverified'))[0], 0)
        self.assertFails('unverified', r'P1 的「a」用了 P1-2，它还是「〔待核实〕」')

    def test_old_format(self):
        """格式 2 报错，提示按 CHANGELOG 转，不再往下查"""
        code, out = run(self.case('old_format'))
        self.assertEqual(code, 1)
        self.assertIn('本脚本只认 ai-content-planner/3；这是旧格式，按本 Skill 的 CHANGELOG.md 转成格式 3', out)
        self.assertEqual(out.count('\n'), 2, out)

    def test_research_md_hint(self):
        """只有格式 1 的 research.md：提示改名"""
        shutil.copy(os.path.join(FIX, 'ok', 'plan.md'), self.tmp)
        shutil.copy(os.path.join(FIX, 'ok', 'content.md'), os.path.join(self.tmp, 'research.md'))
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn('research.md 改名 content.md', out)

    def test_need_rows(self):
        self.assertFails('need_rows', r'需求要正好是这5项：用途和场景、必须有', handoff=False)

    def test_effect_rows(self):
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        write(path, read(path).replace('| 衡量 | 无 | | 用户给的 |\n', '| 衡量 | 无 | | 用户给的 |\n| 凭什么信 | 夹具占位 | | 建议 |\n'))
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('效果要正好是这6项', out)

    def test_need_tbd(self):
        """效果有「待你定」：普通检查过，--handoff 不过"""
        self.assertEqual(run(self.case('need_tbd'))[0], 0)
        self.assertFails('need_tbd', r'plan.md:效果: 「起点」还是「待你定」')

    def test_no_flow(self):
        self.assertFails('no_flow', r'缺「内容流程：」一行', handoff=False)

    def test_bad_points(self):
        self.assertFails('bad_points', r'P1 的要讲的点要按「a. 一点一句<br>b. ……」写', handoff=False)
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        write(path, read(path).replace('<br>b. 是谁做的', '<br>c. 是谁做的'))
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('P1 的要讲的点要从 a 起按顺序编：现在是 a、c', out)

    def test_uncovered(self):
        """要讲的点没有一条信息对应：--handoff 报错"""
        self.assertEqual(run(self.case('uncovered'))[0], 0)
        self.assertFails('uncovered', r'P2 的「a」在 content.md 里没有对应的信息')

    def test_shared_counts(self):
        """「（P2 b 也用）」算作 P2 的 b；去掉以后 P2 b 没有信息"""
        d = self.case('ok')
        path = os.path.join(d, 'content.md')
        write(path, read(path).replace('（P2 b 也用）', ''))
        code, out = run(d, True)
        self.assertEqual(code, 1)
        self.assertIn('P2 的「b」在 content.md 里没有对应的信息', out)
        write(path, read(path).replace('| P1-3 | b |', '| P1-3 | b（P2 也用） |'))
        self.assertEqual(run(d, True)[0], 1)   # 没写字母的「也用」不算作哪一点
        self.assertEqual(run(d)[0], 0)

    def test_wrong_letter(self):
        self.assertFails('wrong_letter', r'P1-1 讲的「c」不在 P1 的要讲的点里', handoff=False)

    def test_bad_section(self):
        self.assertFails('bad_section', r'content.md:P7 收尾: 段 P7 在 plan.md 的框架里没有', handoff=False)

    def test_wrong_prefix(self):
        self.assertFails('wrong_prefix', r'编号格式不对：P1-4（这一节写 P2-1、P2-2）', handoff=False)

    def test_shared_missing(self):
        self.assertFails('shared_missing', r'P1-3 写了「P7 也用」，P7 在框架里没有', handoff=False)

    def test_no_frame_confirm(self):
        self.assertEqual(run(self.case('no_frame_confirm'))[0], 0)
        code, out = run(self.case('no_frame_confirm'), True)
        self.assertEqual(code, 1)
        self.assertIn('没有「框架」一行', out)
        self.assertNotIn('没有「效果」一行', out)

    def test_auto_confirm(self):
        """合并第 1、2 步：确认记录写「自动，未问用户」也算"""
        self.assertEqual(run(self.case('auto_confirm'), True), (0, '通过\n'))

    def test_confirm_with_note(self):
        """「效果」后面带括注也算（回放写「效果（回放模拟）：」）；认不出的行报错"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path)
        write(path, text.replace('2026-11-09 效果：', '2026-11-09 效果（演示用）：'))
        self.assertEqual(run(d, True), (0, '通过\n'))
        write(path, text.replace('2026-11-09 效果：', '2026-11-09 需求：'))
        code, out = run(d, True)
        self.assertEqual(code, 1)
        self.assertIn('这一行认不出是哪种确认', out)
        self.assertIn('没有「效果」一行', out)

    def test_bad_enum(self):
        code, out = run(self.case('bad_enum'))
        self.assertEqual(code, 1)
        self.assertIn('Q1 的归谁「美术」', out)
        self.assertIn('Q1 的提出于「阶段 1」要取 下游 / 第 1 步 / 第 2 步 / 第 3 步', out)
        self.assertIn('状态「阶段 2 补齐中」要取', out)

    def test_example_handoff(self):
        code, out = run(os.path.join(SKILL, 'example'), True)
        self.assertEqual((code, out.strip()), (0, '通过'))

    def test_template_only_notes(self):
        """刚复制的模板：普通检查没有错，只有占位提示；--handoff 不通过"""
        for f in ('plan.md', 'content.md'):
            shutil.copy(os.path.join(SKILL, 'templates', f), self.tmp)
        code, out = run(self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn('占位没填', out)
        self.assertEqual(run(self.tmp, True)[0], 1)

    def test_missing_file(self):
        shutil.copy(os.path.join(FIX, 'ok', 'plan.md'), self.tmp)
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn('content.md: 文件不存在', out)

    def test_first_step_without_content(self):
        """「效果待确认」时还没建 content.md：只提示；别的状态、--handoff 照样报错"""
        path = os.path.join(self.tmp, 'plan.md')
        write(path, read(os.path.join(FIX, 'ok', 'plan.md')).replace('状态：已交接', '状态：效果待确认'))
        code, out = run(self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn('content.md: 还没建', out)
        self.assertEqual(run(self.tmp, True)[0], 1)

    def test_extent(self):
        p = check.parse_extent
        self.assertEqual(p('45 秒'), ('时间', 45, 45))
        self.assertEqual(p('40–50 秒'), ('时间', 40, 50))
        self.assertEqual(p('1 分 30 秒'), ('时间', 90, 90))
        self.assertEqual(p('2 分钟'), ('时间', 120, 120))
        self.assertEqual(p('1 分钟 30 秒'), ('时间', 90, 90))
        self.assertEqual(p('约 45 秒'), ('时间', 45, 45))
        self.assertEqual(p('45 秒左右'), ('时间', 45, 45))
        self.assertEqual(p('3 页'), ('页', 3, 3))
        self.assertEqual(p('2–4 页'), ('页', 2, 4))
        self.assertEqual(p('1500 字'), ('字', 1500, 1500))
        self.assertEqual(p('3 千字'), ('字', 3000, 3000))
        self.assertEqual(p('不限'), ('不限', 0, 0))
        self.assertIsNone(p('四十秒'))
        self.assertIsNone(p('45'))

    def test_duration_total_note(self):
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        write(path, read(path).replace('20 秒；16:9', '60 秒；16:9'))
        code, out = run(d)
        self.assertEqual(code, 0)
        self.assertIn('相差超过 15%', out)

    def test_model_names_not_refs(self):
        """规定格子以外的「华为 P40」「2026 年 Q1」「P9-9」是正文，不当引用"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path).replace('| 背景故事 | 延后 | 时长不够 |', '| 华为 P40、仰望 U9 的对比 | 删除 | 2026 年 Q1 的旧闻，P9-9 |')
        text = text.replace('a. 某日发生某事', 'a. 某日发生某事，对比华为 P40')
        write(path, text)
        for handoff in (False, True):
            code, out = run(d, handoff)
            self.assertEqual((code, out.strip()), (0, '通过'))

    def test_scoped_refs_still_checked(self):
        """规定的格子里写了不存在的编号照样报：作用的 P、缺口「段」的 P"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path).replace('收尾，承接 P1', '收尾，承接 P7').replace('| Q1 | P1 |', '| Q1 | P8 |')
        write(path, text)
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('plan.md:框架: 引用的段 P7 在框架里没有', out)
        self.assertIn('plan.md:缺口: 引用的段 P8 在框架里没有', out)

    def test_whole_gap(self):
        """归下游的缺口，「段」可以写「全部」；空着不行"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        write(path, read(path).replace('| Q1 | P1 | 现场照片一张 |', '| Q1 | 全部 | 品牌标识 |'))
        self.assertEqual(run(d, True)[0], 0)
        write(path, read(path).replace('| Q1 | 全部 | 品牌标识 |', '| Q1 | | 品牌标识 |'))
        code, out = run(d, True)
        self.assertEqual(code, 1)
        self.assertIn('Q1 归下游，要写清缺什么、哪段', out)

    def test_format_line(self):
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        write(path, read(path).replace('格式：ai-content-planner/3\n', ''))
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('找不到格式行', out)

    def test_pages_and_words(self):
        """篇幅用页、字：单位和目标一致就比合计；各段单位不一致只提示"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path).replace('| 视频 | 用户定 |', '| PPT | 用户定 |').replace('20 秒；16:9', '6 页；16:9')
        text = text.replace('| 8–10 秒 |', '| 3 页 |').replace('| 10 秒 |', '| 3 页 |')
        write(path, text)
        self.assertEqual(run(d, True), (0, '通过\n'))
        write(path, text.replace('| 6 页；16:9', '| 20 页；16:9'))
        code, out = run(d)
        self.assertEqual(code, 0)
        self.assertIn('各段合计 6 页，和目标篇幅 20 页 相差超过 15%', out)
        write(path, text.replace('| 3 页 |', '| 800 字 |', 1))
        code, out = run(d)
        self.assertEqual(code, 0)
        self.assertIn('各段篇幅单位不一致', out)

    # ---------- 格式 3：效果、形式、打法、自查、说法、衍生、受众、素材、约束 ----------
    def edit(self, fname, *pairs):
        d = self.case('ok')
        path = os.path.join(d, fname)
        text = read(path)
        for a, b in pairs:
            self.assertIn(a, text)
            text = text.replace(a, b)
        write(path, text)
        return d

    def test_blocks_numbered(self):
        d = self.edit('plan.md', ('① 跟我有什么关系<br>② 以后还有下文吗', '跟我有什么关系'))
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('阻力要按强弱编号', out)

    def test_play_table(self):
        """打法：正好一行「选」；抓的阻力要在效果里；只有一个打法提示"""
        code, out = run(self.edit('plan.md', ('| 慢 | |', '| 慢 | 选 |')))
        self.assertEqual(code, 1)
        self.assertIn('打法表要正好一行「选」写「选」，现在 2 行', out)
        code, out = run(self.edit('plan.md', ('| B 先问后答 | ② |', '| B 先问后答 | ③ |')))
        self.assertIn('打法「B 先问后答」写了「③」，效果的阻力里没有这一条', out)
        code, out = run(self.edit('plan.md', ('| B 先问后答 | ② | 无 | 一个问题 | 慢 | |\n', '')))
        self.assertEqual(code, 0, out)
        self.assertIn('只有一个打法', out)
        code, out = run(self.edit('plan.md', ('一句话主线：', '主线：')))
        self.assertIn('缺「一句话主线：」一行', out)

    def test_form_basis(self):
        code, out = run(self.edit('plan.md', ('| 结构 | 先事后下一步 | 终点 |', '| 结构 | 先事后下一步 | |')))
        self.assertEqual(code, 1)
        self.assertIn('「结构」的「由哪条效果推出」空着', out)

    def test_frame_audience(self):
        """受众要有「→」；「到」写成知道 X 只提示；怎么证明不能空"""
        code, out = run(self.edit('plan.md', ('「以后呢」→ 记下某月', '记下某月')))
        self.assertEqual(code, 1)
        self.assertIn('P2 的受众要写「原来的念头 → 看完这段的念头或动作」', out)
        code, out = run(self.edit('plan.md', ('「以后呢」→ 记下某月', '「以后呢」→ 知道下一步在某月')))
        self.assertEqual(code, 0, out)
        self.assertIn('P2 的受众「到」以「知道下」开头', out)
        code, out = run(self.edit('plan.md', ('| 时间上屏 |', '| |')))
        self.assertIn('P2 的「怎么证明」空着', out)

    def test_empty_words(self):
        code, out = run(self.edit('plan.md', ('| 终点 | 记下下一步的月份 |', '| 终点 | 引发共鸣 |')))
        self.assertEqual(code, 0, out)
        self.assertIn('「终点」写了「引发共鸣」', out)

    def test_self_check(self):
        code, out = run(self.edit('plan.md', ('| 阻力 | ① → P1；② → P2 |', '| 阻力 | ① → P1 |')))
        self.assertEqual(code, 1)
        self.assertIn('阻力② 没写由哪段回应', out)
        code, out = run(self.edit('plan.md', ('| 终点 | P2 |', '| 终点 | 结尾 |')))
        self.assertIn('终点一行要写落在哪段', out)
        code, out = run(self.edit('plan.md', ('| 衍生 | P1、P2 |', '| 衍生 | P1、P5 |')))
        self.assertIn('plan.md:效果自查: 引用的段 P5 在框架里没有', out)

    def test_say(self):
        """说法：点要在框架里；不能丢的引用要存在；交接时每段至少一行"""
        code, out = run(self.edit('plan.md', ('| P2 a | 记下月份 |', '| P2 c | 记下月份 |')))
        self.assertEqual(code, 1)
        self.assertIn('点「P2 c」的「c」不在 P2 的要讲的点里', out)
        code, out = run(self.edit('plan.md', ('| P1-1；K1 |', '| P1-9；K7；M4 |')))
        self.assertIn('plan.md:说法: 引用的 P1-9 在 content.md 里没有', out)
        self.assertIn('引用的 K7 在 content.md 的约束表里没有', out)
        self.assertIn('引用的 M4 在 content.md 的素材表里没有', out)
        d = self.edit('plan.md', ('| P2 a | 记下月份 | 「下一步，某月。」 | P2-1；Q2 |\n', ''))
        self.assertEqual(run(d)[0], 0)
        code, out = run(d, True)
        self.assertIn('P2 没有说法：每段至少一行', out)

    def test_spin(self):
        """衍生：形式写了「无」就只写「无」；形式有衍生，节里不能写「无」；交接时要有行"""
        d = self.edit('plan.md', ('| 衍生 | 拆一条 10 秒 |', '| 衍生 | 无 |'))
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('形式的衍生写了「无」，这一节就只写「无」', out)
        d = self.edit('plan.md', ('| 衍生 | 拆一条 10 秒 |', '| 衍生 | 无 |'),
                      ('| 条 | 用哪些点 | 第一句 | 放在哪 |\n|---|---|---|---|\n| D1 | P1 a、P2 a | 「某日，某事。」 | 10 秒短片 |', '无'))
        self.assertEqual(run(d, True), (0, '通过\n'))
        d = self.edit('plan.md', ('| 条 | 用哪些点 | 第一句 | 放在哪 |\n|---|---|---|---|\n| D1 | P1 a、P2 a | 「某日，某事。」 | 10 秒短片 |', '无'))
        code, out = run(d)
        self.assertIn('形式的衍生是「拆一条 10 秒」，这一节不能写「无」', out)
        code, out = run(self.edit('plan.md', ('| D1 | P1 a、P2 a |', '| E1 | P1 a、P3 a |')))
        self.assertIn('编号格式不对：E1（写 D1、D2）', out)
        self.assertIn('E1 的用哪些点「P1 a、P3 a」的段 P3 在框架里没有', out)

    def test_assets(self):
        code, out = run(self.edit('content.md', ('| 裁后用：裁掉水印 | 能 |', '| 随便 | 可以 |')))
        self.assertEqual(code, 1)
        self.assertIn('M1 的能怎么用「随便」要取', out)
        self.assertIn('M1 的能不能送生成「可以」要取', out)
        d = self.edit('content.md', ('| 裁后用：裁掉水印 | 能 |', '| 只作参考 | 〔待核实〕：授权没写 |'))
        code, out = run(d, True)
        self.assertEqual(code, 0, out)
        self.assertIn('M1 能不能送生成还没核实，下游按「不能」处理', out)
        code, out = run(self.edit('content.md', ('| 能 | P1 |', '| 能 | P4 |')))
        self.assertIn('content.md:素材: 引用的段 P4 在框架里没有', out)
        code, out = run(self.edit('content.md', ('| F2 | M1 |', '| F2 | M3 |')))
        self.assertIn('content.md: 引用的 M3 在 content.md 的素材表里没有', out)
        code, out = run(self.edit('content.md', ('| M1 | https', '| X1 | https')))
        self.assertIn('content.md:素材: 编号格式不对：X1（写 M1、M2）', out)

    def test_rules(self):
        d = self.edit('content.md', ('| M1 | 已核实 |', '| M1 | 〔待核实〕 |'))
        self.assertEqual(run(d)[0], 0)
        code, out = run(d, True)
        self.assertEqual(code, 1)
        self.assertIn('K1 还是「〔待核实〕」：约束要已核实或是设定才能交接', out)
        code, out = run(self.edit('content.md', ('| K1 | 现场的旗是蓝色的 | M1 |', '| K1 | 现场的旗是蓝色的 | M2、P1-8 |')))
        self.assertIn('content.md:约束: 引用的 M2 在 content.md 的素材表里没有', out)
        self.assertIn('content.md:约束: 引用的 P1-8 在 content.md 里没有', out)
        code, out = run(self.edit('plan.md', ('现场照片 M1，照 K1', '现场照片 M1，照 K2')))
        self.assertIn('plan.md:框架: 引用的 K2 在 content.md 的约束表里没有', out)

    def test_voices(self):
        code, out = run(self.edit('content.md', ('| C6 | 某平台评论区 · 2026-11-09 · 抽 20 条里 6 条这么说 | ① |', '| C6 | 某平台评论区 · 2026-11-09 · 抽 20 条里 6 条这么说 | ③ |')))
        self.assertEqual(code, 1)
        self.assertIn('V1 的对应哪条阻力写了「③」，效果的阻力里没有这一条', out)

    def test_missing_new_sections(self):
        code, out = run(self.edit('content.md', ('## 约束', '## 限制')))
        self.assertEqual(code, 1)
        self.assertIn('content.md:约束: 缺这一节', out)
        code, out = run(self.edit('plan.md', ('## 效果自查', '## 自查')))
        self.assertIn('plan.md:效果自查: 缺这一节', out)


class DocsTest(unittest.TestCase):
    def test_formats_match_template(self):
        """formats.md 的表：每种形式都写了篇幅单位和交给谁；形式名和模板需求「输出形式」的选项一致"""
        text = read(os.path.join(SKILL, 'formats.md'))
        t = check.find_table(text.split('\n'), ['输出形式', '篇幅单位', '交给谁'])
        self.assertTrue(t)
        for row in t[1]:
            self.assertTrue(row['篇幅单位'] and row['交给谁'], row)
        tpl = read(os.path.join(SKILL, 'templates', 'plan.md'))
        m = re.search(r'^\| 输出形式和规格 \| 〔([^；〕]+)', tpl, re.M)
        self.assertTrue(m)
        self.assertEqual([x.strip() for x in m.group(1).split('/')], [row['输出形式'] for row in t[1]])


if __name__ == '__main__':
    unittest.main()
