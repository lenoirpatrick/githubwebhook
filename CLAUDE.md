# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A FastAPI-based GitHub webhook server that automatically pulls the latest code from GitHub repositories when a push event is received. Intended for CI/CD deployment on a Raspberry Pi or similar server.

## Commands

### Install dependencies
```shell
pip install -r requirements.txt
```

### Run the server
```shell
python gitpull.py
```

### Lint
```shell
pylint gitpull.py
```

### Run tests
```shell
pytest
```

### Run tests with coverage
```shell
pytest --cov=gitpull --cov-report=term-missing
```

### Run a single test
```shell
pytest test_gitpull.py::TestWebhook::test_invalid_signature_returns_401 -v
```

## Architecture

The entire application is in a single file: `gitpull.py`.

**Endpoints:**
- **`/`** — Dark-themed HTML home page. Lists configured repos (loaded via `GET /config/repos`) with Add / Edit / Delete buttons. All CRUD actions use JS `fetch` — no page reload.
- **`/beats`** — Health check; returns `{"result": true}`.
- **`/webhook`** (POST) — Receives GitHub push events. Verifies the HMAC-SHA256 signature if `webhook_secret` is set in config. Only processes pushes to `refs/heads/main`. Calls `update_webhook()`.
- **`/webhookdemo`** — Returns an HTML terminal-style page simulating `git reset` and `git pull` output. No real git commands are run.
- **`/docs`** — Swagger UI (built into FastAPI).
- **`GET /config/repos`** — Lists configured repos (excludes `ip` and `webhook_secret` keys).
- **`POST /config/repos`** — Adds a repo `{"repo": "owner/repo", "path": "/abs/path"}`. Returns 409 if already exists.
- **`PUT /config/repos/{owner}/{repo}`** — Updates the path of an existing repo. Returns 404 if not found.
- **`DELETE /config/repos/{owner}/{repo}`** — Removes a repo. Returns 404 if not found.

**Key functions:**
- **`_load_config()`** — Loads `config/config.json`. If the file is absent, creates it with `{"ip": "127.0.0.1"}` and returns the default. Never raises on missing file.
- **`_save_config()`** — Writes `config_github` back to `CONFIG_PATH`. Called after every CRUD mutation.
- **`update_webhook(webhook_github)`** — Resolves the repo path, checks the directory exists, runs `git reset --hard HEAD` then `git pull` via `subprocess`. Returns `{"result": bool, "message": str}`.

**Key implementation details:**
- `BASE_DIR = pathlib.Path(__file__).parent` and `CONFIG_PATH = BASE_DIR / 'config' / 'config.json'` are used for all file paths — server can be started from any directory.
- `config_github` is a module-level dict loaded at startup; tests patch it directly along with `BASE_DIR` and `CONFIG_PATH`.
- HMAC verification uses `hmac.compare_digest` to prevent timing attacks. Skipped if `webhook_secret` is absent from config.
- `subprocess.run(check=True)` is wrapped in `try/except CalledProcessError` — errors surface in the JSON response, not as 500s.

## Configuration

`config/config.json` maps repository full names to local paths, and holds the server bind IP and optional webhook secret:

```json
{
  "ip": "0.0.0.0",
  "webhook_secret": "votre_secret_github",
  "lenoirpatrick/githubwebhook": {
    "path": "/home/pi/app/githubwebhook"
  }
}
```

`webhook_secret` must match the secret configured in the GitHub webhook settings for HMAC validation to work. The file is created automatically on first startup if missing.

## Tests

`test_gitpull.py` — 23 tests, 98% coverage. Uses `fastapi.testclient.TestClient` (synchronous). The `patch_config` autouse fixture swaps `gitpull.config_github`, `gitpull.BASE_DIR`, and `gitpull.CONFIG_PATH` in-process for each test, then restores them — no real config files are read or written during tests (except in `TestLoadConfig` which explicitly tests file creation).

## CI

`.github/workflows/build.yml` runs three jobs on push to `main` and on PRs:
- **test** — `pytest --cov` across Python 3.11, 3.12, 3.13; uploads `coverage.xml` as artifact.
- **pylint** — linting across the same Python matrix.
- **sonarqube** — runs after `test`, regenerates `coverage.xml` and sends it to SonarCloud (requires `SONAR_TOKEN` secret).
