# Model Configuration Topology — Lux V2 Pipeline

> Rewritten 2026-07-26 — the previous version of this doc described an
> architecture where most steps inherited the Hermes profile default. That's
> no longer true: verified against the live `run_v2.sh` and the current
> `~/.hermes/profiles/luke/config.yaml`, **every** pipeline step now pins its
> own model and provider explicitly. Nothing in the daily run falls back to
> the profile default.

## 1. Profile Default (`config.yaml`) — NOT used by the pipeline

```yaml
model:
  default: deepseek/deepseek-v4-flash
  provider: openrouter
  base_url: https://openrouter.ai/api/v1
```

This is the fallback for ad-hoc/manual `hermes chat` commands run outside
`run_v2.sh`. Every step the pipeline itself invokes passes an explicit
`-m ... --provider localAIServer`, so changing this default has **no effect** on the
daily run.

## 2. What the pipeline actually uses: explicit `localAIServer` provider

`localAIServer` is a custom provider pointing at a private, third-party-hosted
LiteLLM server (URL and key deliberately not in this public repo — see
`docs/SETUP.md`). Every `hermes chat` call in `run_v2.sh`, and the hardcoded
default in `wire_articles.py`, targets it directly:

| Step | Model | Provider | Where |
|------|-------|----------|-------|
| All 8 `run_scout()` calls (x, research, official, opensource, tools, funding, hardware, italia) | `deepseek-v4-flash` | `localAIServer` | hardcoded inside the `run_scout()` helper, `run_v2.sh` |
| YouTube scout (Phase 4) | `deepseek-v4-flash` | `localAIServer` | `run_v2.sh`, step 2 phase 4 |
| Editor (DS) | `deepseek-v4-flash` | `localAIServer` | `run_v2.sh`, step 4 |
| Editor (K3) | `kimi-k3` | `localAIServer` | `run_v2.sh`, step 4b |
| Image gen orchestrator | `deepseek-v4-flash` | `localAIServer` | `run_v2.sh`, step 5 (the `image_generate` tool call itself still goes to xAI regardless — see §3) |
| Podcast pill dialogue | `deepseek-v4-flash` | `localAIServer` | `run_v2.sh`, step 7 (the actual TTS audio still goes to xAI — see §3) |
| Wire articles (DS) | `deepseek-v4-flash` | `localAIServer` | `wire_articles.py` defaults (`MODEL`/`PROVIDER`, overridable via `--model`/`--provider`) |
| Wire articles (K3) | `kimi-k3` | `localAIServer` | `run_v2.sh` step 8, passed as `--model kimi-k3 --provider localAIServer` |

None of these are pinned to survive a future profile-default change by
accident — they're pinned because the pipeline needs `localAIServer` specifically
(the free/cheap inference tier), not because of drift protection. If you
want a step to use something else, edit its `-m`/`--provider` flags in
`run_v2.sh` (or `MODEL`/`PROVIDER` in `wire_articles.py`) directly.

## 3. Components that bypass `localAIServer` entirely (xAI direct)

These use tool-level integrations, not `hermes chat -m`, so they're
unaffected by any of the above:

| Component | Tool | Provider | Auth |
|-----------|------|----------|------|
| **Image gen** (Grok Imagine) | `image_generate` | xAI API | `xai-oauth` (OAuth) |
| **TTS voices** (podcast Castor/Luna) | `text_to_speech` | xAI API | `xai-oauth` (OAuth) |

Both authenticate against the same xAI account, which is why image gen and
podcast credit exhaustion look related — but they don't always fail on the
same day (see `docs/ARCHITETTURA.md#independent-credit-checks-image-gen-vs-podcast`).
Each has its own independent credit check in `run_v2.sh` as of 2026-07-26.

## 4. Auxiliary Hermes models (`config.yaml`) — unrelated to Lux

Separate from anything above; used by the Hermes gateway itself for internal
features, not invoked by the Lux pipeline:

| Purpose | Provider | Model |
|---------|----------|-------|
| `title_generation` | openrouter | openrouter/owl-alpha |
| `vision` | openrouter | openrouter/owl-alpha |
| `compression` | openrouter | openrouter/owl-alpha |
| `curator` | openrouter | openrouter/owl-alpha |

## How to Change a Step's Model

1. **Identify the step** in `run_v2.sh` (look for the `hermes chat -q` block, or the `run_scout()` helper if it's one of the 8 parallel scouts).
2. **Change its `-m <model> --provider <provider>` flags** directly — there's no default to fall back to, so this fully determines what that step uses.
3. **Test** by running just that step standalone:
   ```bash
   hermes chat -q "..." -s <skill> -t <toolsets> -m <model> --provider <provider> -Q --yolo
   ```
4. **Confirm with the user before editing `run_v2.sh`** — it's the live production orchestrator, symlinked directly into the cron path.
