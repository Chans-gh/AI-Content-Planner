"""check.py 的离线测试。运行：python3 -m unittest discover -s skills/video-content-planner/scripts/tests

fixtures/ok/ 是一份全通过的；其余每个夹具目录只放改过的文件，测试时叠在 ok/ 上。
"""
import io
import json
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
        self.assertFails('missing_ref', r'引用的 U1-9 在 research.md 里没有', handoff=False)

    def test_open_gap(self):
        self.assertEqual(run(self.case('open_gap'))[0], 0)   # 普通检查只看格式
        self.assertFails('open_gap', r'Q2 归策划、还待补')

    def test_unverified(self):
        self.assertFails('unverified', r'P2 的核心内容用了 U1-2，它还是「〔待核实〕」')

    def test_closed_no_reason(self):
        self.assertFails('closed_no_reason', r'Q3 是「改内容关闭」', handoff=False)

    def test_example_handoff(self):
        code, out = run(os.path.join(SKILL, 'example'), True)
        self.assertEqual((code, out.strip()), (0, '通过'))

    def test_template_only_notes(self):
        """刚复制的模板：普通检查没有错，只有占位提示；--handoff 不通过"""
        for f in ('plan.md', 'research.md'):
            shutil.copy(os.path.join(SKILL, 'templates', f), self.tmp)
        code, out = run(self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn('占位没填', out)
        self.assertEqual(run(self.tmp, True)[0], 1)

    def test_missing_file(self):
        shutil.copy(os.path.join(FIX, 'ok', 'plan.md'), self.tmp)
        code, out = run(self.tmp)
        self.assertEqual(code, 1)
        self.assertIn('research.md: 文件不存在', out)

    def test_duration(self):
        p = check.parse_duration
        self.assertEqual(p('45 秒'), (45, 45))
        self.assertEqual(p('40–50 秒'), (40, 50))
        self.assertEqual(p('1 分 30 秒'), (90, 90))
        self.assertEqual(p('2 分钟'), (120, 120))
        self.assertEqual(p('1 分钟 30 秒'), (90, 90))
        self.assertEqual(p('约 45 秒'), (45, 45))
        self.assertEqual(p('45 秒左右'), (45, 45))
        self.assertIsNone(p('四十秒'))
        self.assertIsNone(p('45'))

    def test_duration_total_note(self):
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path).replace('20 秒；16:9', '60 秒；16:9')
        write(path, text)
        code, out = run(d)
        self.assertEqual(code, 0)
        self.assertIn('相差超过 15%', out)

    def test_model_names_not_refs(self):
        """规定格子以外的「华为 P40」「2026 年 Q1」「仰望 U9」是正文，不当引用"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path).replace('| 背景故事 | 延后 | 时长不够 |', '| 华为 P40、仰望 U9 的对比 | 删除 | 2026 年 Q1 的旧闻 |')
        write(path, text)
        for handoff in (False, True):
            code, out = run(d, handoff)
            self.assertEqual((code, out.strip()), (0, '通过'))

    def test_scoped_refs_still_checked(self):
        """规定的格子里写了不存在的编号照样报：素材编排的 Q、作用的 P、凭什么信的 U"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path).replace('照片，见 Q1', '照片，见 Q9').replace('收尾，承接 P1', '收尾，承接 P7')
        text = text.replace('| 用途 | 测试夹具 | 建议 |', '| 用途 | 测试夹具 | 建议 |\n| 凭什么信 | 官方公告（U4-1） | 材料里的 |')
        write(path, text)
        code, out = run(d, False)
        self.assertEqual(code, 1)
        self.assertIn('plan.md:立意: 引用的 U4-1 在 research.md 里没有', out)
        self.assertIn('plan.md:段落: 引用的缺口 Q9 在缺口表里没有', out)
        self.assertIn('plan.md:段落: 引用的段 P7 在段落表里没有', out)

    def test_whole_film_gap(self):
        """归风格后、分镜后的缺口，「段」可以写「全片」；空着不行"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        write(path, read(path).replace('| Q1 | P1 | 现场照片一张 |', '| Q1 | 全片 | 品牌标识 |'))
        self.assertEqual(run(d, True)[0], 0)
        write(path, read(path).replace('| Q1 | 全片 | 品牌标识 |', '| Q1 | | 品牌标识 |'))
        code, out = run(d, True)
        self.assertEqual(code, 1)
        self.assertIn('Q1 归分镜后，要写清缺什么、哪段', out)

    def test_direction_with_note(self):
        """「方向」后面带括注也算方向一行（回放里写「方向（回放模拟）：」被误报过）；只有「局部」不算"""
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path)
        lines = [l for l in text.split('\n') if re.match(r'\s*-\s.*方向[：:]', l)]
        self.assertTrue(lines)
        write(path, text.replace(lines[0], lines[0].replace('方向：', '方向（演示用）：', 1)))
        self.assertEqual(run(d, True), (0, '通过\n'))
        write(path, text.replace(lines[0], '- 2026-11-08 局部：只改了 P1'))
        code, out = run(d, True)
        self.assertEqual(code, 1)
        self.assertIn('没有「方向」一行', out)

    def test_enum(self):
        d = self.case('ok')
        path = os.path.join(d, 'plan.md')
        text = read(path).replace('| 分镜后 | 阶段 1 |', '| 美术 | 阶段 1 |')
        write(path, text)
        code, out = run(d)
        self.assertEqual(code, 1)
        self.assertIn('Q1 的归谁「美术」', out)


class GenresTest(unittest.TestCase):
    def test_genre_names(self):
        """genres.md 的题材名（三级标题）都在 ai-coding-video 的 content_types 里；不在仓库里运行就跳过"""
        tags = os.path.join(os.path.dirname(SKILL), 'ai-coding-video', 'data', 'tags.json')
        if not os.path.exists(tags):
            self.skipTest('找不到 ai-coding-video/data/tags.json')
        names = {c['name'] for c in json.loads(read(tags))['content_types']}
        heads = re.findall(r'^### (.+)$', read(os.path.join(SKILL, 'genres.md')), re.M)
        self.assertTrue(heads)
        self.assertEqual([h for h in heads if h.strip() not in names], [])


if __name__ == '__main__':
    unittest.main()
