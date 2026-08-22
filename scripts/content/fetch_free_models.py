#!/usr/bin/env python3
"""
fetch_free_models.py — Fetch currently-free AI models from OpenRouter and
OpenCode Zen.

Outputs JSON matching the "free_models" contract consumed by render.py's
free-models widget (mirrors the "trending" dual-column shape/pattern used
for GitHub + HuggingFace — see fetch_trending.py).

Strategy (2026-08-21, hardened same day after hand-checking the live catalog
found real false-positive/negative traps — see `_is_actually_free`):
- OpenRouter: official public models API (no auth). A model counts as free
  only when EVERY pricing sub-field is zero (not just prompt/completion —
  some media-generation models report those as "0" but bill per generated
  unit through a channel the structured pricing object doesn't cover at
  all), its output is text-only (excludes exactly that class of model), and
  its id isn't an `openrouter/*` platform routing alias (e.g. `openrouter/
  free`, which auto-picks a random free model and isn't itself one). The
  ":free" id suffix is no longer trusted as the primary signal — it's a
  marketing convention OpenRouter applies inconsistently, not a
  ground-truth flag: it under-covers (some genuinely free models don't
  carry it) as much as it risks over-covering.
- OpenCode Zen: their /v1/models catalog has no pricing field at all, so we
  join two tables scraped from the static docs page (opencode.ai/docs/zen/):
  the "Model / Model ID" table gives us ids, the "Model / Input / Output /
  Cached Read / Cached Write" pricing table flags which rows are free — every
  cost column that has a value must say "Free" (a bare "-" means "not
  applicable", not a hidden charge).
  (Two other providers were investigated and dropped — see the pipeline
  brainstorm notes: GitHub Models' catalog API is being retired (410), and
  Nous Portal's public /v1/models is a straight mirror of OpenRouter's own
  catalog, so it would just duplicate this column under a different name.)

Pure Python 3 stdlib + curl subprocess, deterministic, no LLM, no API key.
No network tool other than curl (matches fetch_trending.py's approach so it
works the same way under the pipeline's web-tool fallback story).

Usage:
    python3 fetch_free_models.py [--output-json PATH]
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date

OPENROUTER_MODELS_API = "https://openrouter.ai/api/v1/models"
OPENCODE_ZEN_DOCS = "https://opencode.ai/docs/zen/"


def curl(url: str, timeout: int = 30) -> str | None:
    """Fetch a URL via curl. Returns None on failure."""
    try:
        result = subprocess.run(
            ["curl", "-sSL", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 10
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


def curl_json(url: str, timeout: int = 30):
    """Fetch a URL via curl and parse as JSON. Returns None on failure."""
    raw = curl(url, timeout)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _empty_column(title, url, link_label):
    return {"title": title, "url": url, "link_label": link_label,
            "date": str(date.today()), "items": []}


def _ctx_label(context_length):
    """Format an OpenRouter context_length into a short '128K ctx' / '1M ctx' label."""
    if not isinstance(context_length, int) or context_length <= 0:
        return ""
    if context_length >= 1_000_000:
        return f"{context_length / 1_000_000:g}M ctx"
    if context_length >= 1000:
        return f"{context_length // 1000}K ctx"
    return f"{context_length} ctx"


def _is_zero(value) -> bool:
    """True if a pricing field is missing, None, or parses to exactly 0."""
    if value is None or value == "":
        return True
    try:
        return float(value) == 0
    except (TypeError, ValueError):
        return False  # unparseable value — treat as NOT proven zero


def _is_actually_free(m) -> bool:
    """Deterministic free check for one OpenRouter model — do not rely on the
    ':free' id suffix or the presence of pricing.prompt/completion alone.

    Two real traps found by hand-checking the live catalog (2026-08-21):
    - Some media-generation models (e.g. google/lyria-3-*-preview) report
      pricing.prompt = pricing.completion = "0" but bill per generated unit
      (per song, per clip) in a way the structured `pricing` object doesn't
      capture at all — only in free-text `description`. The one field that
      *does* reliably flag them is architecture.output_modalities containing
      anything besides "text".
    - openrouter/* ids (openrouter/free, openrouter/auto, ...) aren't models,
      they're the platform's own routing features. Their pricing is $0 by
      definition but listing them as "a free model" would be misleading.

    So: every pricing sub-field must be zero (not just prompt/completion —
    image/audio/request/web_search/reasoning too, in case a future model puts
    a real fee there), output must be text-only, and the id must not be an
    openrouter/* platform alias.
    """
    model_id = str(m.get("id", ""))
    if not model_id or model_id.startswith("openrouter/"):
        return False

    pricing = m.get("pricing") or {}
    for key, value in pricing.items():
        if key == "overrides":
            continue  # time-of-day repricing table, not a flat fee
        if not _is_zero(value):
            return False

    output_modalities = (m.get("architecture") or {}).get("output_modalities")
    if output_modalities != ["text"]:
        return False

    return True


def fetch_openrouter():
    title = "Free on OpenRouter"
    browse_url = "https://openrouter.ai/models?max_price=0"
    link_label = "Browse free models on OpenRouter →"

    data = curl_json(OPENROUTER_MODELS_API)
    if not data:
        print("  [fetch_free_models] OpenRouter API unreachable — empty column", file=sys.stderr)
        return _empty_column(title, browse_url, link_label)

    models = data.get("data") or []
    free = [m for m in models if _is_actually_free(m)]
    free.sort(key=lambda m: (m.get("name") or m.get("id") or "").lower())

    items = []
    for m in free:
        model_id = str(m.get("id", ""))
        if not model_id:
            continue
        # Link to the EXACT id we matched as free, ":free" suffix and all.
        # When a model has both a paid and a free variant (e.g.
        # google/gemma-4-26b-a4b-it vs google/gemma-4-26b-a4b-it:free — two
        # separate catalog entries with different pricing), stripping the
        # suffix here used to point the link at the paid page instead.
        name = " ".join((m.get("name") or model_id).split())
        items.append({
            "name": name,
            "url": f"https://openrouter.ai/{model_id}",
            "meta": _ctx_label(m.get("context_length")),
        })

    print(f"  [fetch_free_models] OpenRouter: {len(items)} free models", file=sys.stderr)
    return {"title": title, "url": browse_url, "link_label": link_label,
            "date": str(date.today()), "items": items}


def _table_rows(table_html):
    """Parse <tr><td>...</td></tr> rows (skips header rows, which use <th>)."""
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", table_html, re.DOTALL):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.DOTALL)
        if cells:
            rows.append([re.sub(r"<[^>]+>", "", c).strip() for c in cells])
    return rows


def _table_headers(table_html):
    heads = re.findall(r"<th[^>]*>(.*?)</th>", table_html, re.DOTALL)
    return [re.sub(r"<[^>]+>", "", h).strip() for h in heads]


def fetch_opencode_zen():
    title = "Free on OpenCode Zen"
    link_label = "See the full Zen catalog →"

    page = curl(OPENCODE_ZEN_DOCS)
    if not page:
        print("  [fetch_free_models] OpenCode Zen docs unreachable — empty column", file=sys.stderr)
        return _empty_column(title, OPENCODE_ZEN_DOCS, link_label)

    tables = re.findall(r"<table.*?</table>", page, re.DOTALL)

    id_by_name = {}
    pricing_rows = []
    for t in tables:
        heads = _table_headers(t)
        if heads[:2] == ["Model", "Model ID"]:
            id_by_name = {r[0]: r[1] for r in _table_rows(t) if len(r) >= 2}
        elif heads[:3] == ["Model", "Input", "Output"]:
            pricing_rows = _table_rows(t)

    if not id_by_name or not pricing_rows:
        print("  [fetch_free_models] OpenCode Zen docs table shape changed — empty column", file=sys.stderr)
        return _empty_column(title, OPENCODE_ZEN_DOCS, link_label)

    items = []
    for row in pricing_rows:
        # Model, Input, Output, Cached Read, Cached Write — a row only counts
        # as free if every column that has a value says "Free" (a bare "-"
        # means "not applicable", not a hidden charge; anything else is a
        # real price and disqualifies the row).
        if len(row) < 3:
            continue
        cost_cells = row[1:5]
        if any(cell not in ("Free", "-") for cell in cost_cells):
            continue
        if row[1] != "Free" or row[2] != "Free":
            continue  # Input/Output are the ones that actually get charged per call
        name = row[0]
        model_id = id_by_name.get(name)
        if not model_id:
            continue
        items.append({"name": name, "url": OPENCODE_ZEN_DOCS, "meta": model_id})

    print(f"  [fetch_free_models] OpenCode Zen: {len(items)} free models", file=sys.stderr)
    return {"title": title, "url": OPENCODE_ZEN_DOCS, "link_label": link_label,
            "date": str(date.today()), "items": items}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-json", default=None, help="write JSON here instead of stdout")
    args = ap.parse_args()

    result = {
        "openrouter": fetch_openrouter(),
        "opencode_zen": fetch_opencode_zen(),
    }

    out = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)

    total = len(result["openrouter"]["items"]) + len(result["opencode_zen"]["items"])
    print(f"fetch_free_models: {total} free models total", file=sys.stderr)


if __name__ == "__main__":
    main()
