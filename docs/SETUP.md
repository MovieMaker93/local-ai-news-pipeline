# Setup — Lux in Tenebris Pipeline

## Prerequisiti

- WSL / Linux
- Hermes Agent configurato (profilo `luke`)
- GitHub SSH keys configurate
- Git

## Installazione

### 1. Clona il pipeline repo

```bash
git clone git@github.com:NTTLuke/lux-in-tenebris-pipeline.git
```

### 2. Symlink ai path originali

Il pipeline repo contiene TUTTO il codice, ma Hermes si aspetta i file
nei path originali. I symlink risolvono questo problema:

```bash
# Scripts pipeline
cd ~/.hermes/profiles/luke/scripts
rm -rf v2   # elimina la directory originale (backup prima!)
ln -s ~/lux-in-tenebris-pipeline/scripts v2

# Skills
cd ~/.hermes/profiles/luke/skills
rm -rf ai-news-v2
ln -s ~/lux-in-tenebris-pipeline/skills ai-news-v2
```

### 3. Verifica

```bash
ls -la ~/.hermes/profiles/luke/scripts/v2
# → lrwxrwxrwx ... ~/lux-in-tenebris-pipeline/scripts

ls -la ~/.hermes/profiles/luke/skills/ai-news-v2
# → lrwxrwxrwx ... ~/lux-in-tenebris-pipeline/skills
```

### 4. Cron job

Il cron job `29fa53d809c4` è già configurato. Se serve ricrearlo:

```bash
hermes cron create \
  --name "Lux in Tenebris V2" \
  --schedule "0 7 * * *" \
  --script v2/cron_wrapper.sh \
  --no-agent \
  --deliver telegram
```

## Flusso di lavoro aggiornamenti

1. Lavori sempre dentro `~/lux-in-tenebris-pipeline/`
2. `git add`, `git commit`, `git push`
3. I symlink fanno sì che Hermes veda subito le modifiche
4. Il cron job usa i symlink → le modifiche sono attive al prossimo run

## Deploy repo separato

Il deploy (output HTML) vive in un repo separato:
- **Repo:** `NTTLuke/luxintenebris-ai-news`
- **Locale:** `~/ai-news-deploy/`
- **URL:** `https://nttluke.github.io/luxintenebris-ai-news/`

La pipeline pusha automaticamente su quel repo ad ogni run.
Non modificare manualmente il deploy repo — le modifiche vengono sovrascritte.