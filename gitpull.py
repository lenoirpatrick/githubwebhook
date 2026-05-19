""" Mies à jour automatique d'un dépot git """

import hashlib
import hmac
import json
import pathlib
import subprocess

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(
    title="GitHub Webhook Server",
    description="Serveur de webhook GitHub pour déploiement CI/CD automatique via `git pull`.",
    version="1.3.0",
    docs_url=None,
)

BASE_DIR = pathlib.Path(__file__).parent
CONFIG_PATH = BASE_DIR / 'config' / 'config.json'


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        default = {"ip": "127.0.0.1"}
        CONFIG_PATH.write_text(json.dumps(default, indent=4), encoding="utf-8")
        return default
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _save_config() -> None:
    CONFIG_PATH.write_text(
        json.dumps(config_github, indent=4, ensure_ascii=False), encoding="utf-8"
    )


config_github = _load_config()


class RepoConfig(BaseModel):
    repo: str
    path: str


_SWAGGER_DARK_CSS = """
body { background-color: #0d1117 !important; }
.swagger-ui { background-color: #0d1117; color: #c9d1d9; }
.swagger-ui .info .title,
.swagger-ui .info p,
.swagger-ui .info li,
.swagger-ui .info a { color: #c9d1d9; }
.swagger-ui .info a { color: #58a6ff; }
.swagger-ui .scheme-container { background: #161b22; box-shadow: none; border-bottom: 1px solid #30363d; }
.swagger-ui .opblock-tag { color: #c9d1d9; border-bottom: 1px solid #30363d; }
.swagger-ui .opblock-tag:hover { background: rgba(255,255,255,0.04); }
.swagger-ui .opblock { border-color: #30363d !important; background: rgba(255,255,255,0.02) !important; }
.swagger-ui .opblock .opblock-summary-description { color: #8b949e; }
.swagger-ui .opblock .opblock-summary-path { color: #c9d1d9; }
.swagger-ui .opblock.opblock-get .opblock-summary-method { background: #1f6feb; }
.swagger-ui .opblock.opblock-post .opblock-summary-method { background: #238636; }
.swagger-ui .opblock.opblock-put .opblock-summary-method { background: #9e6a03; }
.swagger-ui .opblock.opblock-delete .opblock-summary-method { background: #b91c1c; }
.swagger-ui .opblock-body pre.microlight,
.swagger-ui .microlight { background: #161b22 !important; color: #c9d1d9 !important; }
.swagger-ui .opblock-description-wrapper p,
.swagger-ui .opblock-external-docs-wrapper p,
.swagger-ui .opblock-title_normal p { color: #c9d1d9; }
.swagger-ui table thead tr td,
.swagger-ui table thead tr th { color: #8b949e; border-bottom: 1px solid #30363d; }
.swagger-ui .response-col_status { color: #c9d1d9; }
.swagger-ui .response-col_description p { color: #c9d1d9; }
.swagger-ui .response-col_links { color: #8b949e; }
.swagger-ui .responses-inner h4,
.swagger-ui .responses-inner h5 { color: #c9d1d9; }
.swagger-ui .model-box,
.swagger-ui .model { background: #161b22; color: #c9d1d9; }
.swagger-ui section.models { background: #161b22; border-color: #30363d; }
.swagger-ui section.models h4 { color: #c9d1d9; }
.swagger-ui .model-title { color: #c9d1d9; }
.swagger-ui .prop-type { color: #58a6ff; }
.swagger-ui input[type=text],
.swagger-ui input[type=password],
.swagger-ui textarea,
.swagger-ui select { background: #0d1117; color: #c9d1d9; border-color: #30363d; }
.swagger-ui .btn { color: #c9d1d9; border-color: #30363d; background: transparent; }
.swagger-ui .btn.execute { background: #238636; border-color: #238636; color: #fff; }
.swagger-ui .btn.authorize { color: #58a6ff; border-color: #58a6ff; }
.swagger-ui .btn.cancel { color: #f85149; border-color: #f85149; }
.swagger-ui .topbar { display: none; }
.swagger-ui .arrow { filter: invert(1); }
"""


@app.get("/docs", include_in_schema=False)
async def custom_docs():
    html = get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} — Swagger UI")
    content = html.body.decode().replace("</head>", f"<style>{_SWAGGER_DARK_CSS}</style></head>")
    return HTMLResponse(content=content)


@app.get("/", response_class=HTMLResponse)
async def home():
    """ Page index """
    html_content = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>GitHub Webhook Server</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      padding: 3rem 1rem 4rem;
      gap: 1.5rem;
    }

    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 2rem 2.5rem;
      width: 100%;
      max-width: 680px;
      text-align: center;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }

    .icon { font-size: 2.4rem; margin-bottom: 0.75rem; }

    h1 { font-size: 1.4rem; font-weight: 600; color: #f0f6fc; margin-bottom: 0.4rem; }

    p.subtitle {
      font-size: 0.88rem; color: #8b949e;
      margin-bottom: 1.5rem; line-height: 1.5;
    }

    .badge {
      display: inline-flex; align-items: center; gap: 0.4rem;
      background: #1f6feb22; border: 1px solid #1f6feb55;
      color: #58a6ff; border-radius: 20px;
      padding: 0.25rem 0.75rem; font-size: 0.75rem; font-weight: 500;
      margin-bottom: 1.5rem;
    }
    .badge::before {
      content: ""; width: 7px; height: 7px;
      background: #3fb950; border-radius: 50%; display: inline-block;
    }

    .btn {
      display: inline-block; padding: 0.6rem 1.4rem;
      border-radius: 8px; font-size: 0.88rem; font-weight: 500;
      text-decoration: none; cursor: pointer; border: none;
      transition: opacity 0.15s, transform 0.1s;
    }
    .btn:active { transform: scale(0.97); }
    .btn-primary { background: #238636; color: #fff; border: 1px solid #2ea043; }
    .btn-primary:hover { opacity: 0.85; }
    .btn-secondary { background: #21262d; color: #e6edf3; border: 1px solid #30363d; }
    .btn-secondary:hover { background: #30363d; }

    /* Repos panel */
    .panel {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 12px; width: 100%; max-width: 680px;
      overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .panel-header {
      padding: 1rem 1.25rem;
      display: flex; align-items: center; justify-content: space-between;
      border-bottom: 1px solid #30363d;
    }
    .panel-header h2 { font-size: 0.95rem; font-weight: 600; color: #f0f6fc; }

    table { width: 100%; border-collapse: collapse; }
    th {
      text-align: left; padding: 0.6rem 1.25rem;
      font-size: 0.75rem; font-weight: 600; color: #8b949e;
      text-transform: uppercase; letter-spacing: 0.05em;
      border-bottom: 1px solid #21262d;
    }
    td { padding: 0.75rem 1.25rem; font-size: 0.85rem; border-bottom: 1px solid #21262d; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #1c2128; }

    td code { color: #58a6ff; font-size: 0.82rem; }
    td.path { color: #8b949e; font-size: 0.8rem; word-break: break-all; }
    td.actions { white-space: nowrap; text-align: right; }
    td.empty { color: #484f58; text-align: center; padding: 2rem; font-size: 0.85rem; }

    .btn-sm {
      display: inline-block; padding: 0.3rem 0.75rem;
      border-radius: 6px; font-size: 0.78rem; font-weight: 500;
      cursor: pointer; border: 1px solid #30363d;
      transition: opacity 0.15s;
    }
    .btn-edit { background: #21262d; color: #e6edf3; }
    .btn-edit:hover { background: #30363d; }
    .btn-delete { background: transparent; color: #f85149; border-color: #f8514944; margin-left: 0.4rem; }
    .btn-delete:hover { background: #f8514911; }

    /* Modal */
    .modal-overlay {
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,0.7); z-index: 100;
      align-items: center; justify-content: center;
    }
    .modal-overlay.open { display: flex; }
    .modal {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 12px; padding: 1.75rem 2rem;
      width: 90%; max-width: 440px;
      box-shadow: 0 16px 48px rgba(0,0,0,0.6);
    }
    .modal h3 { font-size: 1rem; font-weight: 600; margin-bottom: 1.25rem; color: #f0f6fc; }
    label { display: block; font-size: 0.8rem; color: #8b949e; margin-bottom: 0.3rem; }
    input[type=text] {
      width: 100%; padding: 0.5rem 0.75rem;
      background: #0d1117; border: 1px solid #30363d;
      border-radius: 6px; color: #e6edf3; font-size: 0.88rem;
      margin-bottom: 1rem; outline: none;
    }
    input[type=text]:focus { border-color: #58a6ff; }
    input[type=text]:disabled { opacity: 0.5; cursor: not-allowed; }
    .modal-hint { font-size: 0.75rem; color: #8b949e; margin-top: -0.6rem; margin-bottom: 1rem; }
    .modal-actions { display: flex; gap: 0.75rem; justify-content: flex-end; }

    footer {
      display: flex; gap: 1.5rem; font-size: 0.78rem; margin-top: 0.5rem;
    }
    footer a { color: #484f58; text-decoration: none; transition: color 0.15s; }
    footer a:hover { color: #8b949e; }
  </style>
</head>
<body>

  <!-- Header card -->
  <div class="card">
    <div class="icon">🔗</div>
    <h1>GitHub Webhook Server</h1>
    <p class="subtitle">Déploiement CI/CD automatique via <code>git pull</code> au push sur <strong>main</strong>.</p>
    <div class="badge">En ligne</div><br/>
    <a href="/webhookdemo" class="btn btn-primary">▶ Lancer la démo</a>
  </div>

  <!-- Repos panel -->
  <div class="panel">
    <div class="panel-header">
      <h2>Dépôts configurés</h2>
      <button class="btn btn-secondary" onclick="showModal()">+ Ajouter</button>
    </div>
    <table>
      <thead>
        <tr>
          <th>Dépôt</th>
          <th>Chemin local</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="repo-list">
        <tr><td colspan="3" class="empty">Chargement…</td></tr>
      </tbody>
    </table>
  </div>

  <footer>
    <a href="/beats">Health check</a>
    <a href="/docs">API docs</a>
    <a href="https://github.com/lenoirpatrick/githubwebhook" target="_blank" rel="noopener">GitHub</a>
  </footer>

  <!-- Modal add/edit -->
  <div class="modal-overlay" id="modal-overlay" onclick="closeOnBackdrop(event)">
    <div class="modal">
      <h3 id="modal-title">Ajouter un dépôt</h3>
      <label>Dépôt GitHub (owner/repo)</label>
      <input type="text" id="modal-repo" placeholder="lenoirpatrick/monprojet"/>
      <label>Chemin local absolu</label>
      <input type="text" id="modal-path" placeholder="/home/pi/app/monprojet"/>
      <p class="modal-hint">Répertoire où le <code>git pull</code> sera exécuté sur le serveur.</p>
      <div class="modal-actions">
        <button class="btn btn-secondary" onclick="hideModal()">Annuler</button>
        <button class="btn btn-primary" onclick="saveRepo()">Enregistrer</button>
      </div>
    </div>
  </div>

  <script>
    async function loadRepos() {
      const res = await fetch('/config/repos');
      const data = await res.json();
      const tbody = document.getElementById('repo-list');
      const entries = Object.entries(data);
      if (entries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="empty">Aucun dépôt configuré — cliquez sur « Ajouter ».</td></tr>';
        return;
      }
      tbody.innerHTML = entries.map(([repo, cfg]) => `
        <tr>
          <td><code>${repo}</code></td>
          <td class="path">${cfg.path}</td>
          <td class="actions">
            <button class="btn-sm btn-edit" onclick="showModal('${repo}','${cfg.path}')">Modifier</button>
            <button class="btn-sm btn-delete" onclick="deleteRepo('${repo}')">Supprimer</button>
          </td>
        </tr>`).join('');
    }

    function showModal(repo='', path='') {
      const repoInput = document.getElementById('modal-repo');
      repoInput.value = repo;
      repoInput.disabled = repo !== '';
      document.getElementById('modal-path').value = path;
      document.getElementById('modal-title').textContent = repo ? 'Modifier le dépôt' : 'Ajouter un dépôt';
      document.getElementById('modal-overlay').classList.add('open');
    }

    function hideModal() {
      document.getElementById('modal-overlay').classList.remove('open');
    }

    function closeOnBackdrop(e) {
      if (e.target === document.getElementById('modal-overlay')) hideModal();
    }

    async function saveRepo() {
      const repoInput = document.getElementById('modal-repo');
      const repo = repoInput.value.trim();
      const path = document.getElementById('modal-path').value.trim();
      if (!repo || !path) { alert('Tous les champs sont requis.'); return; }

      const editing = repoInput.disabled;
      const [owner, repoName] = repo.split('/');
      const url = editing ? `/config/repos/${owner}/${repoName}` : '/config/repos';

      const res = await fetch(url, {
        method: editing ? 'PUT' : 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({repo, path})
      });

      if (res.ok) { hideModal(); loadRepos(); }
      else { const err = await res.json(); alert(err.detail || 'Erreur'); }
    }

    async function deleteRepo(repo) {
      if (!confirm(`Supprimer la configuration de ${repo} ?`)) return;
      const [owner, repoName] = repo.split('/');
      await fetch(`/config/repos/${owner}/${repoName}`, {method: 'DELETE'});
      loadRepos();
    }

    window.onload = loadRepos;
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=200)


@app.get('/beats')
def beats():
    """ heart beats """
    return {"result": True}


@app.get('/config/repos')
def list_repos():
    """ Liste les dépôts configurés """
    return {k: v for k, v in config_github.items() if k not in ('ip', 'webhook_secret')}


@app.post('/config/repos', status_code=201)
def add_repo(body: RepoConfig):
    """ Ajoute un dépôt dans la configuration """
    if body.repo in config_github:
        raise HTTPException(status_code=409, detail=f"Repo {body.repo} déjà configuré")
    config_github[body.repo] = {"path": body.path}
    _save_config()
    return {"result": True}


@app.put('/config/repos/{owner}/{repo_name}')
def update_repo(owner: str, repo_name: str, body: RepoConfig):
    """ Modifie le chemin d'un dépôt configuré """
    key = f"{owner}/{repo_name}"
    if key not in config_github:
        raise HTTPException(status_code=404, detail=f"Repo {key} non trouvé")
    config_github[key]["path"] = body.path
    _save_config()
    return {"result": True}


@app.delete('/config/repos/{owner}/{repo_name}')
def delete_repo(owner: str, repo_name: str):
    """ Supprime un dépôt de la configuration """
    key = f"{owner}/{repo_name}"
    if key not in config_github:
        raise HTTPException(status_code=404, detail=f"Repo {key} non trouvé")
    del config_github[key]
    _save_config()
    return {"result": True}


@app.post('/webhook', responses={401: {"description": "Signature HMAC-SHA256 invalide"}})
async def webhook(request: Request):
    """ webhook pour lancer le pull de github """
    body = await request.body()

    secret = config_github.get("webhook_secret", "")
    if secret:
        expected_sig = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        received_sig = request.headers.get("X-Hub-Signature-256", "")
        if not hmac.compare_digest(expected_sig, received_sig):
            raise HTTPException(status_code=401, detail="Signature invalide")

    webhook_github = json.loads(body)

    if webhook_github.get('ref') == 'refs/heads/main':
        print("Nouveau push détecté ! Mise à jour en cours...")
        return update_webhook(webhook_github)

    return {"result": False, "message": "Ignoré : ce n'est pas un push sur la branche principale."}


@app.get('/webhookdemo', response_class=HTMLResponse)
def webhookdemo():
    """ gitpull de demo """
    with (BASE_DIR / 'demo' / 'demo.json').open(encoding="utf-8") as openjson:
        webhook_github = json.load(openjson)

    repo = webhook_github['repository']['full_name']
    path_repo = config_github.get(repo, {}).get('path', '/home/pi/app/' + repo.split('/')[-1])

    cmd_reset = f"git -C {path_repo} reset --hard HEAD"
    cmd_pull  = f"git -C {path_repo} pull"
    out_reset = "HEAD is now at a8d27fd pylint"
    out_pull  = (
        "remote: Enumerating objects: 5, done.\n"
        "remote: Counting objects: 100% (5/5), done.\n"
        "remote: Compressing objects: 100% (3/3), done.\n"
        "Unpacking objects: 100% (3/3), done.\n"
        f"From https://github.com/{repo}\n"
        "   a8d27fd..4c9f049  main -> origin/main\n"
        "Updating a8d27fd..4c9f049\n"
        "Fast-forward\n"
        " gitpull.py | 12 ++++++------\n"
        " 1 file changed, 6 insertions(+), 6 deletions(-)"
    )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Webhook Demo — {repo}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0d1117; color: #e6edf3;
      min-height: 100vh; display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      gap: 1.5rem; padding: 2rem;
    }}
    h1 {{ font-size: 1.1rem; font-weight: 600; color: #f0f6fc; }}
    .meta {{ font-size: 0.8rem; color: #8b949e; }}
    .terminal {{
      background: #010409; border: 1px solid #30363d; border-radius: 10px;
      width: 100%; max-width: 680px; overflow: hidden;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }}
    .term-bar {{
      background: #161b22; border-bottom: 1px solid #30363d;
      padding: 0.6rem 1rem; display: flex; align-items: center; gap: 0.5rem;
    }}
    .dot {{ width:12px; height:12px; border-radius:50%; }}
    .dot-r {{ background:#ff5f57; }} .dot-y {{ background:#febc2e; }} .dot-g {{ background:#28c840; }}
    .term-title {{ flex:1; text-align:center; font-size:0.72rem; color:#484f58; }}
    .term-body {{
      padding: 1.2rem 1.4rem;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.82rem; line-height: 1.7; white-space: pre-wrap; word-break: break-all;
    }}
    .prompt {{ color: #3fb950; }} .cmd {{ color: #e6edf3; }} .out {{ color: #8b949e; }}
    .success {{ color: #3fb950; font-weight:600; margin-top:0.5rem; display:block; }}
    footer {{ display: flex; gap: 1.5rem; font-size: 0.78rem; }}
    footer a {{ color: #484f58; text-decoration:none; transition:color .15s; }}
    footer a:hover {{ color: #8b949e; }}
  </style>
</head>
<body>
  <h1>Simulation webhook — <code style="color:#58a6ff">{repo}</code></h1>
  <p class="meta">Répertoire cible : <code>{path_repo}</code></p>
  <div class="terminal">
    <div class="term-bar">
      <span class="dot dot-r"></span><span class="dot dot-y"></span><span class="dot dot-g"></span>
      <span class="term-title">bash — webhook deploy</span>
    </div>
    <div class="term-body"><span class="prompt">$ </span><span class="cmd">{cmd_reset}</span>
<span class="out">{out_reset}</span>

<span class="prompt">$ </span><span class="cmd">{cmd_pull}</span>
<span class="out">{out_pull}</span>
<span class="success">✓ Mise à jour terminée avec succès.</span></div>
  </div>
  <footer>
    <a href="/">← Accueil</a>
    <a href="/beats">Health check</a>
    <a href="/docs">API docs</a>
    <a href="https://github.com/lenoirpatrick/githubwebhook" target="_blank" rel="noopener">GitHub</a>
  </footer>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


def update_webhook(webhook_github):
    """ Fonction commune de mise à jour du dépot """
    repo = webhook_github['repository']['full_name']

    if repo not in config_github:
        return {"result": False, "message": f"Repo {repo} non configuré"}

    path_repo = config_github[repo]['path']

    if not pathlib.Path(path_repo).is_dir():
        return {"result": False, "message": f"Chemin introuvable : {path_repo}"}

    try:
        subprocess.run(
            ['git', '-C', path_repo, 'reset', '--hard', 'HEAD'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        retour_git = subprocess.run(
            ['git', '-C', path_repo, 'pull'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        return {"result": True, "message": retour_git.stdout}

    except subprocess.CalledProcessError as exc:
        return {"result": False, "message": exc.stderr}


if __name__ == '__main__':
    ip_address = config_github.get("ip", "127.0.0.1")
    uvicorn.run(app, host=ip_address, port=5000)
