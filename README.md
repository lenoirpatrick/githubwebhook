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

# Installation
```shell
git clone githubwebhook.git
cd githubwebhook
pip install -r requirements.txt --break-system-packages
chmod +x run.sh
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