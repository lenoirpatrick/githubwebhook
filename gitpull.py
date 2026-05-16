""" Mies à jour automatique d'un dépot git """

import hashlib
import hmac
import json
import pathlib
import subprocess

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="GitHub Webhook Server",
    description="Serveur de webhook GitHub pour déploiement CI/CD automatique via `git pull`.",
    version="1.2.0",
)

BASE_DIR = pathlib.Path(__file__).parent

with (BASE_DIR / 'config' / 'config.json').open(encoding="utf-8") as githubjson:
    config_github = json.load(githubjson)


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
      justify-content: center;
      gap: 2rem;
    }

    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 2.5rem 3rem;
      max-width: 480px;
      width: 90%;
      text-align: center;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }

    .icon {
      font-size: 2.8rem;
      margin-bottom: 1rem;
    }

    h1 {
      font-size: 1.4rem;
      font-weight: 600;
      color: #f0f6fc;
      margin-bottom: 0.5rem;
    }

    p.subtitle {
      font-size: 0.9rem;
      color: #8b949e;
      margin-bottom: 2rem;
      line-height: 1.5;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background: #1f6feb22;
      border: 1px solid #1f6feb55;
      color: #58a6ff;
      border-radius: 20px;
      padding: 0.25rem 0.75rem;
      font-size: 0.75rem;
      font-weight: 500;
      margin-bottom: 2rem;
    }

    .badge::before {
      content: "";
      width: 7px; height: 7px;
      background: #3fb950;
      border-radius: 50%;
      display: inline-block;
    }

    .btn {
      display: inline-block;
      padding: 0.65rem 1.5rem;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 500;
      text-decoration: none;
      transition: opacity 0.15s, transform 0.1s;
    }

    .btn:active { transform: scale(0.97); }

    .btn-primary {
      background: #238636;
      color: #fff;
      border: 1px solid #2ea043;
    }

    .btn-primary:hover { opacity: 0.85; }

    footer {
      display: flex;
      gap: 1.5rem;
      font-size: 0.78rem;
    }

    footer a {
      color: #484f58;
      text-decoration: none;
      transition: color 0.15s;
    }

    footer a:hover { color: #8b949e; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🔗</div>
    <h1>GitHub Webhook Server</h1>
    <p class="subtitle">Déploiement CI/CD automatique via <code>git pull</code> au push sur <strong>main</strong>.</p>
    <div class="badge">En ligne</div>
    <br/>
    <a href="/webhookdemo" class="btn btn-primary">▶ Lancer la démo</a>
  </div>

  <footer>
    <a href="/beats">Health check</a>
    <a href="/docs">API docs</a>
  </footer>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=200)


@app.get('/beats')
def beats():
    """ heart beats """
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
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 1.5rem;
      padding: 2rem;
    }}
    h1 {{ font-size: 1.1rem; font-weight: 600; color: #f0f6fc; }}
    .meta {{ font-size: 0.8rem; color: #8b949e; }}
    .terminal {{
      background: #010409;
      border: 1px solid #30363d;
      border-radius: 10px;
      width: 100%;
      max-width: 680px;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }}
    .term-bar {{
      background: #161b22;
      border-bottom: 1px solid #30363d;
      padding: 0.6rem 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .dot {{ width:12px; height:12px; border-radius:50%; }}
    .dot-r {{ background:#ff5f57; }}
    .dot-y {{ background:#febc2e; }}
    .dot-g {{ background:#28c840; }}
    .term-title {{ flex:1; text-align:center; font-size:0.72rem; color:#484f58; }}
    .term-body {{
      padding: 1.2rem 1.4rem;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.82rem;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-all;
    }}
    .prompt {{ color: #3fb950; }}
    .cmd    {{ color: #e6edf3; }}
    .out    {{ color: #8b949e; }}
    .success {{ color: #3fb950; font-weight:600; margin-top:0.5rem; display:block; }}
    footer {{
      display: flex; gap: 1.5rem; font-size: 0.78rem;
    }}
    footer a {{ color: #484f58; text-decoration:none; transition:color .15s; }}
    footer a:hover {{ color: #8b949e; }}
  </style>
</head>
<body>
  <h1>Simulation webhook — <code style="color:#58a6ff">{repo}</code></h1>
  <p class="meta">Répertoire cible : <code>{path_repo}</code></p>

  <div class="terminal">
    <div class="term-bar">
      <span class="dot dot-r"></span>
      <span class="dot dot-y"></span>
      <span class="dot dot-g"></span>
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
        print("Retour à l'état propre")
        subprocess.run(
            ['git', '-C', path_repo, 'reset', '--hard', 'HEAD'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        print("Mise à jour du dépot")
        retour_git = subprocess.run(
            ['git', '-C', path_repo, 'pull'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        print(f"Sortie standard : {retour_git.stdout}")
        return {"result": True, "message": retour_git.stdout}

    except subprocess.CalledProcessError as exc:
        print(f"La commande a échoué : {exc.stderr}")
        return {"result": False, "message": exc.stderr}


if __name__ == '__main__':
    ip_address = config_github.get("ip", "127.0.0.1")
    uvicorn.run(app, host=ip_address, port=5000)
