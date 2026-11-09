#!/usr/bin/env python3
"""仓库自检：清单、版本号、frontmatter、行数上限、测试、例子和回放。CI 和提交前都跑这一个。

用法（在任意目录）：python3 scripts/selfcheck.py
只用标准库。每项一行，最后一行「通过」或「N 项不通过」；不通过退出码 1。
"""
import io
import json
import os
import re
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'ai-content-planner'
SKILL = os.path.join(ROOT, 'skills', NAME)
MANIFESTS = ['.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json',
             'skills/.claude-plugin/plugin.json', 'skills/.codex-plugin/plugin.json']
LIMITS = {'SKILL.md': 130, 'README.md': 60, 'handoff.md': 80, 'formats.md': 80, 'types.md': 130}

sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import check  # noqa: E402


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def frontmatter():
    m = re.match(r'---\n(.*?)\n---\n', read(f'skills/{NAME}/SKILL.md'), re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).split('\n'):
        k, _, v = line.partition(':')
        out[k.strip()] = v.strip().strip('"')
    return out


def check_manifests():
    bad, fm = [], frontmatter()
    for rel in MANIFESTS:
        try:
            data = json.loads(read(rel))
        except (OSError, ValueError) as e:
            bad.append(f'{rel} 读不了或不是合法 JSON：{e}')
            continue
        names = [data.get('name')] + [p.get('name') for p in data.get('plugins', [])]
        if any(n != NAME for n in names):
            bad.append(f'{rel} 的 name 要是 {NAME}，现在是 {names}')
        if rel.endswith('plugin.json') and data.get('version') != fm.get('version'):
            bad.append(f'{rel} 的 version {data.get("version")} 和 SKILL.md 的 {fm.get("version")} 不一致')
    return bad


def check_frontmatter():
    bad, fm = [], frontmatter()
    if not fm:
        return ['SKILL.md 没有 frontmatter']
    if fm.get('name') != NAME:
        bad.append(f'SKILL.md 的 name 要和目录名 {NAME} 一致，现在是 {fm.get("name")}')
    if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', fm.get('name', '')):
        bad.append('SKILL.md 的 name 只能用小写字母、数字、连字符')
    for k in ('description', 'version', 'display_name', 'display_name_en', 'description_en'):
        if not fm.get(k):
            bad.append(f'SKILL.md 缺 {k}')
    if len(fm.get('description', '')) > 1024:
        bad.append(f'SKILL.md 的 description 有 {len(fm["description"])} 个字符，超过 1024')
    return bad


def check_lines():
    bad = []
    for f, n in LIMITS.items():
        k = read(f'skills/{NAME}/{f}').count('\n')
        if k > n:
            bad.append(f'{f} 有 {k} 行，上限 {n}')
    return bad


def check_tests():
    suite = unittest.defaultTestLoader.discover(os.path.join(SKILL, 'scripts', 'tests'))
    buf = io.StringIO()
    with redirect_stderr(buf), redirect_stdout(buf):
        res = unittest.TextTestRunner(stream=buf, verbosity=0).run(suite)
    if res.wasSuccessful():
        return []
    return [f'测试不通过：{len(res.failures)} 个失败、{len(res.errors)} 个出错', buf.getvalue().strip()[-1500:]]


def check_examples():
    dirs = [os.path.join(SKILL, 'example')]
    replay = os.path.join(ROOT, 'docs', 'replay')
    if os.path.isdir(replay):
        dirs += sorted(os.path.join(replay, d) for d in os.listdir(replay) if os.path.isdir(os.path.join(replay, d)))
    bad = []
    for d in dirs:
        r = check.check(d, handoff=True)
        if r.errors:
            bad.append(f'{os.path.relpath(d, ROOT)} --handoff 不通过：' + '；'.join(r.errors[:3]))
    return bad


def main():
    items = [('清单和版本号', check_manifests), ('SKILL.md frontmatter', check_frontmatter),
             ('行数上限', check_lines), ('脚本测试', check_tests), ('例子和回放 --handoff', check_examples)]
    failed = 0
    for title, fn in items:
        bad = fn()
        print(f'{"✗" if bad else "✓"} {title}')
        for b in bad:
            print(f'    {b}')
        failed += bool(bad)
    print('通过' if not failed else f'{failed} 项不通过')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
