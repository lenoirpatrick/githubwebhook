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

## Architecture

The entire application is in a single file: `gitpull.py`.

- **`/`** — HTML home page with a link to the demo endpoint.
- **`/beats`** — Health check endpoint; returns `{"result": true}`.
- **`/webhook`** (POST) — Receives GitHub push events. Checks the `ref` field; only processes pushes to `refs/heads/main`. Calls `update_webhook()`.
- **`/webhookdemo`** — Triggers a simulated webhook using `demo/demo.json` as the payload. Useful for manual testing.
- **`update_webhook(webhook_github)`** — Core logic: resolves the repo path from `config/config.json`, runs `git reset --hard HEAD~1` then `git pull` in that path.

## Configuration

`config/config.json` maps repository full names (e.g. `"lenoirpatrick/githubwebhook"`) to local paths, and contains the server bind IP:

```json
{
  "ip": "127.0.0.1",
  "lenoirpatrick/githubwebhook": {
    "path": "/home/pi/app/githubwebhook"
  }
}
```

The config is loaded at module startup (global scope), so the server must be started from the project root directory.

## CI

`.github/workflows/build.yml` runs two jobs on push to `main`/`develop` and on PRs:
- **SonarQube** — static analysis via SonarCloud (requires `SONAR_TOKEN` secret).
- **pylint** — runs across Python 3.11, 3.12, 3.13 matrix.