# Projet_module-AGH

Environnement de développement Odoo 18 avec Docker et PostgreSQL, comprenant
des modules personnalisés pour la gestion de l’entreprise et des fonctionnalités
e-commerce. Les modules sont regroupés dans `odoo-development` et `e-commerce`.

## Prérequis

- Docker Desktop avec Docker Compose

## Démarrage

Depuis la racine du projet, lancez :

```powershell
docker compose up -d
```

Odoo est accessible à l’adresse http://localhost:8070.

Les données Odoo et PostgreSQL sont conservées dans des volumes Docker.

## Configuration et sécurité

La configuration locale `config/odoo.conf` n’est pas publiée. Compose utilise
la configuration par défaut de l’image Odoo et les paramètres de connexion
définis dans `docker-compose.yml`.

Les identifiants PostgreSQL présents dans le fichier Compose sont réservés au
développement local. Ne les utilisez pas tels quels sur un serveur ou pour un
service exposé sur Internet.
