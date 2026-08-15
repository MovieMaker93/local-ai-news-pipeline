#!/usr/bin/env python3
"""validate_repo.py — static checks that run on every PR.

No network, no secrets, no LLM calls — this repo has no CI environment that
can reach the private inference server or xAI, so this only catches what's
provable without running the pipeline: syntax errors, malformed shared data,
and the one invariant the whole pipeline depends on (a skill's directory
name and its frontmatter `name:` must match, or `hermes chat -s <name>`
can't find it).

Passing this does NOT mean a PR is safe to merge — it means the PR didn't
break anything a computer can check without secrets. See CONTRIBUTING.md
for what still needs a human (or an AI assistant paired with one) to judge.

Usage:
    python3 .github/scripts/validate_repo.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
errors = []


def check(label, ok, detail=""):
    status = "OK  " if ok else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        errors.append(label + (f": {detail}" if detail else ""))


def tracked_files(pattern):
    """Files git actually tracks, matching pattern — skips .git/ and anything
    gitignored (generated __pycache__, local scratch files, etc.)."""
    out = subprocess.run(
        ["git", "ls-files", pattern], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return sorted(ROOT / p for p in out.stdout.splitlines() if p)


# ── 1. Every tracked Python file parses ─────────────────────────────
for f in tracked_files("*.py"):
    r = subprocess.run(["python3", "-m", "py_compile", str(f)], capture_output=True, text=True)
    check(f"py_compile {f.relative_to(ROOT)}", r.returncode == 0, r.stderr.strip())

# ── 2. Every tracked shell script parses ────────────────────────────
for f in tracked_files("*.sh"):
    r = subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True)
    check(f"bash -n {f.relative_to(ROOT)}", r.returncode == 0, r.stderr.strip())

# ── 3. skills/_shared/sources.md — every JSON block under a
#      <!-- sources:key:field --> anchor parses, and there's at least one ──
sources_md = ROOT / "skills" / "_shared" / "sources.md"
if sources_md.exists():
    text = sources_md.read_text()
    anchors = re.findall(r"<!-- sources:([a-z0-9-]+):([a-z]+) -->", text)
    check("sources.md has at least one anchor", len(anchors) > 0)
    for key, sub in anchors:
        pattern = (
            r"<!-- sources:" + re.escape(key) + ":" + re.escape(sub) + r" -->\s*```json\s*(.*?)```"
        )
        m = re.search(pattern, text, re.S)
        if not m:
            check(f"sources.md block [{key}:{sub}] has a json fence", False, "anchor found, no fenced json block after it")
            continue
        try:
            json.loads(m.group(1))
            check(f"sources.md JSON block [{key}:{sub}]", True)
        except json.JSONDecodeError as e:
            check(f"sources.md JSON block [{key}:{sub}]", False, str(e))

# ── 4. Every skill's frontmatter name: matches its directory name ──────
# This is the one invariant that actually breaks something at runtime if
# violated: run.sh invokes skills by name (`-s <name>`), and that name is
# resolved from the frontmatter, not the directory. A mismatch here means
# `-s <dirname>` silently can't find the skill.
skills_dir = ROOT / "skills"
if skills_dir.exists():
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir() and p.name != "_shared"):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            check(f"skill has a SKILL.md [{skill_dir.name}]", False, "directory with no SKILL.md")
            continue
        text = skill_md.read_text()
        m = re.search(r"^name:\s*(\S+)\s*$", text, re.M)
        name = m.group(1).strip() if m else None
        check(
            f"skill frontmatter name matches dir [{skill_dir.name}]",
            name == skill_dir.name,
            f"frontmatter says name: {name!r}",
        )

# ── Summary ──────────────────────────────────────────────────────────
print()
if errors:
    print(f"{len(errors)} check(s) failed:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print("All checks passed.")
