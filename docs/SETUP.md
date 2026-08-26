# Setup — Local AI News Pipeline

## Prerequisites

- Linux (Fedora VPS or similar)
- [Hermes Agent](https://hermes-agent.nousresearch.com), with a profile configured
  (this doc uses `paper` as the profile name)
- GitHub credentials with push access to both repos (stored via
  `git credential`)
- Git, Python 3.12+ (everything is stdlib; `trafilatura` optional but
  recommended — `pip install -r requirements.txt`)
- A LiteLLM/OpenAI-compatible endpoint for inference. This setup uses the
  DGX Spark's proxy at `http://100.89.102.56:4000/v1`.

## Installation

### 1. Clone the pipeline repo

```bash
git clone https://github.com/MovieMaker93/local-ai-news-pipeline.git
```

### 2. Symlink to Hermes paths

The pipeline repo contains ALL code, but Hermes expects files at specific
profile-relative paths. Symlinks bridge this gap:

```bash
# Pipeline scripts
mkdir -p ~/.hermes/profiles/paper/scripts
ln -s ~/local-ai-news-pipeline/scripts ~/.hermes/profiles/paper/scripts/v2

# Skills
mkdir -p ~/.hermes/profiles/paper/skills
ln -s ~/local-ai-news-pipeline/skills ~/.hermes/profiles/paper/skills/lain
```

### 3. The Hermes profile

The pipeline invokes `hermes chat --profile paper -s <skill> -t <toolsets>
-m flash --provider spark`. Create the profile and give it the `spark`
custom provider (in `~/.hermes/profiles/paper/config.yaml`):

```yaml
custom_providers:
  - name: spark
    base_url: http://100.89.102.56:4000/v1
    api_key: <your LiteLLM key>
    models:
      - flash
```

### 4. Point the orchestrator at your setup

`scripts/run.sh` self-locates its own script/template paths (works wherever
the repo is cloned or symlinked). Override via environment variables read at
the top of the script:

| Variable | Default | What it is |
|---|---|---|
| `PAPER_PROFILE` | `paper` | Hermes profile name |
| `PAPER_HERMES_BIN` | `$HOME/.local/bin/hermes` | Path to the hermes binary |
| `PAPER_DEPLOY_DIR` | `$HOME/local-ai-news-deploy` | Local clone of the deploy repo |
| `PAPER_TG_ENV` | `~/.hermes/profiles/paper/.env` | Optional .env with Telegram creds |
| `PAPER_SITE_URL` | `https://moviemaker93.github.io/local-ai-news/` | Site URL for notifications |

Export these in whatever launches the pipeline — e.g. a small untracked
wrapper script outside this repo:

```bash
#!/bin/bash
export PAPER_PROFILE=paper
export PAPER_DEPLOY_DIR="$HOME/local-ai-news-deploy"
exec bash ~/.hermes/profiles/paper/scripts/v2/cron_wrapper.sh
```

### 5. Deploy repository

The pipeline pushes rendered output to a **separate** repo (keeps the
pipeline's own history free of generated HTML):

1. Create an empty repo and enable GitHub Pages (Settings → Pages → Deploy
   from a branch → `main`, root).
2. `git clone` it to wherever `PAPER_DEPLOY_DIR` points (default
   `~/local-ai-news-deploy`).
3. **First run only:** the pipeline reads the issue number from the *live*
   page's own masthead, so on a brand-new deploy repo with no `index.html`
   yet it starts at issue `#1` automatically.
4. URL will be `https://<user>.github.io/local-ai-news/` (project page —
   all internal links are relative, which is why the template uses
   `archive/` not `/archive/`).

### 6. Cron job

```bash
hermes cron create \
  --name "Local AI News" \
  --schedule "30 6 * * *" \
  --script v2/cron_wrapper.sh \
  --no-agent
```

### 7. Telegram notifications (optional)

`run.sh` posts short milestone updates (scout progress, failures, final
report) to Telegram if it finds credentials — silently skips otherwise.
Create the file at `PAPER_TG_ENV` (default `~/.hermes/profiles/paper/.env`) with:

```
TELEGRAM_BOT_TOKEN=<your bot token>
TELEGRAM_HOME_CHANNEL=<your chat id>
```

## Update workflow

1. Always work inside `~/local-ai-news-pipeline/`
2. `git add`, `git commit`, `git push`
3. Symlinks mean Hermes sees changes immediately, active on next run

## Separate deploy repository

The output HTML lives in a separate deploy repo (see step 5). Do not
manually modify it — the pipeline overwrites it on every run.
