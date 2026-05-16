# githubwebhook
Gestion du webhook Github pour déploiement CI/CD sur vos environnements.

![Python 3.11](https://img.shields.io/badge/python-3.11-green.svg?style=flat&logo=python&logoColor=white)
![Python 3.14](https://img.shields.io/badge/python-3.14-green.svg?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green.svg?style=flat&logo=flask&logoColor=white)

[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=lenoirpatrick_githubwebhook&metric=bugs&token=011a45798e3e17e7ef261f6e561aab843f9dadbd)](https://sonarcloud.io/summary/new_code?id=lenoirpatrick_githubwebhook)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=lenoirpatrick_githubwebhook&metric=code_smells&token=011a45798e3e17e7ef261f6e561aab843f9dadbd)](https://sonarcloud.io/summary/new_code?id=lenoirpatrick_githubwebhook)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=lenoirpatrick_githubwebhook&metric=reliability_rating&token=011a45798e3e17e7ef261f6e561aab843f9dadbd)](https://sonarcloud.io/summary/new_code?id=lenoirpatrick_githubwebhook)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=lenoirpatrick_githubwebhook&metric=security_rating&token=011a45798e3e17e7ef261f6e561aab843f9dadbd)](https://sonarcloud.io/summary/new_code?id=lenoirpatrick_githubwebhook)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=lenoirpatrick_githubwebhook&metric=alert_status&token=011a45798e3e17e7ef261f6e561aab843f9dadbd)](https://sonarcloud.io/summary/new_code?id=lenoirpatrick_githubwebhook)

[![GitHub stars](https://img.shields.io/github/stars/lenoirpatrick/githubwebhook)](https://github.com/lenoirpatrick/githubwebhook)
[![GitHub license](https://img.shields.io/github/license/lenoirpatrick/githubwebhook)](https://github.com/lenoirpatrick/githubwebhook)

# Prérequis — Configurer le webhook GitHub

Sur chaque dépôt à déployer, un webhook doit être configuré dans GitHub pour notifier cette application à chaque push.

1. Aller dans **Settings → Webhooks → Add webhook** du dépôt concerné
2. Renseigner les champs suivants :

| Champ | Valeur |
|-------|--------|
| **Payload URL** | `http://<adresse-du-serveur>:5000/webhook` |
| **Content type** | `application/json` |
| **Secret** | La valeur de `webhook_secret` définie dans `config.json` (si configurée) |
| **Which events?** | *Just the push event* |

3. Cocher **Active** et valider.

GitHub enverra alors un événement `POST /webhook` à chaque push. Seuls les pushs sur la branche `main` déclenchent un `git pull`.

# Installation
```shell
git clone githubwebhook.git
cd githubwebhook
pip install -r requirements.txt --break-system-packages
chmod +x run.sh
```

# Configuration

Dans le répertoire `config`, créer un fichier `config.json` :

```json
{
    "ip": "0.0.0.0",
    "webhook_secret": "votre_secret_github",
    "lenoirpatrick/githubwebhook": {
        "path": "/home/pi/app/githubwebhook"
    },
    "lenoirpatrick/autreprojet": {
        "path": "/home/pi/app/autreprojet"
    }
}
```

| Clé | Description |
|-----|-------------|
| `ip` | Adresse d'écoute : `0.0.0.0` pour toutes les interfaces, `127.0.0.1` pour local uniquement |
| `webhook_secret` | Secret partagé avec GitHub pour valider la signature HMAC-SHA256 (optionnel mais recommandé) |
| `"owner/repo"` | Chemin absolu local du dépôt à mettre à jour lors d'un push sur `main` |

Plusieurs dépôts peuvent être configurés simultanément.

# Lancement

## Manuel

```shell
./run.sh
```

Le script installe les dépendances, puis lance l'application en arrière-plan via `nohup`. Les logs sont disponibles dans `nohup.out`.

## Démarrage automatique avec systemd (recommandé)

Pour que le serveur se lance automatiquement au démarrage de Linux, créer un service systemd.

**1. Créer le fichier de service** (adapter les chemins et l'utilisateur) :

```shell
sudo nano /etc/systemd/system/githubwebhook.service
```

```ini
[Unit]
Description=GitHub Webhook Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/app/githubwebhook
ExecStart=/usr/bin/python3 /home/pi/app/githubwebhook/gitpull.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**2. Activer et démarrer le service :**

```shell
sudo systemctl daemon-reload
sudo systemctl enable githubwebhook
sudo systemctl start githubwebhook
```

**3. Vérifier que le service tourne :**

```shell
sudo systemctl status githubwebhook
```

**Commandes utiles :**

```shell
sudo systemctl stop githubwebhook      # arrêter
sudo systemctl restart githubwebhook   # redémarrer
journalctl -u githubwebhook -f         # suivre les logs en temps réel
```