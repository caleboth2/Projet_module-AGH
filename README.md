# Odoo Docker project

Environnement de développement basé sur Odoo 18 et PostgreSQL 15. Le dépôt
contient les modules personnalisés dans `odoo-development` ainsi que les
modules e-commerce dans `e-commerce`.

## Démarrage

Prérequis : Docker Desktop avec Docker Compose.

```powershell
docker compose up -d
```

Odoo est accessible à l'adresse http://localhost:8070.

Les identifiants PostgreSQL `odoo` utilisés par la configuration Compose sont
réservés au développement local. Ne pas exposer cette configuration telle
quelle sur un serveur ou sur Internet.

La configuration locale `config/odoo.conf` n'est pas publiée. Compose utilise
la configuration fournie par l'image Odoo et les paramètres de connexion
définis dans `docker-compose.yml`.
