# Model Configuration Topology — Local AI News Pipeline

> Adapted from the upstream Lux reference (2026-07-26 rewrite). Every
> pipeline step pins its own model and provider explicitly; nothing in the
> daily run falls back to the profile default.

## 1. The pipeline's provider: the `spark` custom provider

Every `hermes chat` call in `run.sh` targets the DGX Spark's LiteLLM proxy
through the single `PIPELINE_PROVIDER` variable defined at the top of
`run.sh`:

```bash
PIPELINE_PROVIDER="spark"
PIPELINE_MODEL="qwen-mia"
```

There is exactly one place to look and one place to change. This fork uses
`qwen-mia` (served by the Spark's LiteLLM proxy). The old
`flash`/`deepseek-v4-flash` route was removed from LiteLLM on 2026-09-04;
`qwen3.8-flash-next` was the 2026-09-04/05 stopgap, replaced by `qwen-nvidia`
on 2026-09-06, then by `qwen-mia` (reasoning model) later the same day.

| Step | Model | Provider | Where |
|------|-------|----------|-------|
| All 10 `run_scout()` calls | `qwen-mia` | `$PIPELINE_PROVIDER` | inside the `run_scout()` helper, `run.sh` |
| Editor | `qwen-mia` | `$PIPELINE_PROVIDER` | `run.sh`, step 4 |
| Wire articles | `qwen-mia` | `spark` | `wire_articles.py` defaults (`MODEL`/`PROVIDER`, overridable via `--model`/`--provider`) |

## 2. Do not swap the provider

These are pinned, not incidental drift protection — the pipeline has to run
on the self-hosted Spark server, while the operator's interactive Hermes
chats may run on any other provider. Upstream incident (2026-07-27/28): a
session asked to raise the scout timeout and also silently rewrote all
`--provider` flags to `openrouter`, producing a day's edition on the wrong
(paid, metered) backend before anyone noticed. The `PIPELINE_PROVIDER`
indirection and the warning block above it exist because of that.

Being one self-hosted box is also why scouts run **one at a time** — see
`docs/ARCHITETTURA.md#scout-concurrency--why-sequential`.

## 3. How to Change a Step's Model

1. **Identify the step** in `run.sh` (look for the `hermes chat -q` block, or the `run_scout()` helper if it's one of the 10 scouts).
2. **Change its `-m <model> --provider <provider>` flags** directly — there's no default to fall back to, so this fully determines what that step uses.
3. **Test** by running just that step standalone:
   ```bash
   hermes chat -q "..." -s <skill> -t <toolsets> -m <model> --provider <provider> -Q --yolo
   ```
4. **Confirm with Alfonso before editing `run.sh`** — it's the live production orchestrator, symlinked directly into the cron path.
