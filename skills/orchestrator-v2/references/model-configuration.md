# Model Configuration Topology — Lux V2 Pipeline

Every `hermes chat -q` call in the pipeline uses one of three model sources:

## 1. Profile Default (`config.yaml`)

```yaml
model:
  default: deepseek/deepseek-v4-flash
  provider: openrouter
```

Used by **all steps that lack `-m`**:
- Step 2 → all `run_scout()` calls (x, research, official, opensource, tools, funding, hardware)
- Step 4 → **Editor** (writes edition.json: all headlines, summaries, deck, section ordering)
- Step 5 → **Image gen** orchestrator (the `image_generate` tool itself goes to Grok Imagine, but the agent orchestrating the calls uses default)

These inherit whatever the profile default is. Changing the default in `config.yaml` affects all of them.

## 2. Explicit `-m` Override in `run_v2.sh`

```bash
-m <provider/model-slug> --provider openrouter
```

| Step | Model | Lines |
|------|-------|-------|
| **YouTube scout** (Phase 4) | `deepseek/deepseek-v4-flash` | 155-156 |
| **Editor** | *(none — inherits default)* | — |

The YouTube model is **pinned** so it doesn't drift if the profile default changes. Same model as default, redundantly specified.

## 3. Hardcoded in Python (`wire_articles.py`)

```python
MODEL = 'deepseek/deepseek-v4-flash'   # line 77
# Overridable via env var WIRE_MODEL     # line 288
```

Used when `wire_articles.py` spawns `hermes chat -q` as a subprocess to write each article. The model name is also injected into the article's attribution footer.

## 4. Credential Pool Layer (`auth.json`) — Where API Keys Live

Credentials are stored separately from the model config in `~/.hermes/profiles/luke/auth.json`:

| Provider | Source | Base URL | Active? |
|----------|--------|----------|---------|
| **openrouter** | `env:OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` | ✅ Active (profile default) |
| **deepseek** | `env:DEEPSEEK_API_KEY` | `https://api.deepseek.com/v1` | ❌ Credentials exist but NOT active |
| **xai-oauth** | `loopback_pkce` (OAuth) | `https://api.x.ai/v1` | ✅ Used for Grok Imagine |

The deepseek API key is stored and the provider plugin exists (`hermes-agent/plugins/model-providers/deepseek/`), but the profile routes `deepseek/deepseek-v4-flash` through **OpenRouter**, not the direct DeepSeek API. To use the direct provider, change `config.yaml`:
```yaml
model:
  default: deepseek-v4-flash    # no "deepseek/" prefix
  provider: deepseek
```

## 5. Hermes Auxiliary Models (`config.yaml`)

These are **separate from the Lux pipeline** — used by the Hermes gateway for internal features. The relevant one for title work is `auxiliary.title_generation`, which controls how Hermes generates episode/chat titles in the gateway's session list (not Lux article headlines):

| Purpose | Model | Used For |
|---------|-------|----------|
| `title_generation` | openrouter/owl-alpha | Episode title metadata (gateway) |
| `vision` | openrouter/owl-alpha | Image analysis fallback |
| `compression` | openrouter/owl-alpha | Context compression |
| `curator` | openrouter/owl-alpha | Skill curator |

## How to Change a Step's Model

1. **Identify the step** in `run_v2.sh` (look for the `hermes chat -q` block)
2. **Add flags** before `-Q --yolo`:
   ```bash
   -m <provider/model-slug> \
   --provider <provider-name> \
   ```
3. **Test** by running just that step standalone:
   ```bash
   hermes chat -q "..." -s <skill> -t <toolsets> -m <model> --provider <provider> -Q --yolo
   ```
4. **Do NOT actually modify the file** without user confirmation — see Pitfall #14.