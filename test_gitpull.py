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
    import gitpull
    original = dict(gitpull.config_github)
    original_base = gitpull.BASE_DIR
    original_config_path = gitpull.CONFIG_PATH

    demo_dir = tmp_path / "demo"
    demo_dir.mkdir()
    (demo_dir / "demo.json").write_text(json.dumps(DEMO_PAYLOAD), encoding="utf-8")

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    config_path.write_text(json.dumps(CONFIG_FIXTURE), encoding="utf-8")

    gitpull.config_github.clear()
    gitpull.config_github.update(CONFIG_FIXTURE)
    gitpull.BASE_DIR = tmp_path
    gitpull.CONFIG_PATH = config_path

    yield

    gitpull.config_github.clear()
    gitpull.config_github.update(original)
    gitpull.BASE_DIR = original_base
    gitpull.CONFIG_PATH = original_config_path


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
    def test_returns_html(self, client):
        resp = client.get("/webhookdemo")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_shows_repo_and_commands(self, client):
        resp = client.get("/webhookdemo")
        assert "lenoirpatrick/testrepo" in resp.text
        assert "git" in resp.text
        assert "pull" in resp.text

    def test_no_real_path_required(self, client):
        """La page s'affiche même si le répertoire du repo n'existe pas."""
        resp = client.get("/webhookdemo")
        assert resp.status_code == 200


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


# ---------------------------------------------------------------------------
# GET /config/repos
# ---------------------------------------------------------------------------

class TestConfigRepos:
    def test_list_excludes_ip_and_secret(self, client):
        resp = client.get("/config/repos")
        assert resp.status_code == 200
        data = resp.json()
        assert "ip" not in data
        assert "webhook_secret" not in data
        assert "lenoirpatrick/testrepo" in data

    def test_add_repo(self, client):
        resp = client.post("/config/repos", json={"repo": "owner/newrepo", "path": "/tmp/newrepo"})
        assert resp.status_code == 201
        assert resp.json()["result"] is True
        import gitpull
        assert "owner/newrepo" in gitpull.config_github

    def test_add_duplicate_returns_409(self, client):
        resp = client.post("/config/repos", json={"repo": "lenoirpatrick/testrepo", "path": "/tmp/x"})
        assert resp.status_code == 409

    def test_update_repo(self, client):
        resp = client.put("/config/repos/lenoirpatrick/testrepo",
                          json={"repo": "lenoirpatrick/testrepo", "path": "/new/path"})
        assert resp.status_code == 200
        import gitpull
        assert gitpull.config_github["lenoirpatrick/testrepo"]["path"] == "/new/path"

    def test_update_unknown_repo_returns_404(self, client):
        resp = client.put("/config/repos/unknown/repo",
                          json={"repo": "unknown/repo", "path": "/tmp/x"})
        assert resp.status_code == 404

    def test_delete_repo(self, client):
        resp = client.delete("/config/repos/lenoirpatrick/testrepo")
        assert resp.status_code == 200
        import gitpull
        assert "lenoirpatrick/testrepo" not in gitpull.config_github

    def test_delete_unknown_repo_returns_404(self, client):
        resp = client.delete("/config/repos/unknown/repo")
        assert resp.status_code == 404

    def test_config_persisted_to_file(self, client):
        import gitpull
        client.post("/config/repos", json={"repo": "owner/saved", "path": "/tmp/saved"})
        saved = json.loads(gitpull.CONFIG_PATH.read_text(encoding="utf-8"))
        assert "owner/saved" in saved


# ---------------------------------------------------------------------------
# Issue #26 — config.json absent au démarrage
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_creates_default_config_if_missing(self, tmp_path):
        import gitpull
        missing_path = tmp_path / "nodir" / "config.json"
        gitpull.CONFIG_PATH = missing_path
        result = gitpull._load_config()
        assert result == {"ip": "127.0.0.1"}
        assert missing_path.exists()
        gitpull.CONFIG_PATH = tmp_path / "config" / "config.json"