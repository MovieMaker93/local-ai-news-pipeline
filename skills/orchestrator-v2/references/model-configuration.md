# Model Configuration Topology — Lux V2 Pipeline

Every `hermes chat -q` call in the pipeline uses one of three model sources:

## 1. Profile Default (`config.yaml`)

```yaml
model:
  default: glm-5.2
  provider: openrouter
  base_url: https://your-litellm-server.example/v1
  api_key: sk-…  # Friend's LiteLLM server
```

Used by **all steps that lack `-m`**:
- Step 2 → all `run_scout()` calls (x, research, official, opensource, tools, funding, hardware, italia)
- Step 4 → **Editor** (writes edition.json: all headlines, summaries, deck, section ordering)
- Step 5 → **Image gen** orchestrator (the `image_generate` tool itself goes to Grok Imagine, but the agent orchestrating the calls uses default)
- Step 7 → **Podcast pill** script generation (Castor/Luna dialogue — TTS voices remain on xAI/Grok via `tts.xai` config)

These inherit whatever the profile default is. Changing the default in `config.yaml` affects all of them.

## 2. Explicit `-m` Override in `run_v2.sh`

```bash
-m <model-name> --provider openrouter
```

| Step | Model | Lines |
|------|-------|-------|
| **YouTube scout** (Phase 4) | `glm-5.2` | 168-175 |
| **Editor** | *(none — inherits default)* | — |

The YouTube model is **pinned** so it doesn't drift if the profile default changes.

## 3. Hardcoded in Python (`wire_articles.py`)

```python
MODEL = 'glm-5.2'      # line 77
PROVIDER = 'openrouter' # line 78
# Overridable via env var WIRE_MODEL     # line 288
```

Used when `wire_articles.py` spawns `hermes chat -q` as a subprocess to write each article. The model name is also injected into the article's attribution footer.

## 4. Components NOT Using the Default Model

These components are configured independently and bypass the profile default:

| Component | Provider | Base URL | Auth |
|-----------|----------|----------|------|
| **Image gen** (Grok Imagine) | `image_generate` tool | xAI API | `xai-oauth` (OAuth) |
| **TTS voices** (podcast Castor/Luna) | `tts.xai` config | xAI API | `XAI_API_KEY` |
| **Auxiliary models** (vision, compression, curator, title_gen) | openrouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |

## 5. Credential Pool Layer (`auth.json`)

| Provider | Source | Base URL | Active? |
|----------|--------|----------|---------|
| **openrouter** (used for GLM-5.2 routing) | `config.yaml` inline | `https://your-litellm-server.example/v1` | ✅ Active (profile default) |
| **openrouter** (auxiliary models) | `env:OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` | ✅ Auxiliary only |
| **xai-oauth** | `loopback_pkce` (OAuth) | `https://api.x.ai/v1` | ✅ Image gen + TTS |

The `openrouter` provider name is reused for two different endpoints:
- **Default model** (scouts, editor, podcast script) → routes through `your-litellm-server.example` (friend's LiteLLM)
- **Auxiliary models** (vision, compression, curator, title_gen) → routes through `openrouter.ai` (separate config in `auxiliary.*` section)

## 6. Hermes Auxiliary Models (`config.yaml`)

These are **separate from the Lux pipeline** — used by the Hermes gateway for internal features:

| Purpose | Provider | Model |
|---------|----------|-------|
| `title_generation` | openrouter | openrouter/owl-alpha |
| `vision` | openrouter | openrouter/owl-alpha |
| `compression` | openrouter | openrouter/owl-alpha |
| `curator` | openrouter | openrouter/owl-alpha |

## How to Change a Step's Model

1. **Identify the step** in `run_v2.sh` (look for the `hermes chat -q` block)
2. **Add flags** before `-Q --yolo`:
   ```bash
   -m <model-name> \
   --provider openrouter \
   ```
3. **Test** by running just that step standalone:
   ```bash
   hermes chat -q "..." -s <skill> -t <toolsets> -m <model> --provider openrouter -Q --yolo
   ```
4. **Do NOT actually modify the file** without user confirmation — see Pitfall #14.