"""brief.py 的离线测试。运行：python3 -m unittest discover -s skills/ai-content-planner/scripts/tests"""
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import brief  # noqa: E402

OK = os.path.join(HERE, 'fixtures', 'ok')
EXAMPLE = os.path.join(SKILL, 'example')


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = brief.main(list(args))
    return code, out.getvalue(), err.getvalue()


class BriefTest(unittest.TestCase):
    def test_example(self):
        code, out, _ = run(EXAMPLE)
        self.assertEqual(code, 0)
        for s in ('**主线**', '## 总则', '**基调**：冷静播报', '**语速**：中', '## 红线', 'B3 不许', '### P1', '### P3',
                  '从 → 到：「又一条航天新闻」', '看 H1〔代码画 · 一个数〕', '最大的字：252,756 英里', '念 S1〔原句〕', '念 S9〔可删①〕',
                  'P3-2〔已核实〕', '## 不能送生成的素材', 'M1', '## 字数', '| P2 | 25 秒 | 78 | 95 | 112 |'):
            self.assertIn(s, out)
        p3 = out[out.index('### P3'):]
        self.assertLess(p3.index('看 H6'), p3.index('念 S8'))   # 每段先列看什么再列念什么
        self.assertNotIn('P3-4', p3)   # 去向「不讲」的不列
        self.assertNotIn('还没交接', out)
        self.assertNotIn('## 衍生', out)

    def test_ok_fixture(self):
        code, out, _ = run(OK)
        self.assertEqual(code, 0)
        self.assertIn('## 约束', out)
        self.assertIn('K1', out)

    def test_out_file(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, 'brief.md')
        code, out, _ = run(EXAMPLE, '--out', path)
        self.assertEqual((code, out), (0, ''))
        with open(path, encoding='utf-8') as f:
            self.assertTrue(f.read().startswith('# 精简版：'))
        self.assertNotIn('brief.md', os.listdir(EXAMPLE))

    def test_not_handed_off(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        for n in ('plan.md', 'content.md'):
            shutil.copy(os.path.join(EXAMPLE, n), d)
        p = os.path.join(d, 'content.md')
        with open(p, encoding='utf-8') as f:
            t = f.read()
        with open(p, 'w', encoding='utf-8') as f:
            f.write(t.replace('状态：已交接', '状态：补齐中', 1))
        code, out, _ = run(d)
        self.assertEqual(code, 0)
        self.assertIn('还没交接', out)

    def test_refuses_broken(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        shutil.copy(os.path.join(EXAMPLE, 'plan.md'), d)
        code, out, err = run(d)
        self.assertEqual((code, out), (1, ''))
        self.assertIn('content.md', err)

    def test_budget(self):
        with open(os.path.join(EXAMPLE, 'content.md'), encoding='utf-8') as f:
            nums = brief.budget(f.read())
        self.assertEqual([(n[0], n[1], n[4]) for n in nums], [('P1', 15, 67.5), ('P2', 25, 112.5), ('P3', 20, 90)])

    def test_no_narration_no_budget(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        for n in ('plan.md', 'content.md'):
            shutil.copy(os.path.join(OK, n), d)
        p = os.path.join(d, 'content.md')
        with open(p, encoding='utf-8') as f:
            t = f.read()
        with open(p, 'w', encoding='utf-8') as f:
            f.write(t.replace('| 语速 | 中 |', '| 语速 | 无 |').replace('| 声音 | 旁白，第三人称 |', '| 声音 | 不说话，只上字 |'))
        code, out, err = run(d)
        self.assertEqual(code, 0, err)
        self.assertNotIn('## 字数', out)


if __name__ == '__main__':
    unittest.main()
