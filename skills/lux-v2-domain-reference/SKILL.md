---
name: lux-v2-domain-reference
description: "Reference: path changes and config for luxintenebris.news custom domain. NOT a standalone skill — exists because symlinked skills can't be edited via skill_manage."
---

# Lux V2 — Domain Reference

## Path Update (2026-07-24)

When migrating from `nttluke.github.io/luxintenebris-ai-news/` to `luxintenebris.news`:

| File | Old | New |
|------|-----|-----|
| `template/newspaper.html` | `/luxintenebris-ai-news/archive/` | `/archive/` |
| `scripts/archive_issue.py` `ARCHIVE_URL` | `/luxintenebris-ai-news/archive/` | `/archive/` |
| `scripts/archive_issue.py` `HOME_URL` | `/luxintenebris-ai-news/` | `/` |
| `scripts/fix_archive_issue_numbers.py` | same two constants | same two values |

Also update already-deployed files: `sed -i 's|/luxintenebris-ai-news/archive/|/archive/|g' index.html archive/index.html` and regenerate archive listing.

## Rogue Files Pitfall (2026-07-24)

`git add -A` picks up untracked files. If `general.html`, `technical.html`, or other small test files exist in the deploy dir, they can replace the real `index.html` when committed (smaller file wins the name collision). Before `git add -A`, always:

```bash
ls -la index.html  # should be ~55KB, not ~1KB
grep -c 'LVX IN TENEBRIS' index.html  # should be >= 1
```

## Related Skills

The actual domain setup is documented in `lux-v2-domain` (symlinked, edit at `~/lux-in-tenebris-pipeline/skills/lux-v2-domain/SKILL.md`).