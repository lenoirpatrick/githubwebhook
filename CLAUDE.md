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

### Run in background (production-style)
```shell
./run.sh
```
Uses `nohup python gitpull.py &`; logs go to `nohup.out`.

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
- **`/webhookdemo`** — Returns an HTML terminal-style page simulating `git reset` and `git pull` output. Reads `demo/demo.json` for repo metadata. No real git commands are run.
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

`test_gitpull.py` — 23 tests, 98% coverage. Uses `fastapi.testclient.TestClient` (synchronous).

**`patch_config` autouse fixture** swaps three module-level globals for each test, then restores them:
- `gitpull.config_github` — replaced with `CONFIG_FIXTURE` dict
- `gitpull.BASE_DIR` — replaced with `tmp_path`
- `gitpull.CONFIG_PATH` — replaced with `tmp_path/config/config.json`

It also creates `tmp_path/demo/demo.json` so `/webhookdemo` can read it. No real config files are read or written during tests (except in `TestLoadConfig` which explicitly tests file creation).

## Demo fixture

`demo/demo.json` is a minimal GitHub push-event payload used by `/webhookdemo` and the test fixture. It contains `ref` and `repository.full_name`. `demo/demo_full.json` is a full GitHub payload sample (reference only, not used at runtime).

## CI

`.github/workflows/build.yml` triggers on push to `main` or `develop`, and on pull requests. Runs three jobs:
- **test** — `pytest --cov` across Python 3.11, 3.12, 3.13; uploads `coverage.xml` as artifact.
- **pylint** — linting (`pylint $(git ls-files '*.py')`) across the same Python matrix.
- **sonarqube** — runs after `test`, regenerates `coverage.xml` and sends it to SonarCloud (requires `SONAR_TOKEN` secret).

When bumping the app version (`app = FastAPI(version=...)`) also update `sonar-project.properties` → `sonar.projectVersion`.

## Milestone 1.4.0 — features in progress

Issues open in the GitHub project (all in Backlog):
- **#29** — README badge → version 1.4.0
- **#30** — `POST /deploy/{owner}/{repo}` endpoint + Deploy button on home page
- **#31** — `POST /reload` endpoint + Reload button on home page (uses `os.execv`; page polls `/beats` and auto-redirects)
- **#32** — SQLite `data/deployments.db`, table `deployment_log`, function `log_action()`
- **#33** — Call `log_action()` for every significant action: `startup`, `webhook`, `git_reset`, `git_pull`, `deploy`, `reload`
- **#34** — `GET /history` HTML page + `GET /api/history` JSON (paginated, filterable by repo/status)
- **#35** — Error badge on home page rows when last deployment failed (enriches `GET /config/repos` response)
- **#36** — Epic grouping #32–#35
- **#37** — Swagger UI in dark mode
- **#38** — Footer link to `https://github.com/lenoirpatrick/githubwebhook`

Dependency order: **#32 → #33 → #34 and #35**. Issues #30, #31, #37, #38 are independent.
