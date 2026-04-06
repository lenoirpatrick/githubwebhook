from flask import Flask, request, jsonify, render_template_string
import subprocess
import os
import json

app = Flask(__name__)

with(open('config.json', 'r')) as githubjson:
    config_github = json.load(githubjson)

@app.route('/')
def home():
    # Page HTML simple avec un lien vers /webhooktest
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
    return render_template_string(html_content)

@app.route('/webhook', methods=['POST'])
def webhook():
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

@app.route('/webhookdemo', methods=['GET'])
def webhookdemo():
    # Vérifier la signature (optionnel)
    import json
    with(open('demo.json', 'r')) as openjson:
        webhook_github = json.load(openjson)
    
    return update_webhook(webhook_github)

def update_webhook(webhook_github):
    try:
        repo = webhook_github['repository']['full_name']
        path_repo = config_github[repo]['path']
        command = ['git', '-C', path_repo, 'pull']
        if os.path.isdir(path_repo):
            command_reset = ['git', 'reset', '--hard', 'HEAD~1']
            subprocess.run(command_reset)
            subprocess.run(command)
        return f"repo mis à jour dans {path_repo} avec la commande : {command}"
    except Exception as ex:
        return ex


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)