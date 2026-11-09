#!/usr/bin/env bash
# 把 skills/ 下的 Skill（每个含 SKILL.md 的目录）拷到各家 Agent 的 Skill 目录。
#   scripts/install.sh claude|codex|dsh|all            装到用户目录（~/.claude/skills 等）
#   scripts/install.sh claude|codex|dsh|all <项目目录>  装到某个项目里（<项目>/.claude/skills 等）
#   scripts/install.sh zip                             每个 Skill 打一个包 dist/<Skill 名>.zip（上传到 WorkBuddy 等）
# claude 另外把 skills/agents/*.md（随包的子代理）拷到 <目录>/.claude/agents/；zip 把 agents/ 一起打进包。
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
target="${1:-}"; base="${2:-$HOME}"
claude="$base/.claude/skills"; codex="$base/.agents/skills"; dsh="$base/.dsh/skills"
names=(); for f in "$HERE"/skills/*/SKILL.md; do d="$(dirname "$f")"; names+=("$(basename "$d")"); done
# 不带走测试缓存和可能装过的依赖、产物（__pycache__、node_modules、out）
copy() { mkdir -p "$1"; for n in "${names[@]}"; do rm -rf "${1:?}/$n"; cp -R "$HERE/skills/$n" "$1/$n"
  find "$1/$n" -depth -type d \( -name node_modules -o -name out -o -name __pycache__ \) -exec rm -rf {} +; echo "已装到 $1/$n"; done; }
# 随包的子代理（Claude Code 读 .claude/agents/）；别家不认子代理文件，主模型按 SKILL.md「子代理」的降级自己查
agents() { [ -d "$HERE/skills/agents" ] || return 0; mkdir -p "$base/.claude/agents"
  for f in "$HERE"/skills/agents/*.md; do cp "$f" "$base/.claude/agents/"; echo "已装子代理 $base/.claude/agents/$(basename "$f")"; done; }
case "$target" in
  claude) copy "$claude"; agents;;
  codex)  copy "$codex";;
  dsh)    copy "$dsh";;
  all)    copy "$claude"; agents; copy "$codex"; copy "$dsh";;
  zip)    mkdir -p "$HERE/dist"; for n in "${names[@]}"; do (cd "$HERE/skills" && rm -f "$HERE/dist/$n.zip" && zip -qr "$HERE/dist/$n.zip" "$n" $( [ -d agents ] && echo agents ) -x '*/.gitkeep' '*/__pycache__/*' '*/node_modules/*' '*/out/*'); echo "已打包 dist/$n.zip"; done;;
  *) sed -n 2,5p "$0"; exit 1;;
esac
