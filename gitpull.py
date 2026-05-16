""" Mies à jour automatique d'un dépot git """

import hashlib
import hmac
import json
import pathlib
import subprocess

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

BASE_DIR = pathlib.Path(__file__).parent

with (BASE_DIR / 'config' / 'config.json').open(encoding="utf-8") as githubjson:
    config_github = json.load(githubjson)


@app.get("/", response_class=HTMLResponse)
async def home():
    """ Page index """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Accueil - Webhook Demo</title>
    </head>
    <body>
        <h1>Bienvenue sur le serveur de webhook GitHub</h1>
        <p>Cliquez ci-dessous pour tester le webhook :</p>
        <a href="/webhookdemo">Tester le webhook</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get('/beats')
def beats():
    """ heart beats """
    return {"result": True}


@app.post('/webhook')
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


@app.get('/webhookdemo')
def webhookdemo():
    """ gitpull de demo """
    with (BASE_DIR / 'demo' / 'demo.json').open(encoding="utf-8") as openjson:
        webhook_github = json.load(openjson)

    return update_webhook(webhook_github)


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