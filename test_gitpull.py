""" Tests de couverture pour gitpull.py """

import hashlib
import hmac
import json
import pathlib
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


CONFIG_FIXTURE = {
    "ip": "127.0.0.1",
    "webhook_secret": "supersecret",
    "lenoirpatrick/testrepo": {"path": "/fake/path/testrepo"},
}

DEMO_PAYLOAD = {
    "ref": "refs/heads/main",
    "repository": {"full_name": "lenoirpatrick/testrepo"},
}


@pytest.fixture(autouse=True)
def patch_config(tmp_path):
    """Remplace la config globale et les fichiers lus au module-level."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(json.dumps(CONFIG_FIXTURE), encoding="utf-8")

    demo_dir = tmp_path / "demo"
    demo_dir.mkdir()
    (demo_dir / "demo.json").write_text(json.dumps(DEMO_PAYLOAD), encoding="utf-8")

    import gitpull
    original = dict(gitpull.config_github)
    original_base = gitpull.BASE_DIR

    gitpull.config_github.clear()
    gitpull.config_github.update(CONFIG_FIXTURE)
    gitpull.BASE_DIR = tmp_path
    (tmp_path / "demo" / "demo.json").write_text(json.dumps(DEMO_PAYLOAD), encoding="utf-8")

    yield

    gitpull.config_github.clear()
    gitpull.config_github.update(original)
    gitpull.BASE_DIR = original_base


@pytest.fixture()
def client():
    from gitpull import app
    return TestClient(app, raise_server_exceptions=False)


def _make_signature(body: bytes, secret: str = "supersecret") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestHome:
    def test_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "webhook" in resp.text.lower()


# ---------------------------------------------------------------------------
# GET /beats
# ---------------------------------------------------------------------------

class TestBeats:
    def test_returns_true(self, client):
        resp = client.get("/beats")
        assert resp.status_code == 200
        assert resp.json() == {"result": True}


# ---------------------------------------------------------------------------
# POST /webhook
# ---------------------------------------------------------------------------

class TestWebhook:
    def _post(self, client, payload: dict, secret: str = "supersecret", headers=None):
        body = json.dumps(payload).encode()
        sig = _make_signature(body, secret)
        h = {"X-Hub-Signature-256": sig}
        if headers:
            h.update(headers)
        return client.post("/webhook", content=body, headers=h)

    def test_push_main_triggers_update(self, client):
        with patch("gitpull.update_webhook", return_value={"result": True, "message": "ok"}) as mock_upd:
            resp = self._post(client, DEMO_PAYLOAD)
        assert resp.status_code == 200
        mock_upd.assert_called_once()

    def test_push_other_branch_ignored(self, client):
        payload = {"ref": "refs/heads/develop", "repository": {"full_name": "lenoirpatrick/testrepo"}}
        resp = self._post(client, payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"] is False
        assert "principale" in data["message"]

    def test_invalid_signature_returns_401(self, client):
        body = json.dumps(DEMO_PAYLOAD).encode()
        resp = client.post(
            "/webhook",
            content=body,
            headers={"X-Hub-Signature-256": "sha256=invalide"},
        )
        assert resp.status_code == 401

    def test_no_secret_in_config_skips_check(self, client):
        import gitpull
        gitpull.config_github.pop("webhook_secret", None)
        body = json.dumps(DEMO_PAYLOAD).encode()
        with patch("gitpull.update_webhook", return_value={"result": True, "message": "ok"}):
            resp = client.post("/webhook", content=body)
        assert resp.status_code == 200
        gitpull.config_github["webhook_secret"] = "supersecret"


# ---------------------------------------------------------------------------
# GET /webhookdemo
# ---------------------------------------------------------------------------

class TestWebhookDemo:
    def test_calls_update_webhook(self, client):
        with patch("gitpull.update_webhook", return_value={"result": True, "message": "demo ok"}) as mock_upd:
            resp = client.get("/webhookdemo")
        assert resp.status_code == 200
        mock_upd.assert_called_once_with(DEMO_PAYLOAD)


# ---------------------------------------------------------------------------
# update_webhook()
# ---------------------------------------------------------------------------

class TestUpdateWebhook:
    def test_repo_not_in_config(self):
        from gitpull import update_webhook
        payload = {"repository": {"full_name": "unknown/repo"}}
        result = update_webhook(payload)
        assert result["result"] is False
        assert "non configuré" in result["message"]

    def test_path_not_a_directory(self):
        from gitpull import update_webhook
        result = update_webhook(DEMO_PAYLOAD)
        assert result["result"] is False
        assert "introuvable" in result["message"]

    def test_successful_pull(self, tmp_path):
        from gitpull import update_webhook
        import gitpull
        gitpull.config_github["lenoirpatrick/testrepo"]["path"] = str(tmp_path)

        mock_result = MagicMock()
        mock_result.stdout = "Already up to date."
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = update_webhook(DEMO_PAYLOAD)

        assert result["result"] is True
        assert "Already up to date." in result["message"]
        assert mock_run.call_count == 2  # reset + pull

        reset_call = mock_run.call_args_list[0]
        pull_call = mock_run.call_args_list[1]
        assert "reset" in reset_call.args[0]
        assert "-C" in reset_call.args[0]
        assert "pull" in pull_call.args[0]

    def test_git_pull_failure(self, tmp_path):
        from gitpull import update_webhook
        import gitpull
        gitpull.config_github["lenoirpatrick/testrepo"]["path"] = str(tmp_path)

        error = subprocess.CalledProcessError(1, "git pull", stderr="fatal: error")

        with patch("subprocess.run", side_effect=[MagicMock(), error]):
            result = update_webhook(DEMO_PAYLOAD)

        assert result["result"] is False
        assert "fatal: error" in result["message"]

    def test_git_reset_failure(self, tmp_path):
        from gitpull import update_webhook
        import gitpull
        gitpull.config_github["lenoirpatrick/testrepo"]["path"] = str(tmp_path)

        error = subprocess.CalledProcessError(1, "git reset", stderr="fatal: reset error")

        with patch("subprocess.run", side_effect=error):
            result = update_webhook(DEMO_PAYLOAD)

        assert result["result"] is False
        assert "fatal: reset error" in result["message"]