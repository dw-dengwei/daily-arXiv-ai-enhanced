# Deployment Guide

This project supports two deployment modes:

1. Local/LAN deployment: run the crawler and website on your own machine, then access it from `localhost` or other devices on the same network.
2. GitHub Pages deployment: use GitHub Actions to generate content and publish the front end.

If you mainly want to use this project on your own computer or inside your home/office network, start with the Local/LAN section below.

## Local/LAN deployment

### What this mode does

In local mode, your machine does all of the following:

- crawls arXiv papers
- runs AI enhancement
- writes generated files into `data/`
- updates `assets/file-list.txt`
- serves the static site over HTTP

The front end reads files from the same origin, so you no longer depend on GitHub Raw URLs.

### Requirements

- macOS, Linux, or another Unix-like environment
- Python 3.12 recommended
- `uv` installed
- an LLM API key if you want full AI enhancement

Install dependencies:

```bash
uv sync
```

### Step 1: Prepare `.env`

Create a local config file:

```bash
cp .env.example .env
```

A typical example:

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.deepseek.com
LANGUAGE=Chinese
CATEGORIES=cs.CV, cs.CL, cs.TCS
MODEL_NAME=deepseek-v4-pro
DISABLE_SENSITIVE_CHECK=false
ACCESS_PASSWORD=
TOKEN_GITHUB=
```

Notes:

- `OPENAI_API_KEY` is required for the full AI flow.
- `OPENAI_BASE_URL` depends on your provider.
- `CATEGORIES` can be written as `cs.CV, cs.CL, cs.TCS`.
- `DISABLE_SENSITIVE_CHECK=true` is useful for local runs when the remote sensitive-check API is rate limited.
- `ACCESS_PASSWORD` is optional and only used for lightweight front-end password protection.

### Step 2: Run the local pipeline

Use:

```bash
./run.sh
```

What `run.sh` does:

- loads `.env` automatically when it exists
- uses `.venv` if present
- otherwise falls back to `uv run --python 3.12`
- creates `data/` and `assets/` if they do not exist
- crawls papers, runs AI enhancement, converts output, and refreshes `assets/file-list.txt`

If `OPENAI_API_KEY` is not set, the script offers a partial mode that only runs crawling and deduplication.

### Step 3: Start the local web server

After data has been generated, start the static server:

```bash
python serve_local.py --host 0.0.0.0 --port 8000
```

Then open:

- `http://127.0.0.1:8000` on the same machine
- `http://<your-lan-ip>:8000` from another device on the same network

The script prints detected LAN addresses when it starts.

### Step 4: Optional password protection

If you want a simple password gate for LAN access:

1. set `ACCESS_PASSWORD` in `.env`
2. run:

```bash
./setup-local-auth.sh
```

This updates `js/auth-config.js` with a password hash.

Important:

- this is front-end-only protection
- it uses hashed comparison plus `localStorage`
- it is suitable for lightweight LAN usage
- it is not a replacement for real server-side authentication

### Step 5: Keep it updated

To refresh papers manually:

```bash
./run.sh
```

To update automatically, schedule `run.sh` with `launchd` or `cron`.

Example `cron` entry:

```cron
0 9 * * * cd /absolute/path/to/daily-arXiv-ai-enhanced && /bin/bash ./run.sh >> /tmp/daily-arxiv.log 2>&1
```

Keep the website process (`serve_local.py`) running separately from the scheduled update job.

## GitHub Pages deployment

This is the original deployment mode of the project.

### Step 1: Fork the repository

Fork this repository to your own GitHub account.

If needed, remove or replace project-specific information such as donation links in `buy-me-a-coffee/README.md`.

### Step 2: Configure GitHub Secrets

Go to:

- your repository
- `Settings`
- `Secrets and variables`
- `Actions`

Create these repository secrets:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`

Optional:

- `ACCESS_PASSWORD`

### Step 3: Configure GitHub Variables

Create these repository variables:

- `CATEGORIES`
- `LANGUAGE`
- `MODEL_NAME`
- `EMAIL`
- `NAME`

Example values:

- `CATEGORIES=cs.CL, cs.CV`
- `LANGUAGE=Chinese`
- `MODEL_NAME=deepseek-chat`

### Step 4: Run GitHub Actions

Open:

- your repository
- `Actions`
- `arXiv-daily-ai-enhanced`

Run the workflow manually once to verify the pipeline.

The workflow file is:

- `.github/workflows/run.yml`

### Step 5: Enable GitHub Pages

Go to:

- your repository
- `Settings`
- `Pages`

Under `Build and deployment`:

- `Source = Deploy from a branch`
- `Branch = main`
- folder = `/(root)`

After Pages finishes publishing, open:

```text
https://<your-github-username>.github.io/daily-arXiv-ai-enhanced/
```

## Common issues

### `zsh: permission denied: ./run.sh`

Cause:

- `run.sh` does not have execute permission

Fix:

```bash
chmod +x run.sh
./run.sh
```

### `BASH_SOURCE[0]: parameter not set`

Cause:

- the script was run with `zsh ./run.sh`
- `run.sh` is a Bash script, not a Zsh script

Fix:

```bash
./run.sh
```

or:

```bash
bash ./run.sh
```

Do not run:

```bash
zsh ./run.sh
```

### `.env: command not found: cs.CL,`

Cause:

- `.env` was loaded with shell `source` semantics and a value such as `CATEGORIES=cs.CV, cs.CL` was interpreted incorrectly

Fix:

- use the current version of `run.sh`, which parses `.env` safely
- keep `CATEGORIES` as a single line in `.env`

Example:

```env
CATEGORIES=cs.CV, cs.CL, cs.TCS
```

### `No module named scrapy`

Cause:

- the active Python environment does not contain project dependencies

Fix:

```bash
uv sync
./run.sh
```

The current `run.sh` also attempts to fall back to `uv run --python 3.12` when `.venv` is not active.

### First run is slow

Cause:

- `uv` may download Python 3.12 and install dependencies on first use

This is normal. Later runs should be faster.

## Recommended local workflow

For day-to-day local use:

1. `uv sync`
2. `cp .env.example .env`
3. fill in `.env`
4. `./run.sh`
5. `python serve_local.py --host 0.0.0.0 --port 8000`
6. open the printed local or LAN URL

## Security note

Local/LAN deployment is designed for lightweight personal use. If you plan to expose this service to the public internet, you should add real server-side authentication and treat the current password flow as insufficient.
