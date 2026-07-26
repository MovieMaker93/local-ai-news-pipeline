# Setup — Lux in Tenebris Pipeline

## Prerequisites

- WSL / Linux
- [Hermes Agent](https://hermes-agent.nousresearch.com) configured (profile `luke`)
- GitHub SSH keys configured
- Git
- Python 3.13+

## Installation

### 1. Clone the pipeline repo

```bash
git clone git@github.com:NTTLuke/lux-in-tenebris-pipeline.git
```

### 2. Symlink to Hermes paths

The pipeline repo contains ALL code, but Hermes expects files at original paths.
Symlinks bridge this gap:

```bash
# Pipeline scripts
cd ~/.hermes/profiles/luke/scripts
rm -rf v2   # remove original directory (backup first!)
ln -s ~/lux-in-tenebris-pipeline/scripts v2

# Skills
cd ~/.hermes/profiles/luke/skills
rm -rf ai-news-v2
ln -s ~/lux-in-tenebris-pipeline/skills ai-news-v2
```

### 3. Verify

```bash
ls -la ~/.hermes/profiles/luke/scripts/v2
# → lrwxrwxrwx ... ~/lux-in-tenebris-pipeline/scripts

ls -la ~/.hermes/profiles/luke/skills/ai-news-v2
# → lrwxrwxrwx ... ~/lux-in-tenebris-pipeline/skills
```

### 4. Cron job

The cron job `29fa53d809c4` is already configured. To recreate it:

```bash
hermes cron create \
  --name "Lux in Tenebris V2" \
  --schedule "0 7 * * *" \
  --script v2/cron_wrapper.sh \
  --no-agent \
  --deliver telegram
```

### 5. LiteLLM private server

The pipeline runs its models (`deepseek-v4-flash`, `kimi-k3`) through a
private, third-party-hosted LiteLLM server, configured as a custom provider
named `localAIServer` in `~/.hermes/profiles/luke/config.yaml`. The base URL and API
key are private and deliberately not included in this public repo — ask the
repo owner if you need them, or point `localAIServer` at your own
OpenAI-compatible/LiteLLM endpoint instead:

```yaml
custom_providers:
  - name: localAIServer
    base_url: <your LiteLLM / OpenAI-compatible endpoint>
    api_key: <your key>
    models:
      - deepseek-v4-flash
      - kimi-k3
```

## Update Workflow

1. Always work inside `~/lux-in-tenebris-pipeline/`
2. `git add`, `git commit`, `git push`
3. Symlinks mean Hermes sees changes immediately
4. The cron job uses symlinks → changes are active on the next run

## Separate Deploy Repository

The output HTML lives in a separate deploy repo:
- **Repo:** `NTTLuke/luxintenebris-ai-news`
- **Local:** `~/ai-news-deploy/`
- **URL:** `https://luxintenebris.news` (custom domain via Cloudflare)
- **K3 edition:** `https://luxintenebris.news/k3/`

The pipeline automatically pushes to the deploy repo on every run.
Do not manually modify the deploy repo — changes will be overwritten.