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
        """格式 3 报错，提示照 handoff.md 第 7 节转；更早的按 CHANGELOG；都不再往下查"""
        code, out = run(self.case('old_format'))
        self.assertEqual(code, 1)
        self.assertIn('本脚本只认 ai-content-planner/4；这是旧格式，照本 Skill 的 handoff.md 第 7 节转成格式 4', out)
        self.assertEqual(out.count('\n'), 2, out)
        path = os.path.join(self.tmp, 'plan.md')
        write(path, read(path).replace('ai-content-planner/3', 'ai-content-planner/2'))
        self.assertIn('按本 Skill 的 CHANGELOG.md 一版一版转成格式 4', run(self.tmp)[1])

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
        write(path, read(path).replace('格式：ai-content-planner/4\n', ''))
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
        code, out = run(self.edit('plan.md', ('| 表达 | 结果前置，3 秒念完；张力 2，全片没有感叹号；边界查过 |\n', '')))
        self.assertIn('效果自查要正好是这6项', out)

    def test_say(self):
        """说法：点要在框架里；不能丢的引用要存在；交接时每段至少一行"""
        code, out = run(self.edit('plan.md', ('| P2 a | 记下月份 |', '| P2 c | 记下月份 |')))
        self.assertEqual(code, 1)
        self.assertIn('点「P2 c」的「c」不在 P2 的要讲的点里', out)
        code, out = run(self.edit('plan.md', ('| 原句；P1-1；K1 |', '| 原句；P1-9；K7；M4 |')))
        self.assertIn('plan.md:说法: 引用的 P1-9 在 content.md 里没有', out)
        self.assertIn('引用的 K7 在 content.md 的约束表里没有', out)
        self.assertIn('引用的 M4 在 content.md 的素材表里没有', out)
        d = self.edit('plan.md', ('| P2 a | 记下月份 | 「下一步在某月。还是同一家机构、同一支队伍来做，记下这个月份。」 | 原句；P2-1；Q2 |\n', ''))
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

    # ---------- 格式 4：表达、画面、制作条件、说法的字数和原句 ----------
    def test_tone(self):
        """表达：六项；基调是一档或「自定：」；局部档的段要在框架里；张力 1–3；前三项要写推出自哪条效果"""
        code, out = run(self.edit('plan.md', ('| 基调 | 冷静播报 |', '| 基调 | 轻松活泼 |')))
        self.assertEqual(code, 1)
        self.assertIn('基调「轻松活泼」要以 tone.md 的一档开头', out)
        self.assertEqual(run(self.edit('plan.md', ('| 基调 | 冷静播报 |', '| 基调 | 自定：像老师傅讲手艺 |')), True), (0, '通过\n'))
        self.assertEqual(run(self.edit('plan.md', ('| 基调 | 冷静播报 |', '| 基调 | 冷静播报；P2 换讲透型 |')), True), (0, '通过\n'))
        code, out = run(self.edit('plan.md', ('| 基调 | 冷静播报 |', '| 基调 | 冷静播报；P5 换讲透型 |')))
        self.assertIn('plan.md:表达: 引用的段 P5 在框架里没有', out)
        code, out = run(self.edit('plan.md', ('| 张力 | 2：', '| 张力 | 中等：')))
        self.assertIn('张力要以 1、2、3 开头', out)
        code, out = run(self.edit('plan.md', ('| 钩子 | 结果前置：第一句就说某事做成了 | 阻力① |', '| 钩子 | 结果前置：第一句就说某事做成了 | |')))
        self.assertIn('「钩子」的「由哪条效果推出」空着', out)
        code, out = run(self.edit('plan.md', ('| 句式和节奏 | 一句一个信息；', '| 句式和节奏 | 口语化一点；')))
        self.assertEqual(code, 0, out)
        self.assertIn('「句式和节奏」写了「口语化」', out)
        code, out = run(self.edit('plan.md', ('| 边界 | 只讲公告写的 | 杠杆 | 建议 |\n', '')))
        self.assertIn('表达要正好是这6项', out)
        d = self.edit('plan.md', ('| 情绪曲线 | 好奇 → P1 停下 → 收在记住月份 | 终点 | 建议 |', '| 情绪曲线 | 待你定 | 终点 | 待你定 |'))
        self.assertEqual(run(d)[0], 0)
        self.assertIn('「情绪曲线」还是「待你定」', run(d, True)[1])
        d = self.edit('plan.md', ('| 边界 | 只讲公告写的 |', '| 边界 | |'))
        self.assertIn('「边界」空着：表达六项都写了才能交接', run(d, True)[1])

    def test_make_terms(self):
        """制作条件写成「能用：……；不能用：……」；画面来源不能在「不能用」里"""
        code, out = run(self.edit('plan.md', ('| 制作条件 | 能用：照片、代码画；不能用：生图、生视频 |', '| 制作条件 | 无真人 |')))
        self.assertEqual(code, 1)
        self.assertIn('「制作条件」要写成「能用：……；不能用：……」', out)
        code, out = run(self.edit('plan.md', ('不能用：生图、生视频 |', '不能用：照片、生视频 |')))
        self.assertIn('H1 的来源是「照片」，形式的制作条件写了不能用', out)
        self.assertEqual(run(self.edit('plan.md', ('能用：照片、代码画；', '能用：照片、代码画、生图：只出手；')))[0], 0)

    def test_shots(self):
        """画面：表头、编号、段号、来源取值、用到的编号要存在"""
        code, out = run(self.edit('plan.md', ('| # | 段 | 要看到什么 | 来源 | 用到 |', '| # | 段 | 画面 | 来源 | 用到 |')))
        self.assertEqual(code, 1)
        self.assertIn('画面表表头要正好是', out)
        code, out = run(self.edit('plan.md', ('| H2 | P2 |', '| H1 | P2 |')))
        self.assertIn('plan.md:画面: 编号重复：H1', out)
        code, out = run(self.edit('plan.md', ('| H2 | P2 |', '| X2 | P2 |')))
        self.assertIn('编号格式不对：X2（写 H1、H2）', out)
        code, out = run(self.edit('plan.md', ('| H2 | P2 |', '| H2 | P2、P1 |')))
        self.assertIn('H2 的段「P2、P1」只写一个段号', out)
        code, out = run(self.edit('plan.md', ('| H2 | P2 |', '| H2 | P4 |')))
        self.assertIn('H2 的段 P4 在框架里没有', out)
        code, out = run(self.edit('plan.md', ('| 代码画 |', '| 动画 |')))
        self.assertIn('H2 的来源「动画」要取 代码画 / 照片', out)
        code, out = run(self.edit('plan.md', ('| M1、K1 |', '| M3、K1、Q9 |')))
        self.assertIn('plan.md:画面: 引用的 M3 在 content.md 的素材表里没有', out)
        self.assertIn('plan.md:画面: 引用的 Q9 在缺口表里没有', out)
        code, out = run(self.edit('plan.md', ('| P2-1、P2 a |', '| P2-1、P2 c |')))
        self.assertIn('H2 用到「P2 c」，「c」不在 P2 的要讲的点里', out)

    def test_shot_grounding(self):
        """画面的「用到」按来源要有着落"""
        code, out = run(self.edit('plan.md', ('| P2-1、P2 a |', '| K1 |')))
        self.assertEqual(code, 1)
        self.assertIn('H2 是代码画，「用到」要有它画的信息（P1-1）或上屏的说法点（P1 a）', out)
        self.assertEqual(run(self.edit('plan.md', ('| P2-1、P2 a |', '| P2 a |')))[0], 0)
        code, out = run(self.edit('plan.md', ('| M1、K1 |', '| K1、Q2 |')))
        self.assertIn('H1 是照片，「用到」要有素材 M，或归下游的缺口 Q', out)   # Q2 归策划，不算
        self.assertEqual(run(self.edit('plan.md', ('| M1、K1 |', '| Q1 |')))[0], 0)
        code, out = run(self.edit('plan.md', ('| 代码画 | P2-1、P2 a |', '| 数据 | P2 a |')))
        self.assertIn('H2 是数据，「用到」要有数据本身（P1-1）或数据文件（M1）', out)
        code, out = run(self.edit('plan.md', ('| 代码画 | P2-1、P2 a |', '| 录屏 | 某个界面 |')))
        self.assertIn('H2 的「用到」要写编号', out)

    def test_generated(self):
        """生图、生视频：至少一条 K；用到的 M 不能是「不能」送生成，〔待核实〕提示"""
        d = self.edit('plan.md', ('| 照片 | M1、K1 |', '| 生图 | M1 |'), ('不能用：生图、生视频', '不能用：生视频'))
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('H1 是生图，「用到」至少要有一条约束 K', out)
        d = self.edit('plan.md', ('| 照片 | M1、K1 |', '| 生图 | M1、K1 |'), ('不能用：生图、生视频', '不能用：生视频'))
        self.assertEqual(run(d)[0], 0)
        cpath = os.path.join(d, 'content.md')
        write(cpath, read(cpath).replace('| 裁后用：裁掉水印 | 能 |', '| 裁后用：裁掉水印 | 不能：有人脸 |'))
        self.assertIn('H1 是生图，用到的 M1 不能送生成', run(d)[1])
        write(cpath, read(cpath).replace('| 不能：有人脸 |', '| 〔待核实〕 |'))
        code, out = run(d)
        self.assertEqual(code, 0, out)
        self.assertIn('H1 是生图，用到的 M1 能不能送生成还没核实', out)

    def test_shot_per_segment(self):
        """每段至少一行画面：平时提示，--handoff 报错"""
        d = self.edit('plan.md', ('| H2 | P2 | 「下一步，某月」上屏 | 代码画 | P2-1、P2 a |\n', ''))
        code, out = run(d)
        self.assertEqual(code, 0, out)
        self.assertIn('P2 没有画面：每段至少一行（提示）', out)
        code, out = run(d, True)
        self.assertEqual(code, 1)
        self.assertIn('P2 没有画面：每段至少一行', out)

    def test_asset_unused(self):
        """要用的 M 没有画面行用到：提示"""
        code, out = run(self.edit('plan.md', ('| 照片 | M1、K1 |', '| 照片 | Q1、K1 |')))
        self.assertEqual(code, 0, out)
        self.assertIn('M1 要用（P1），但画面表没有一行用到它', out)

    def test_say_length(self):
        """有旁白的视频：每段说法按每秒 2.5–5 字提示；单句超过 40 字提示；没有旁白不查"""
        code, out = run(self.edit('plan.md', ('「下一步在某月。还是同一家机构、同一支队伍来做，记下这个月份。」', '「下一步，某月。」')))
        self.assertEqual(code, 0, out)
        self.assertIn('P2 的说法 5 字，篇幅 10 秒按每秒 2.5–5 字该是 25–50 字', out)
        long_ = '「某日，某机构在某地做成了某事，现场照片里那面旗是蓝色的，大家都看见了那面旗。」'
        code, out = run(self.edit('plan.md', ('「某日，某机构在某地做成了某事。现场照片就在这里，旗是蓝色的。」', long_)))
        self.assertNotIn('有一句', out)   # 37 字不超
        long_ = '「某日，某机构在某地做成了某事，现场照片里那面旗是蓝色的，大家都看见了那面旗，也都记住了那一天发生的事。」'
        code, out = run(self.edit('plan.md', ('「某日，某机构在某地做成了某事。现场照片就在这里，旗是蓝色的。」', long_)))
        self.assertRegex(out, r'「P1 a、b」有一句 4\d 字，口播单句不超过 40 字')
        d = self.edit('plan.md', ('「下一步在某月。还是同一家机构、同一支队伍来做，记下这个月份。」', '「下一步，某月。」'),
                      ('| 声音 | 旁白，第三人称 |', '| 声音 | 不说话，只上字 |'))
        self.assertNotIn('的说法 5 字', run(d)[1])

    def test_original(self):
        """有旁白或上字的视频：第一行和终点那段的说法要写「原句」，--handoff 报错、平时提示"""
        d = self.edit('plan.md', ('| 原句；P1-1；K1 |', '| P1-1；K1 |'))
        code, out = run(d)
        self.assertEqual(code, 0, out)
        self.assertIn('第一行（开头的钩子句）的说法要在「不能丢的」写「原句」', out)
        self.assertEqual(run(d, True)[0], 1)
        d = self.edit('plan.md', ('| 原句；P2-1；Q2 |', '| P2-1；Q2 |'))
        self.assertIn('终点 P2 那段的说法要在「不能丢的」写「原句」', run(d, True)[1])
        d = self.edit('plan.md', ('| 原句；P2-1；Q2 |', '| P2-1；Q2 |'), ('| 视频 | 用户定 |', '| 图文 | 用户定 |'))
        self.assertNotIn('原句', run(d, True)[1])

    def test_extreme_words_allowed(self):
        """极限词不再提示（维护者 2026-11-18 定）：事实要有依据照「夸张不用在事实上」，靠写的人判断"""
        a = '旗是蓝色的。」'
        self.assertEqual(run(self.edit('plan.md', (a, '旗是全网最蓝的，行业第一。」')))[1], '通过\n')

    def test_make_limits(self):
        """制作条件的限制写在括号里，括号里有逗号也不拆；拆出来不是画面来源的提示"""
        cell = '| 制作条件 | 能用：照片、代码画；不能用：生图、生视频 |'
        out = run(self.edit('plan.md', (cell, '| 制作条件 | 能用：照片（只用公开的，标出处）、代码画；不能用：生图、生视频 |')))[1]
        self.assertEqual(out, '通过\n')
        code, out = run(self.edit('plan.md', (cell, '| 制作条件 | 能用：照片：只用公开的，标出处、代码画；不能用：生图、生视频 |')))
        self.assertEqual(code, 0, out)
        self.assertIn('「制作条件」里的「标出处」不是画面来源的名字', out)

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
