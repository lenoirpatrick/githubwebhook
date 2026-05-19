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
- **`/`** — Dark-themed HTML home page. Lists configured repos (loaded via `GET /config/repos`) with Deploy / Edit / Delete buttons and a colored status dot per repo. Reload button in the header card.
- **`/beats`** — Health check; returns `{"result": true}`.
- **`/webhook`** (POST) — Receives GitHub push events. Verifies the HMAC-SHA256 signature if `webhook_secret` is set in config. Only processes pushes to `refs/heads/main`. Calls `update_webhook()`.
- **`/webhookdemo`** — Returns an HTML terminal-style page simulating `git reset` and `git pull` output. Reads `demo/demo.json` for repo metadata. No real git commands are run.
- **`/docs`** — Swagger UI in dark mode (custom endpoint, default disabled via `docs_url=None`).
- **`GET /config/repos`** — Lists configured repos (excludes `ip` and `webhook_secret` keys). Each entry includes `last_status` and `last_timestamp` from the deployment log.
- **`POST /config/repos`** — Adds a repo `{"repo": "owner/repo", "path": "/abs/path"}`. Returns 409 if already exists.
- **`PUT /config/repos/{owner}/{repo}`** — Updates the path of an existing repo. Returns 404 if not found.
- **`DELETE /config/repos/{owner}/{repo}`** — Removes a repo. Returns 404 if not found.
- **`POST /deploy/{owner}/{repo}`** — Manually triggers `git reset --hard HEAD` + `git pull` on the configured repo. Logs a `deploy` entry with the actual result status.
- **`POST /reload`** — Restarts the server process via `os.execv` (0.5 s delay in a daemon thread). Logs a `reload` entry. The home page polls `/beats` and auto-redirects when the server is back up.
- **`GET /api/history`** — Paginated JSON list of deployment log entries. Query params: `page` (default 1), `per_page` (default 50, max 200), `repo` (optional), `status` (optional).
- **`GET /history`** — Dark-themed HTML page showing deployment history. Loads data from `/api/history` via JS; supports filtering by repo and status, and pagination.

**Key functions:**
- **`_load_config()`** — Loads `config/config.json`. If the file is absent, creates it with `{"ip": "127.0.0.1"}` and returns the default. Never raises on missing file.
- **`_save_config()`** — Writes `config_github` back to `CONFIG_PATH`. Called after every CRUD mutation.
- **`_init_db()`** — Creates `data/deployments.db` and the `deployment_log` table if they don't exist (`CREATE TABLE IF NOT EXISTS`). Uses the current value of `DB_PATH` (patchable in tests). Idempotent.
- **`log_action(action, repo, status, message)`** — Calls `_init_db()` then inserts a row into `deployment_log`. Called on: `startup`, `webhook`, `git_reset`, `git_pull`, `deploy`, `reload`.
- **`update_webhook(webhook_github)`** — Resolves the repo path, checks the directory exists, runs `git reset --hard HEAD` (logs `git_reset`) then `git pull` (logs `git_pull`) via `subprocess`. Each step logged independently with `ok`/`error` status. Returns `{"result": bool, "message": str}`.

**Key implementation details:**
- `BASE_DIR = pathlib.Path(__file__).parent`, `CONFIG_PATH = BASE_DIR / 'config' / 'config.json'`, and `DB_PATH = BASE_DIR / 'data' / 'deployments.db'` are module-level variables — server can be started from any directory, and all three are patchable in tests.
- `config_github` is a module-level dict loaded at startup; tests patch it directly along with `BASE_DIR`, `CONFIG_PATH`, and `DB_PATH`.
- FastAPI lifespan (`_lifespan`) calls `log_action('startup')` on server start. Not triggered in tests (TestClient without context manager).
- Swagger UI dark mode: `docs_url=None` disables the default UI; `GET /docs` injects a `<style>` block with GitHub-dark CSS overrides into the HTML returned by `get_swagger_ui_html`.
- HMAC verification uses `hmac.compare_digest` to prevent timing attacks. Skipped if `webhook_secret` is absent from config.
- `subprocess.run(check=True)` is wrapped in separate `try/except CalledProcessError` blocks for reset and pull — each step logged independently.

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

## Database

`data/deployments.db` — SQLite database created automatically on first use.

**Table `deployment_log`:**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `timestamp` | TEXT | UTC ISO-8601, set by SQLite default |
| `action` | TEXT | `startup`, `webhook`, `git_reset`, `git_pull`, `deploy`, `reload` |
| `repo` | TEXT | `owner/repo` or NULL for non-repo actions |
| `status` | TEXT | `ok` or `error` |
| `message` | TEXT | Git output or error message |

## Tests

`test_gitpull.py` — 36 tests. Uses `fastapi.testclient.TestClient` (synchronous).

**`patch_config` autouse fixture** swaps four module-level globals for each test, then restores them:
- `gitpull.config_github` — replaced with `CONFIG_FIXTURE` dict
- `gitpull.BASE_DIR` — replaced with `tmp_path`
- `gitpull.CONFIG_PATH` — replaced with `tmp_path/config/config.json`
- `gitpull.DB_PATH` — replaced with `tmp_path/data/deployments.db`; `_init_db()` is called immediately after patching

It also creates `tmp_path/demo/demo.json` so `/webhookdemo` can read it. No real config or DB files are read or written during tests (except in `TestLoadConfig`).

## Demo fixture

`demo/demo.json` is a minimal GitHub push-event payload used by `/webhookdemo` and the test fixture. It contains `ref` and `repository.full_name`. `demo/demo_full.json` is a full GitHub payload sample (reference only, not used at runtime).

## CI

`.github/workflows/build.yml` triggers on push to `main` or `develop`, and on pull requests. Runs three jobs:
- **test** — `pytest --cov` across Python 3.11, 3.12, 3.13; uploads `coverage.xml` as artifact.
- **pylint** — linting (`pylint $(git ls-files '*.py')`) across the same Python matrix.
- **sonarqube** — runs after `test`, regenerates `coverage.xml` and sends it to SonarCloud (requires `SONAR_TOKEN` secret).

When bumping the app version (`app = FastAPI(version=...)`) also update `sonar-project.properties` → `sonar.projectVersion`.
