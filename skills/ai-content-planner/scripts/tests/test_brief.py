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
        for s in ('**主线**', '## 效果', '## 形式', '### P1', '### P3', '受众：「又一条航天新闻」',
                  '说法 P1 a、b', 'P3-2〔已核实〕', '## 不能送生成的素材', 'M1'):
            self.assertIn(s, out)
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
        p = os.path.join(d, 'plan.md')
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


if __name__ == '__main__':
    unittest.main()
