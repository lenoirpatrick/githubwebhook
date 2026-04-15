""" Mies à jour automatique d'un dépot git """

import subprocess
import os
import json

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

with(open('config/config.json', 'r', encoding="utf-8")) as githubjson:
    config_github = json.load(githubjson)

@app.get("/", response_class=HTMLResponse)
async def home():
    """ Page index """
    # Page HTML simple avec un lien vers /webhookdemo
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
    return {"result": True}, 200

@app.post('/webhook')
def webhook(request: Request):
    """ webhook pour lancer le pull de github """
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
    return "Ignoré : ce n'est pas un push sur la branche principale.", 200


@app.get('/webhookdemo')
def webhookdemo():
    """ gitpull de demo """
    # Vérifier la signature (optionnel)
    with(open('demo/demo.json', 'r', encoding="utf-8")) as openjson:
        webhook_github = json.load(openjson)

    return update_webhook(webhook_github), 200


def update_webhook(webhook_github):
    """ Fonction commune de mise à jour du dépot """
    repo = webhook_github['repository']['full_name']
    path_repo = config_github[repo]['path']
    command = ['git', '-C', path_repo, 'pull']
    result = True
    message = f"repo mis à jour dans {path_repo} avec la commande : {command}"
    if os.path.isdir(path_repo):
        print("Retour en arrière")
        command_reset = ['git', 'reset', '--hard', 'HEAD~1']
        subprocess.run(command_reset, check=True)

        print("Mise à jour du dépot")
        retour_git = subprocess.run(command,
            stdout=subprocess.PIPE,  # Capturer la sortie standard
            stderr=subprocess.PIPE,  # Capturer la sortie d'erreur
            text=True,  # Retourner les sorties sous forme de chaînes de caractères
            check=True
        )

        # Vérifier le code de retour
        if retour_git.returncode == 0:
            print("La commande a réussi.")
            print(f"Sortie standard : {retour_git.stdout}")
            message = retour_git.stdout  # Message de retour en cas de succès
            result = True
        else:
            print(f"La commande a échoué avec le code {retour_git.returncode}.")
            print(f"Sortie d'erreur : {retour_git.stderr}")
            message = retour_git.stderr  # Message d'erreur
            result = False

    retour = {
        "result": result,
        "message": message
    }

    # retour vers home assistant

    return retour


if __name__ == '__main__':
    ip_address = config_github.get("ip")

    uvicorn.run(app, host=ip_address, port=5000)
