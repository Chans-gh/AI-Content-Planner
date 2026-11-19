"""check.py 的离线测试。运行：python3 -m unittest discover -s skills/ai-content-planner/scripts/tests

fixtures/ok/ 是一份全通过的（格式 5）；fixtures/ep05_flaws/ 照 ep05 复盘的四处毛病写（内容自拟）。
别的情况都在测试里改 ok/ 的一处再查。
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
        self.dir = os.path.join(self.tmp, 'demo')
        os.makedirs(self.dir)

    def case(self, name='ok'):
        for f in os.listdir(os.path.join(FIX, name)):
            shutil.copy(os.path.join(FIX, name, f), self.dir)
        return self.dir

    def edit(self, fname, *pairs):
        """ok/ 复制一份，按 (原文, 改成) 改 fname"""
        d = self.case()
        path = os.path.join(d, fname)
        text = read(path)
        for a, b in pairs:
            self.assertIn(a, text)
            text = text.replace(a, b)
        write(path, text)
        return d

    def fails(self, d, pattern, handoff=False):
        code, out = run(d, handoff)
        self.assertEqual(code, 1, out)
        self.assertRegex(out, pattern)
        return out

    def notes(self, d, pattern, handoff=False):
        code, out = run(d, handoff)
        self.assertEqual(code, 0, out)
        self.assertRegex(out, pattern)
        return out

    def passes(self, d, handoff=True):
        self.assertEqual(run(d, handoff), (0, '通过\n'))

    # ---------- 全通过的 ----------
    def test_ok(self):
        for handoff in (False, True):
            self.passes(os.path.join(FIX, 'ok'), handoff)

    def test_example_handoff(self):
        self.passes(os.path.join(SKILL, 'example'))

    def test_template_only_notes(self):
        """刚复制的模板：普通检查没有错，只有占位提示；--handoff 不通过"""
        for f in ('plan.md', 'content.md'):
            shutil.copy(os.path.join(SKILL, 'templates', f), self.dir)
        code, out = run(self.dir)
        self.assertEqual(code, 0, out)
        self.assertIn('占位没填', out)
        self.assertEqual(run(self.dir, True)[0], 1)

    def test_ep05_flaws(self):
        """ep05 的四处毛病，--handoff 都要报出来：取舍保留没落点、信息没有去向、原句撞红线的词、待核实没关"""
        d = self.case('ep05_flaws')
        code, out = run(d, True)
        self.assertEqual(code, 1, out)
        self.assertIn('「以公告为准的提示」是「保留」，「落在」要写落在哪句', out)
        self.assertIn('P2-1 的去向空着', out)
        self.assertIn('S1 用了红线 B2 的词「首次」', out)
        self.assertIn('P1-2 还「待处理」', out)

    # ---------- 文件、格式行、状态行、节 ----------
    def test_missing_file(self):
        shutil.copy(os.path.join(FIX, 'ok', 'plan.md'), self.dir)
        self.fails(self.dir, 'content.md: 文件不存在')

    def test_research_md_hint(self):
        shutil.copy(os.path.join(FIX, 'ok', 'plan.md'), self.dir)
        shutil.copy(os.path.join(FIX, 'ok', 'content.md'), os.path.join(self.dir, 'research.md'))
        self.fails(self.dir, 'research.md 改名 content.md')

    def test_old_format(self):
        """格式 4（格式行在 plan.md）报错，提示照 handoff.md 第 7 节转；更早的按 CHANGELOG；都不再往下查"""
        d = self.edit('content.md', ('格式：ai-content-planner/5\n', ''))
        p = os.path.join(d, 'plan.md')
        write(p, read(p).replace('格式和状态见 content.md', '格式：ai-content-planner/4\n状态：已交接（2026-11-09）。'))
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('本脚本只认 ai-content-planner/5；照本 Skill 的 handoff.md 第 7 节转成格式 5', out)
        self.assertEqual(out.count('\n'), 2, out)
        write(p, read(p).replace('ai-content-planner/4', 'ai-content-planner/3'))
        self.assertIn('按本 Skill 的 CHANGELOG.md 一版一版转成格式 5', run(d)[1])

    def test_format_line(self):
        self.fails(self.edit('content.md', ('格式：ai-content-planner/5\n', '')), '找不到格式行')
        self.fails(self.edit('content.md', ('ai-content-planner/5', 'ai-content-planner/9')), '格式是「ai-content-planner/9」')

    def test_plan_second_line(self):
        """plan.md 不写格式、状态，第二行写「格式和状态见 content.md」"""
        self.fails(self.edit('plan.md', ('格式和状态见 content.md', '状态：已交接（2026-11-09）。')), '状态行只写在 content.md')
        self.fails(self.edit('plan.md', ('格式和状态见 content.md', '')), '标题下第一行写「格式和状态见 content.md」')

    def test_status(self):
        self.fails(self.edit('content.md', ('状态：已交接', '状态：阶段 2 补齐中')), '状态「阶段 2 补齐中」要取')
        self.fails(self.edit('content.md', ('状态：已交接（2026-11-09）。下一步转分镜。\n', '')), '找不到状态行')
        self.notes(self.edit('content.md', ('状态：已交接', '状态：补齐中')), '交接时改成「已交接」', True)

    def test_sections(self):
        self.fails(self.edit('content.md', ('## 约束', '## 限制')), 'content.md:约束: 缺这一节')
        self.fails(self.edit('plan.md', ('## 效果自查', '## 自查')), 'plan.md:效果自查: 缺这一节')
        c = read(os.path.join(FIX, 'ok', 'content.md'))
        red = c[c.index('## 红线'):c.index('## 约束')]
        self.fails(self.edit('content.md', (red, ''), ('## P1 开场', red + '## P1 开场')), '节的顺序要是 总则、红线、约束')
        p = read(os.path.join(FIX, 'ok', 'plan.md'))
        aud = p[p.index('## 受众'):p.index('## 待核实和有冲突')]
        self.fails(self.edit('plan.md', (aud, ''), ('## 取舍', aud + '## 取舍')), '节的顺序要是 确认记录、需求')

    def test_no_assets_section(self):
        """素材节可以没有；有就要有行"""
        c = read(os.path.join(FIX, 'ok', 'content.md'))
        start, end = c.index('## 素材'), c.index('## 资料清单')
        d = self.edit('content.md', (c[start:end], ''), ('| M1、K1、P1-4 |', '| Q1、K1、P1-4 |'), ('| K1 | 现场的旗是蓝色的 | M1 |', '| K1 | 现场的旗是蓝色的 | P1-4 |'),
                      ('| F2 | M1 |', '| F2 | 某公告附图 |'))
        self.passes(d)
        d = self.edit('content.md', ('| M1 | https://example.com/a.jpg | 现场照片 | 右下角水印 | 裁后用：裁掉水印 | 能 | P1 |\n', ''))
        self.fails(d, '素材节没有行', True)

    # ---------- plan.md：确认记录、需求、效果、立意、自查、取舍、缺口、受众、待核实 ----------
    def test_confirms(self):
        d = self.edit('plan.md', ('- 2026-11-09 框架：选打法 A，两段，先讲发生了什么，再讲接下来看什么。\n', ''))
        self.assertEqual(run(d)[0], 0)
        out = self.fails(d, '没有「框架」一行', True)
        self.assertNotIn('没有「效果」一行', out)
        self.passes(self.edit('plan.md', ('2026-11-09 效果：', '2026-11-09 效果（演示用）：')))
        self.passes(self.edit('plan.md', ('2026-11-09 效果：用户确认终点、阻力和 20 秒视频。', '2026-11-09 效果：自动，未问用户（用户说直接做）'),
                              ('2026-11-09 框架：选打法 A，两段，先讲发生了什么，再讲接下来看什么。', '2026-11-09 框架：自动，未问用户（同上）')))
        d = self.edit('plan.md', ('2026-11-09 效果：', '2026-11-09 需求：'))
        out = self.fails(d, '这一行认不出是哪种确认', True)
        self.assertIn('没有「效果」一行', out)

    def test_need_effect_rows(self):
        self.fails(self.edit('plan.md', ('| 品牌与风格 | 无 | 用户给的 |\n', '')), '需求要正好是这5项：用途和场景、必须有')
        self.fails(self.edit('plan.md', ('| 衡量 | 无 | | 用户给的 |\n', '| 衡量 | 无 | | 用户给的 |\n| 凭什么信 | 夹具 | | 建议 |\n')), '效果要正好是这6项')
        d = self.edit('plan.md', ('| 起点 | 没听说这件事 | 问来的 | 用户给的 |', '| 起点 | 待你定 | | 待你定 |'))
        self.assertEqual(run(d)[0], 0)
        self.fails(d, 'plan.md:效果: 「起点」还是「待你定」', True)

    def test_blocks(self):
        self.fails(self.edit('plan.md', ('① 跟我有什么关系<br>② 以后还有下文吗', '跟我有什么关系')), '阻力要按强弱编号')
        self.notes(self.edit('plan.md', ('| 终点 | 记下下一步的月份 |', '| 终点 | 引发共鸣 |')), '「终点」写了「引发共鸣」')
        self.fails(self.edit('plan.md', ('| ① | 已核实 |', '| ③ | 已核实 |')), 'V1 的对应哪条阻力写了「③」，效果的阻力里没有这一条')

    def test_play_table(self):
        self.fails(self.edit('plan.md', ('| 慢 | |', '| 慢 | 选 |')), '打法表要正好一行「选」写「选」，现在 2 行')
        self.fails(self.edit('plan.md', ('| B 先问后答 | ② |', '| B 先问后答 | ③ |')), '打法「B 先问后答」写了「③」，效果的阻力里没有这一条')
        self.notes(self.edit('plan.md', ('| B 先问后答 | ② | 无 | 一个问题 | 慢 | |\n', '')), '只有一个打法')
        self.fails(self.edit('plan.md', ('一句话主线：', '主线：')), '缺「一句话主线：」一行')
        self.fails(self.edit('plan.md', ('内容流程：', '流程：')), '缺「内容流程：」一行')

    def test_self_check(self):
        self.fails(self.edit('plan.md', ('| 阻力 | ① → P1；② → P2 |', '| 阻力 | ① → P1 |')), '阻力② 没写由哪段回应')
        self.fails(self.edit('plan.md', ('| 终点 | P2 |', '| 终点 | 结尾 |')), '终点一行要写落在哪段')
        self.fails(self.edit('plan.md', ('| 衍生 | P1、P2 |', '| 衍生 | P1、P5 |')), 'plan.md:效果自查: 引用的段 P5 在 content.md 里没有')
        self.fails(self.edit('plan.md', ('S1 约 3 秒念完', 'S9 约 3 秒念完')), 'plan.md:效果自查: 引用的 S9 在念什么里没有')
        self.fails(self.edit('plan.md', ('| 换题测试 | P2 换题照样成立；P1 不成立 |\n', '')), '效果自查要正好是这6项')

    def test_trades(self):
        """取舍：保留、合并要落在 S、H、B、K；编号要存在；处理的取值"""
        self.fails(self.edit('plan.md', ('| 保留 | S2、K1 |', '| 保留 | 口播带过 |')), '「旗的颜色」是「保留」，「落在」要写')
        self.fails(self.edit('plan.md', ('| 保留 | S2、K1 |', '| 保留 | S9 |')), 'plan.md:取舍: 引用的 S9 在念什么里没有')
        self.fails(self.edit('plan.md', ('| 背景故事 | 延后 |', '| 背景故事 | 以后再说 |')), '处理「以后再说」要取')
        self.fails(self.edit('plan.md', ('| 内容 | 处理 | 落在 | 理由 |', '| 内容 | 处理 | 理由 | 落在 |')), '取舍表表头要正好是')

    def test_gaps(self):
        d = self.edit('plan.md', ('| Q2 | P2 | 下一步的时间 | 策划 | 第 1 步 | 已补 |', '| Q2 | P2 | 下一步的时间 | 策划 | 第 1 步 | 待补 |'))
        self.assertEqual(run(d)[0], 0)
        self.fails(d, 'Q2 归策划、还待补', True)
        self.fails(self.edit('plan.md', ('| 改内容关闭 | 删掉第三段，确认记录里有 |', '| 改内容关闭 |  |')), 'Q3 是「改内容关闭」')
        self.fails(self.edit('plan.md', ('| 已补 | 记成 P2-1 |', '| 已补 | 记成 P2-9 |')), r'plan.md:缺口: 引用的 P2-9 在 content.md 里没有')
        out = self.fails(self.edit('plan.md', ('| Q1 | P1 | 现场照片一张 | 下游 | 第 2 步 |', '| Q1 | P1 | 现场照片一张 | 美术 | 阶段 1 |')), 'Q1 的归谁「美术」')
        self.assertIn('Q1 的提出于「阶段 1」要取 下游 / 第 1 步 / 第 2 步 / 第 3 步', out)
        self.passes(self.edit('plan.md', ('| Q1 | P1 | 现场照片一张 |', '| Q1 | 全部 | 品牌标识 |')))
        self.fails(self.edit('plan.md', ('| Q1 | P1 | 现场照片一张 |', '| Q1 | | 品牌标识 |')), 'Q1 归下游，要写清缺什么、哪段', True)
        self.fails(self.edit('plan.md', ('| Q1 | P1 |', '| Q1 | P8 |')), 'plan.md:缺口: 引用的段 P8 在 content.md 里没有')

    def test_open_items(self):
        """待核实和有冲突：交接前全部已处理、「落在」不空；平时只提示"""
        d = self.edit('plan.md', ('| 不讲 | 已处理 | 无：P1-2 去向「不讲」 |', '| 不讲 | 待处理 | |'))
        self.notes(d, 'P1-2 还「待处理」')
        self.fails(d, 'P1-2 还「待处理」', True)
        self.fails(self.edit('plan.md', ('| 不讲 | 已处理 | 无：P1-2 去向「不讲」 |', '| 不讲 | 已处理 | |')), 'P1-2 的「落在」空着', True)
        self.fails(self.edit('plan.md', ('| 不讲 | 已处理 |', '| 不讲 | 办完了 |')), 'P1-2 的状态「办完了」要取 待处理 / 已处理')
        self.fails(self.edit('plan.md', ('| 无：P1-2 去向「不讲」 |', '| B9 |')), 'plan.md:待核实和有冲突: 引用的 B9 在红线里没有')

    # ---------- 总则 ----------
    def test_general_rows(self):
        self.fails(self.edit('content.md', ('| 语速 | 中 | 默认档 |\n', '')), '总则要正好是这13项')
        self.fails(self.edit('content.md', ('| 结构 | 先事后下一步 | 终点 |', '| 结构 | 先事后下一步 | |')), '「结构」的「依据」空着')
        d = self.edit('content.md', ('| 情绪曲线 | 好奇 → P1 停下 → 收在记住月份 | 终点 |', '| 情绪曲线 | 待你定 | 待你定 |'))
        self.assertEqual(run(d)[0], 0)
        self.fails(d, '「情绪曲线」还是「待你定」', True)
        self.fails(self.edit('content.md', ('| 情绪曲线 | 好奇 → P1 停下 → 收在记住月份 | 终点 |', '| 情绪曲线 | | 终点 |')), '「情绪曲线」空着', True)

    def test_tone(self):
        self.fails(self.edit('content.md', ('| 基调 | 冷静播报 |', '| 基调 | 轻松活泼 |')), '基调「轻松活泼」要以 tone.md 的一档开头')
        self.passes(self.edit('content.md', ('| 基调 | 冷静播报 |', '| 基调 | 自定：像老师傅讲手艺 |')))
        self.passes(self.edit('content.md', ('| 基调 | 冷静播报 |', '| 基调 | 冷静播报；P2 换讲透型 |')))
        self.fails(self.edit('content.md', ('| 基调 | 冷静播报 |', '| 基调 | 冷静播报；P5 换讲透型 |')), 'content.md:总则: 引用的段 P5 在 content.md 里没有')
        self.fails(self.edit('content.md', ('| 张力 | 2：', '| 张力 | 中等：')), '张力要以 1、2、3 开头')
        self.notes(self.edit('content.md', ('| 句式和节奏 | 一句一个信息；', '| 句式和节奏 | 口语化一点；')), '「句式和节奏」写了「口语化」')
        self.fails(self.edit('content.md', ('；见 S1 |', '；见 S7 |')), 'content.md:总则: 引用的 S7 在念什么里没有')

    def test_rate(self):
        """语速：慢 / 中 / 快 / 无；有旁白不能写「无」"""
        self.passes(self.edit('content.md', ('| 语速 | 中 |', '| 语速 | 快 |')))
        self.fails(self.edit('content.md', ('| 语速 | 中 |', '| 语速 | 1.2 倍 |')), '语速写 慢 / 中 / 快')
        self.fails(self.edit('content.md', ('| 语速 | 中 |', '| 语速 | 无 |')), '声音有旁白，语速要写 慢 / 中 / 快')

    def test_make_terms(self):
        cell = '| 制作条件 | 能用：照片、代码画；不能用：生图、生视频 |'
        self.fails(self.edit('content.md', (cell, '| 制作条件 | 无真人 |')), '「制作条件」要写成「能用：……；不能用：……」')
        self.fails(self.edit('content.md', ('不能用：生图、生视频 |', '不能用：照片、生视频 |')), 'H1 的来源是「照片」，总则的制作条件写了不能用')
        self.passes(self.edit('content.md', (cell, '| 制作条件 | 能用：照片（只用公开的，标出处）、代码画；不能用：生图、生视频 |')))
        self.notes(self.edit('content.md', (cell, '| 制作条件 | 能用：照片：只用公开的，标出处、代码画；不能用：生图、生视频 |')), '「制作条件」里的「标出处」不是画面来源的名字')

    def test_total_extent(self):
        """各段篇幅合计不在总则的区间里：提示；只写目标的按 ±15%"""
        self.notes(self.edit('content.md', ('| 篇幅 | 20 秒，16–24 |', '| 篇幅 | 60 秒，55–70 |')), '各段篇幅合计 18–20 秒，不在总则篇幅的区间 55–70 秒 里')
        self.passes(self.edit('content.md', ('| 篇幅 | 20 秒，16–24 |', '| 篇幅 | 20 秒 |')))
        self.notes(self.edit('content.md', ('| 篇幅 | 20 秒，16–24 |', '| 篇幅 | 30 秒 |')), '不在总则篇幅的区间 25.5–34.5 秒 里')
        self.fails(self.edit('content.md', ('| 篇幅 | 20 秒，16–24 |', '| 篇幅 | 短一点 |')), '篇幅「短一点」解析不出')

    def test_target(self):
        t = check.parse_target
        self.assertEqual(t('90 秒，80–105'), ('时间', 90, 90, 80, 105))
        self.assertEqual(t('60 秒'), ('时间', 60, 60, 60, 60))
        self.assertEqual(t('12 页'), ('页', 12, 12, 12, 12))
        self.assertEqual(t('1 分钟，50–70 秒'), ('时间', 60, 60, 50, 70))
        self.assertIsNone(t('短一点'))

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

    def test_pages(self):
        """篇幅用页：单位一致才比合计；不是视频不查字数、原句、可删"""
        d = self.edit('content.md', ('| 输出形式和规格 | 视频；16:9；中文；有旁白 |', '| 输出形式和规格 | PPT；16:9；中文 |'),
                      ('| 声音 | 旁白，第三人称 |', '| 声音 | 讲者现场讲 |'), ('| 语速 | 中 |', '| 语速 | 无 |'),
                      ('| 篇幅 | 20 秒，16–24 |', '| 篇幅 | 6 页 |'), ('| 8–10 秒 |', '| 3 页 |'), ('| 10 秒 |', '| 3 页 |'),
                      ('| 原句 |', '| 必讲 |'), ('| 可删① |', '| 必讲 |'))
        self.passes(d)
        p = os.path.join(d, 'content.md')
        write(p, read(p).replace('| 篇幅 | 6 页 |', '| 篇幅 | 20 页 |'))
        self.notes(d, '各段篇幅合计 6 页，不在总则篇幅的区间 17–23 页 里')
        write(p, read(p).replace('| 3 页 |', '| 800 字 |', 1))
        self.notes(d, '各段篇幅单位不一致')

    # ---------- 红线、约束、素材 ----------
    def test_red_lines(self):
        self.fails(self.edit('content.md', ('| B1 | 讲公告以外的事 | 人工：', '| B1 | 讲公告以外的事 | 看着办：')), 'B1 的「怎么查」要以「词：」「条件：」「人工：」开头')
        self.fails(self.edit('content.md', ('词：「史上第一」「首次」', '词：史上第一')), 'B2 写了「词：」，后面要用「」列出词')
        self.fails(self.edit('content.md', ('| B3 | 只说月份', '| C3 | 只说月份')), '编号格式不对：C3（写 B1、B2）')
        self.fails(self.edit('content.md', ('| P2-1、P1-3、B3 |', '| P2-1、P1-3、B7 |')), 'content.md:P2:念什么: 引用的 B7 在红线里没有')

    def test_red_words(self):
        """「词：」的词出现在念什么里：提示（引述原话可以）；「；」后面的除外说明里的「」不算词"""
        self.assertEqual(check.red_words('词：「收益」「回报」；题目里「客户原话」除外'), ['收益', '回报'])
        self.notes(self.edit('content.md', ('「记下这个月份。」', '「记下这个首次的月份。」')), 'S4 用了红线 B2 的词「首次」')
        self.notes(self.edit('content.md', ('「记下这个月份。」', '「记下这个客户原话。」'), ('；除外：题目', '；「客户原话」除外')), 'B2 的例外要写成')

    def test_red_except(self):
        """红线的例外写成「；除外：S1、题目」：写到的 S 不再提示；写成自由文字的提示；除外的 S 要存在"""
        self.assertEqual(check.red_except('词：「收益」；除外：S1、S25、题目'), (['S1', 'S25'], True, True))
        self.assertEqual(check.red_except('词：「收益」'), ([], False, True))
        self.assertEqual(check.red_except('词：「收益」；引述观众原话除外')[2], False)
        self.passes(self.edit('content.md', ('「记下这个月份。」', '「记下这个首次的月份。」'), ('；除外：题目', '；除外：S4、题目')))
        self.notes(self.edit('content.md', ('；除外：题目', '；引述公告原话除外')), 'B2 的例外要写成「；除外：S1、题目」')
        self.fails(self.edit('content.md', ('；除外：题目', '；除外：S99')), 'B2 的除外写了 S99，念什么里没有这句')

    def test_spoken_and_count(self):
        """要念的字只剥最外层「」；数字按念法算字数；〔2020〕这类文号不算占位"""
        s1 = '「「下班就关电脑，有错吗？」这话不全错：可第二天的活，确实会堆起来。」'
        self.assertEqual(check.char_count(check.spoken(s1)), 26)
        self.assertEqual(check.spoken('「甲」（停顿）「乙」'), '甲；乙')
        self.assertEqual(check.char_count('利率按 2.0% 假设'), 11)        # 百分之二点零 6 字
        self.assertEqual(check.char_count('1.4 倍'), 4)
        self.assertEqual(check.char_count('第 12 年，交 10 万'), 7)         # 第十二年，交十万
        self.assertEqual(check.char_count('2026 年'), 5)                  # 年份一位一位念
        self.assertEqual(check.char_count('252,756 英里'), 13)            # 二十五万二千七百五十六
        self.assertFalse(check.is_placeholder('〔2020〕'))
        self.assertTrue(check.is_placeholder('〔待定〕'))

    def test_self_check_numbers(self):
        """效果自查手写字数：提示"""
        self.notes(self.edit('plan.md', ('| 表达 |', '| 表达 | S1 24 字，约 5 秒；')), '「表达」手写了字数')

    def test_rules(self):
        d = self.edit('content.md', ('| M1 | 已核实 |', '| M1 | 〔待核实〕 |'))
        self.assertEqual(run(d)[0], 0)
        self.fails(d, 'K1 还是「〔待核实〕」：约束要已核实或是设定才能交接', True)
        out = self.fails(self.edit('content.md', ('| K1 | 现场的旗是蓝色的 | M1 |', '| K1 | 现场的旗是蓝色的 | M2、P1-8 |')), 'content.md:约束: 引用的 M2 在 content.md 的素材表里没有')
        self.assertIn('content.md:约束: 引用的 P1-8 在 content.md 里没有', out)

    def test_assets(self):
        out = self.fails(self.edit('content.md', ('| 裁后用：裁掉水印 | 能 |', '| 随便 | 可以 |')), 'M1 的能怎么用「随便」要取')
        self.assertIn('M1 的能不能送生成「可以」要取', out)
        self.notes(self.edit('content.md', ('| 裁后用：裁掉水印 | 能 |', '| 只作参考 | 〔待核实〕：授权没写 |')), 'M1 能不能送生成还没核实，下游按「不能」处理', True)
        self.fails(self.edit('content.md', ('| 能 | P1 |', '| 能 | P4 |')), 'content.md:素材: 引用的段 P4 在 content.md 里没有')
        self.fails(self.edit('content.md', ('| F2 | M1 |', '| F2 | M3 |')), 'content.md:P1:信息: 引用的 M3 在 content.md 的素材表里没有')
        self.fails(self.edit('content.md', ('| M1 | https', '| N1 | https')), 'content.md:素材: 编号格式不对：N1（写 M1、M2）')
        self.notes(self.edit('content.md', ('| M1、K1、P1-4 |', '| Q1、K1、P1-4 |')), 'M1 要用（P1），但看什么没有一格用到它')

    # ---------- 每段：段头 ----------
    def test_seg_head(self):
        self.fails(self.edit('content.md', ('| 节奏 | 快 |\n', '')), '段头要正好是这6项')
        self.fails(self.edit('content.md', ('| 情绪 | 紧 |', '| 情绪 | 激动 |')), 'P1 的情绪要以 紧 / 松 / 稳 / 扬 开头')
        self.passes(self.edit('content.md', ('| 情绪 | 紧 |', '| 情绪 | 松（段子手） |')))
        self.fails(self.edit('content.md', ('| 节奏 | 快 |', '| 节奏 | 很快 |')), 'P1 的节奏要以 快 / 中 / 慢 开头')
        self.fails(self.edit('content.md', ('| 8–10 秒 |', '| 十秒 |')), 'P1 的篇幅「十秒」解析不出')
        self.fails(self.edit('content.md', ('| 作用 | 收尾，承接 P1 |', '| 作用 | 收尾，承接 P7 |')), 'content.md:P2: 引用的段 P7 在 content.md 里没有')

    def test_points(self):
        self.fails(self.edit('content.md', ('a. 某日发生某事<br>b. 是谁做的', '某日发生某事；是谁做的')), r'P1 的要讲的点要按「a. 一点一句<br>b. ……」写')
        self.fails(self.edit('content.md', ('<br>b. 是谁做的', '<br>c. 是谁做的')), 'P1 的要讲的点要从 a 起按顺序编：现在是 a、c')

    def test_audience(self):
        self.fails(self.edit('content.md', ('「以后呢」→ 记下某月', '记下某月')), 'P2 的「从 → 到」要写「原来的念头 → 看完这段的念头或动作」')
        self.notes(self.edit('content.md', ('「以后呢」→ 记下某月', '「以后呢」→ 知道下一步在某月')), 'P2 的「到」以「知道下」开头')

    def test_seg_names(self):
        self.fails(self.edit('content.md', ('## P2 收尾', '## Px 收尾')), '节名的段号格式不对：Px')
        self.fails(self.edit('content.md', ('## P2 收尾', '## P1 收尾')), '段 P1 有两节')
        self.fails(self.edit('content.md', ('### 看什么\n\n| # | 要看到什么 | 来源 | 主角 | 最大的字 | 上屏的字 | 配哪句 | 用到 |\n|---|---|---|---|---|---|---|---|\n| H2', '| H2')), '缺「### 看什么」')

    # ---------- 每段：念什么 ----------
    def test_say_table(self):
        self.fails(self.edit('content.md', ('| # | 点 | 句 | 级 | 依据 |', '| # | 点 | 句 | 级别 | 依据 |')), '念什么表表头要正好是')
        self.fails(self.edit('content.md', ('| S3 | a、b |', '| S2 | a、b |')), '编号重复：S2')
        self.fails(self.edit('content.md', ('| S3 | a、b |', '| T3 | a、b |')), '编号格式不对：T3（写 S1、S2）')
        self.fails(self.edit('content.md', ('| 可删① | P1-4、K1 |', '| 可删 | P1-4、K1 |')), 'S2 的级「可删」要取 原句 / 必讲 / 可删①')
        self.fails(self.edit('content.md', ('| S2 | a |', '| S2 | c |')), 'S2 的点「c」不在 P1 的要讲的点里')
        self.fails(self.edit('content.md', ('| S2 | a |', '| S2 | |')), 'S2 的点空着')

    def test_say_basis(self):
        """依据：编号要存在；不说事实的写 比喻 / 观点 / 过渡；说了数字要有信息编号"""
        self.fails(self.edit('content.md', ('| 可删① | 观点 |', '| 可删① | 我觉得 |')), 'S4 的依据要写信息、约束、红线编号')
        self.fails(self.edit('content.md', ('「记下这个月份。」 | 可删① | 观点 |', '「记下这个月份，11 月。」 | 可删① | 观点 |')), 'S4 说了数字，依据要有信息编号')
        self.fails(self.edit('content.md', ('「记下这个月份。」 | 可删① | 观点 |', '「再等三万年。」 | 可删① | 观点 |')), 'S4 说了数字')
        self.fails(self.edit('content.md', ('| P1-4、K1 |', '| P1-4、K7 |')), 'content.md:P1:念什么: 引用的 K7 在 content.md 的约束表里没有')

    def test_original_and_cut(self):
        """有旁白的视频：全片第一句、终点那段要有原句；每段至少一句可删（只有原句的段除外）：交接报错、平时提示"""
        d = self.edit('content.md', ('某事。」 | 原句 |', '某事。」 | 必讲 |'))
        self.notes(d, '全片第一句 S1（钩子句）的级要是「原句」')
        self.fails(d, '全片第一句 S1', True)
        self.fails(self.edit('content.md', ('来做。」 | 原句 |', '来做。」 | 必讲 |')), '终点 P2 那段要有一句「原句」', True)
        d = self.edit('content.md', ('| 可删① | 观点 |', '| 必讲 | 观点 |'))
        self.notes(d, 'P2 没有「可删」')
        self.fails(d, 'P2 没有「可删」', True)
        self.passes(self.edit('content.md', ('| 可删① | 观点 |', '| 原句 | 观点 |')))   # 只有原句的段
        d = self.edit('content.md', ('某事。」 | 原句 |', '某事。」 | 必讲 |'), ('来做。」 | 原句 |', '来做。」 | 必讲 |'),
                      ('| 可删① | 观点 |', '| 必讲 | 观点 |'), ('| 声音 | 旁白，第三人称 |', '| 声音 | 不说话，只放画面 |'), ('| 语速 | 中 |', '| 语速 | 无 |'))
        self.passes(d)

    def test_budget(self):
        """字数按篇幅 × 语速档估算，只提示：原句 + 必讲超过 85%、全部超过 115%；单句超过 40 字"""
        long_ = '「某日，某机构在某地做成了某事，现场照片里那面旗是蓝色的，大家那一天都看见了那面旗。」'
        d = self.edit('content.md', ('「某日，某机构在某地做成了某事。」', long_))
        self.notes(d, r'P1 原句加必讲 \d+ 字，超过上限 40.5 字的 85%')
        self.notes(d, r'P1 原句加必讲', True)   # 交接时也只提示
        d = self.edit('content.md', ('「现场照片就在这里，旗是蓝色的。」', '「现场照片就在这里，旗是蓝色的，大家都看见了那面旗，也记住了那一天。」'),
                      ('| 语速 | 中 |', '| 语速 | 慢 |'))
        self.notes(d, r'P1 全部 \d+ 字，超过上限 36 字的 115%')
        self.passes(self.edit('content.md', ('| 语速 | 中 |', '| 语速 | 快 |')))
        long_ = '「某日，某机构在某地做成了某事，现场照片里那面旗是蓝色的，大家都看见了那面旗，也都记住了那一天发生的事。」'
        self.notes(self.edit('content.md', ('「现场照片就在这里，旗是蓝色的。」', long_)), r'S2 有 4\d 字，口播单句不超过 40 字')

    # ---------- 每段：看什么 ----------
    def test_view_table(self):
        self.fails(self.edit('content.md', ('| H2 |', '| H1 |')), 'content.md:P2:看什么: 编号重复：H1')
        self.fails(self.edit('content.md', ('| H2 |', '| X2 |')), '编号格式不对：X2（写 H1、H2）')
        self.fails(self.edit('content.md', ('| 代码画 |', '| 动画 |')), 'H2 的来源「动画」要取 代码画 / 照片')
        self.fails(self.edit('content.md', ('| 场景 |', '| 风景 |')), 'H1 的主角「风景」要取 一个数')
        self.notes(self.edit('content.md', ('| 场景 |', '| 其他：一面旗 |')), 'H1 的主角写了「其他」')
        self.fails(self.edit('content.md', ('| 一句话 | 某月 |', '| 一句话 | |')), 'H2 的最大的字空着')
        self.notes(self.edit('content.md', ('| 一句话 | 某月 |', '| 一句话 | 无 |')), 'H2 的主角是「一句话」，最大的字却写了「无」')
        self.notes(self.edit('content.md', ('| 一句话 | 某月 |', '| 一句话 | 明年 |')), 'H2 的最大的字「明年」不在上屏的字里')
        self.fails(self.edit('content.md', ('| 下一步，某月 | S3 |', '| | S3 |')), 'H2 的上屏的字空着')

    def test_view_pair(self):
        self.fails(self.edit('content.md', ('| 下一步，某月 | S3 |', '| 下一步，某月 | S1 |')), 'H2 配的 S1 在 P1，要配本段的句')
        self.fails(self.edit('content.md', ('| 下一步，某月 | S3 |', '| 下一步，某月 | S9 |')), 'H2 配的 S9 在念什么里没有')
        self.fails(self.edit('content.md', ('| 下一步，某月 | S3 |', '| 下一步，某月 | |')), 'H2 的配哪句空着')
        self.passes(self.edit('content.md', ('| 下一步，某月 | S3 |', '| 下一步，某月 | 无 |')))
        self.passes(self.edit('content.md', ('| 下一步，某月 | S3 |', '| 下一步，某月 | S3–S4 |')))

    def test_view_grounding(self):
        """看什么的「用到」按来源要有着落"""
        self.fails(self.edit('content.md', ('| S3 | P2-1、P2 a |', '| S3 | K1 |'), ('念 S3；上屏 H2 |', '念 S3 |')), 'H2 是代码画，「用到」要有它画的信息（P1-1）或上屏的点（P1 a）')
        self.passes(self.edit('content.md', ('| S3 | P2-1、P2 a |', '| S3 | P2 a |'), ('念 S3；上屏 H2 |', '念 S3 |')))
        self.fails(self.edit('content.md', ('| M1、K1、P1-4 |', '| K1、Q2、P1-4 |')), 'H1 是照片，「用到」要有素材 M，或归下游的缺口 Q')
        self.passes(self.edit('content.md', ('| M1、K1、P1-4 |', '| Q1、P1-4 |'), ('| K1 | 现场的旗是蓝色的 | M1 |', '| K1 | 现场的旗是蓝色的 | P1-4 |'),
                              ('| M1 | https://example.com/a.jpg | 现场照片 | 右下角水印 | 裁后用：裁掉水印 | 能 | P1 |', '| M1 | https://example.com/a.jpg | 现场照片 | 右下角水印 | 裁后用：裁掉水印 | 能 | 不用 |')))
        self.fails(self.edit('content.md', ('| 代码画 | 一句话 |', '| 数据 | 一句话 |'), ('| S3 | P2-1、P2 a |', '| S3 | P2 a |'), ('念 S3；上屏 H2 |', '念 S3 |')),
                   'H2 是数据，「用到」要有数据本身（P1-1）或数据文件（M1）')
        self.fails(self.edit('content.md', ('| 代码画 | 一句话 |', '| 录屏 | 界面 |'), ('| S3 | P2-1、P2 a |', '| S3 | 某个界面 |'), ('念 S3；上屏 H2 |', '念 S3 |')), 'H2 的「用到」要写编号')
        self.fails(self.edit('content.md', ('| M1、K1、P1-4 |', '| M3、K1、Q9、P1-4 |')), 'content.md:P1:看什么: 引用的 M3 在 content.md 的素材表里没有')
        self.fails(self.edit('content.md', ('| P2-1、P2 a |', '| P2-1、P2 c |')), 'H2 用到「P2 c」，「c」不在 P2 的要讲的点里')

    def test_generated(self):
        d = self.edit('content.md', ('| 照片 | 场景 |', '| 生图 | 场景 |'), ('| M1、K1、P1-4 |', '| M1、P1-4 |'), ('不能用：生图、生视频', '不能用：生视频'))
        self.fails(d, 'H1 是生图，「用到」至少要有一条约束 K')
        d = self.edit('content.md', ('| 照片 | 场景 |', '| 生图 | 场景 |'), ('不能用：生图、生视频', '不能用：生视频'))
        self.passes(d, False)
        p = os.path.join(d, 'content.md')
        write(p, read(p).replace('| 裁后用：裁掉水印 | 能 |', '| 裁后用：裁掉水印 | 不能：有人脸 |'))
        self.fails(d, 'H1 是生图，用到的 M1 不能送生成')
        write(p, read(p).replace('| 不能：有人脸 |', '| 〔待核实〕 |'))
        self.notes(d, 'H1 是生图，用到的 M1 能不能送生成还没核实')

    def test_view_per_segment(self):
        d = self.edit('content.md', ('| H2 | 「下一步，某月」上屏 | 代码画 | 一句话 | 某月 | 下一步，某月 | S3 | P2-1、P2 a |\n', ''), ('念 S3；上屏 H2 |', '念 S3 |'))
        self.notes(d, 'P2 没有看什么：每段至少一行（提示）')
        self.fails(d, 'P2 没有看什么：每段至少一行', True)

    # ---------- 每段：信息和去向 ----------
    def test_data_rows(self):
        self.fails(self.edit('content.md', ('| P2-1 | a |', '| P1-5 | a |'), ('P2-1', 'P1-5')), '编号格式不对：P1-5（这一节写 P2-1、P2-2）')
        self.fails(self.edit('content.md', ('| P1-1 | a |', '| P1-1 | c |')), 'P1-1 讲的「c」不在 P1 的要讲的点里')
        self.fails(self.edit('content.md', ('b（P2 b 也用）', 'b（P7 也用）')), 'P1-3 写了「P7 也用」，P7 在 content.md 里没有这一段')
        self.fails(self.edit('content.md', ('| P1-2 | a |', '| P1-2 | 不用 |')), 'P1-2 的「讲哪一点」写了「不用」：格式 5 改成写字母')
        self.fails(self.edit('content.md', ('| 〔待核实〕 | 不讲', '| 待查 | 不讲')), 'P1-2 的状态「待查」不在')

    def test_destinations(self):
        """去向：取值；不讲要有理由、不能并列别的"""
        self.fails(self.edit('content.md', ('| 念 S1 |', '| 口播 |')), 'P1-1 的去向「口播」认不出')
        self.fails(self.edit('content.md', ('| 不讲：只有一家媒体报道 |', '| 不讲 |')), 'P1-2 写了「不讲」，后面要写理由')
        self.fails(self.edit('content.md', ('| 不讲：只有一家媒体报道 |', '| 不讲：备查；上屏 H1 |')), 'P1-2 的去向写了「不讲」，就不能再念')
        self.fails(self.edit('content.md', ('| 念 S1 |', '| 念 S9 |')), 'P1-1 的去向写了 S9，念什么里没有这一句')
        self.fails(self.edit('content.md', ('| 念 S1 |', '| |')), 'P1-1 的去向空着')
        self.passes(self.edit('content.md', ('念 S1、S3 |', '念 S1；念 S3 |')))
        self.assertEqual(check.s_ids('S1–S3、S5'), ['S1', 'S2', 'S3', 'S5'])

    def test_destinations_match(self):
        """去向和念什么的依据、看什么的用到两边对得上"""
        self.fails(self.edit('content.md', ('| P1-1、P1-3、B1 |', '| P1-3、B1 |')), 'P1-1 的去向写了 S1，S1 的依据里却没有 P1-1')
        self.fails(self.edit('content.md', ('| 可删① | 观点 |', '| 可删① | P2-1 |')), 'S4 的依据写了 P2-1，P2-1 的去向没有「念 S4」或「依据：S4」')
        self.fails(self.edit('content.md', ('依据：S2；上屏 H1 |', '依据：S2 |')), 'H1 的用到写了 P1-4，P1-4 的去向没有「上屏 H1」')
        self.fails(self.edit('content.md', ('| P1-4、K1 |', '| K1 |')), 'P1-4 的去向写了 S2，S2 的依据里却没有 P1-4')
        self.fails(self.edit('content.md', ('依据：S2；上屏 H1 |', '依据：S2；上屏 H1、H2 |')), 'P1-4 的去向写了上屏 H2，H2 的用到里却没有 P1-4')

    def test_coverage(self):
        """交接时：每个要讲的点有信息（去向不是「不讲」）、有一句念它"""
        d = self.edit('content.md', ('b（P2 b 也用）', 'b'))
        self.assertEqual(run(d)[0], 0)
        self.fails(d, 'P2 的「b」没有对应的信息', True)
        d = self.edit('content.md', ('| S3 | a、b |', '| S3 | a |'))
        self.assertEqual(run(d)[0], 0)
        self.fails(d, 'P2 的「b」没有一句念它', True)
        d = self.edit('content.md', ('| P1-3 | b（P2 b 也用） |', '| P1-3 | b（P2 也用） |'))
        self.fails(d, 'P2 的「b」没有对应的信息', True)   # 没写字母的「也用」不算作哪一点

    def test_unverified(self):
        """「不讲」的〔待核实〕不挡交接；要用就挡"""
        d = self.edit('content.md', ('| 不讲：只有一家媒体报道 |', '| 念 S2 |'), ('| P1-4、K1 |', '| P1-4、P1-2、K1 |'))
        self.assertEqual(run(d)[0], 0)
        self.fails(d, 'P1-2 要用（去向不是「不讲」），它还是「〔待核实〕」', True)

    def test_model_names_not_refs(self):
        """规定格子以外的「华为 P40」「2026 年 Q1」「S70」是正文，不当引用"""
        d = self.edit('plan.md', ('| 背景故事 | 延后 | 无 | 时长不够 |', '| 华为 P40、仰望 U9 的对比 | 删除 | 无 | 2026 年 Q1 的旧闻，P9-9、S70 |'))
        p = os.path.join(d, 'content.md')
        write(p, read(p).replace('a. 某日发生某事', 'a. 某日发生某事，对比华为 P40'))
        for handoff in (False, True):
            self.passes(d, handoff)

    # ---------- 资料清单、衍生、下游回报 ----------
    def test_sources(self):
        self.fails(self.edit('content.md', ('| 内容依据、素材 |', '| 内容依据，素材 |')), '「某公告」的用途「内容依据，素材」要取')
        d = self.edit('content.md', ('| https://example.com/a |', '| `source/a/article.md` |'))
        self.notes(d, '位置 source/a/article.md 不存在')
        self.fails(d, '位置 source/a/article.md 不存在', True)
        os.makedirs(os.path.join(d, 'source', 'a'))
        write(os.path.join(d, 'source', 'a', 'article.md'), '原文')
        self.passes(d)
        d = self.edit('content.md', ('| https://example.com/a |', '| `plans/other/source/a/article.md` |'))
        self.fails(d, '指到别的策划目录 plans/other/source/a/article.md', True)
        d = self.edit('content.md', ('| https://example.com/a |', '| `plans/demo/source/b/article.md` |'))
        self.fails(d, '位置 plans/demo/source/b/article.md 不存在', True)
        os.makedirs(os.path.join(d, 'source', 'b'))
        write(os.path.join(d, 'source', 'b', 'article.md'), '原文')
        self.passes(d)

    def test_spin(self):
        self.passes(self.edit('content.md', ('| 条 | 用哪些点 | 第一句 | 放在哪 |\n|---|---|---|---|\n| D1 | P1 a、P2 a | 「某日，某事。」 | 10 秒短片 |', '无')))
        self.fails(self.edit('content.md', ('| 条 | 用哪些点 | 第一句 | 放在哪 |\n|---|---|---|---|\n| D1 | P1 a、P2 a | 「某日，某事。」 | 10 秒短片 |', '没有')), '没有衍生就只写一行「无」')
        out = self.fails(self.edit('content.md', ('| D1 | P1 a、P2 a |', '| E1 | P1 a、P3 a |')), '编号格式不对：E1（写 D1、D2）')
        d = self.edit('content.md', ('| D1 | P1 a、P2 a |', '| D1 | P1 a、P3 a |'))
        self.fails(d, 'D1 用到的段 P3 在 content.md 里没有')

    def test_back_reports(self):
        """下游回报：取值、对象编号；有待补的交接报错；归策划待补而状态不是回流中提示"""
        head = '| # | 段 | 类型 | 对象 | 说明 | 归谁 | 状态 | 怎么解决的 |\n|---|---|---|---|---|---|---|---|\n'
        d = self.edit('content.md', (head, head + '| X1 | P1 | 删减 | S2 | 超时删了 | 下游 | 已知悉 | |\n'))
        self.passes(d)
        d = self.edit('content.md', (head, head + '| X1 | P1 | 改了 | S9 | 说明 | 美术 | 搁置 | |\n'))
        out = self.fails(d, 'X1 的类型「改了」要取')
        self.assertIn('X1 的归谁「美术」要取', out)
        self.assertIn('X1 的状态「搁置」要取', out)
        self.assertIn('content.md:下游回报: 引用的 S9 在念什么里没有', out)
        d = self.edit('content.md', (head, head + '| X1 | P2 | 缺素材 | H2 | 风格包没有这个部件 | 策划 | 待补 | |\n'))
        out = self.notes(d, 'X1 归策划、还待补，状态行该是「回流中」')
        self.fails(d, 'X1 还「待补」', True)
        self.fails(self.edit('content.md', (head, head + '| X1 | P9 | 删减 | S2 | 说明 | 下游 | 已知悉 | |\n')), 'X1 的段「P9」写段号')


class DocsTest(unittest.TestCase):
    def test_formats_match_template(self):
        """formats.md 的表：每种形式都写了篇幅单位和交给谁；形式名和模板总则「输出形式和规格」的选项一致"""
        text = read(os.path.join(SKILL, 'formats.md'))
        t = check.find_table(text.split('\n'), ['输出形式', '篇幅单位', '交给谁'])
        self.assertTrue(t)
        for row in t[1]:
            self.assertTrue(row['篇幅单位'] and row['交给谁'], row)
        tpl = read(os.path.join(SKILL, 'templates', 'content.md'))
        m = re.search(r'^\| 输出形式和规格 \| 〔([^；〕]+)', tpl, re.M)
        self.assertTrue(m)
        self.assertEqual([x.strip() for x in m.group(1).split('/')], [row['输出形式'] for row in t[1]])

    def test_leads_documented(self):
        """主角的 15 个取值在 effect.md 里都写了"""
        text = read(os.path.join(SKILL, 'effect.md'))
        for lead in check.LEADS:
            self.assertIn(lead, text)


if __name__ == '__main__':
    unittest.main()
