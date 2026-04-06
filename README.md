# githubwebhook
Gestion du webhook Github pour déploiement CI/CD sur vos environnements.

# Installation
```shell
git clone githubwebhook.git
cd githubwebhook
pip install -r requirements --break-system-packages
```

# Configuration
Dans le répertoire config, créer un fichier config.json
```json
{
	"lenoirpatrick/githubwebhook": {
		"path": "/home/pi/app/githubwebhook"
	}
}
```

# Lancement
Executer le script ```run.sh```