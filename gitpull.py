from flask import Flask, request, abort
import subprocess
import os

app = Flask(__name__)

# Clé secrète pour sécuriser le webhook (optionnel mais recommandé)
SECRET = "votre_cle_secrete"

@app.route('/webhook', methods=['POST'])
def webhook():
    # Vérifier la signature (optionnel)
    if request.headers.get('X-Hub-Signature-256'):
        # Ici, vous pouvez vérifier la signature avec votre clé secrète
        pass

    # Récupérer les données du webhook
    data = request.json
    print(data)

    # Vérifier que c'est un push sur la branche principale
    if data['ref'] == 'refs/heads/main':
        print("Nouveau push détecté ! Mise à jour en cours...")

        # Mettre à jour le dépôt local
        subprocess.run(['git', '-C', '/chemin/vers/votre/depot', 'pull'])

        # Redémarrer le service ou exécuter un script de déploiement
        subprocess.run(['sudo', 'systemctl', 'restart', 'votre_service'])

        return "Mise à jour effectuée !", 200
    else:
        return "Ignoré : ce n'est pas un push sur la branche principale.", 200

@app.route('/webhooktest', methods=['GET'])
def webhooktest():
    # Vérifier la signature (optionnel)
    import json
    with(open('demo.json', 'r')) as openjson:
        webhook_github = json.load(openjson)
    
    print("hello")
    print(webhook_github['repository']['full_name'])

    subprocess.run(['git', '-C', '/home/pi/gitpull/test/pigpio', 'pull'])
    return webhook_github['repository']['full_name']

    # return "Ignoré : ce n'est pas un push sur la branche principale.", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)