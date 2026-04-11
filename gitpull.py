import subprocess
import os
import json

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

with(open('config/config.json', 'r')) as githubjson:
    config_github = json.load(githubjson)


@app.get("/", response_class=HTMLResponse)
async def home():
    # Page HTML simple avec un lien vers /webhookgitlabdemo
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Accueil - Webhook Demo</title>
    </head>
    <body>
        <h1>Bienvenue sur le serveur de webhook GitHub</h1>
        <p>Cliquez ci-dessous pour tester le webhook :</p>
        <a href="/webhookgitlabdemo">Tester le webhook</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.post('/webhook')
def webhook(request: Request):
    # Vérifier la signature (optionnel)
    if request.headers.get('X-Hub-Signature-256'):
        # Ici, vous pouvez vérifier la signature avec votre clé secrète
        pass

    # Récupérer les données du webhook
    webhook_github = request.json

    # Vérifier que c'est un push sur la branche principale
    if webhook_github['ref'] == 'refs/heads/main':
        print("Nouveau push détecté ! Mise à jour en cours...")

        return update_webhook(webhook_github), 200
    else:
        return "Ignoré : ce n'est pas un push sur la branche principale.", 200


@app.get('/webhookgitlabdemo')
def webhookgitlabdemo():
    # Vérifier la signature (optionnel)
    import json
    with(open('demo/demo.json', 'r')) as openjson:
        webhook_github = json.load(openjson)

    return update_webhook(webhook_github)


def update_webhook(webhook_github):
    try:
        repo = webhook_github['repository']['full_name']
        path_repo = config_github[repo]['path']
        command = ['git', '-C', path_repo, 'pull']
        if os.path.isdir(path_repo):
            print("Retour en arrière")
            command_reset = ['git', 'reset', '--hard', 'HEAD~1']
            subprocess.run(command_reset)

            print("Mise à jour du dépot")
            subprocess.run(command)
        return f"repo mis à jour dans {path_repo} avec la commande : {command}"
    except Exception as ex:
        return ex


if __name__ == '__main__':
    ip_address = config_github.get("ip")

    uvicorn.run(app, host=ip_address, port=5000)