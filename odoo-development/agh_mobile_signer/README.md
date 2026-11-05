# Sovereign Mobile Signer (`agh_mobile_signer`)

## 🛡️ Présentation
Ce module Odoo transforme votre instance locale en une **Tour de Contrôle souveraine** pour la signature d'applications mobiles (Android & iOS). Il permet de valider humainement les builds générés sur GitHub avant de déclencher une signature via un coffre-fort local (HashiCorp Vault), le tout en restant totalement invisible sur Internet grâce au réseau **Tor**.

## 🏗️ Architecture du Code
Le module suit une structure standard Odoo 18.0 avec une orientation sécurité forte :

- **`models/sign_request.py`** : Cœur de la logique métier. Gère le cycle de vie des demandes. Les appels GitHub utilisent le proxy Tor, tandis que les appels Vault sont directs (réseau local).
- **`models/res_config_settings.py`** : Extension des paramètres système pour stocker de manière sécurisée les URLs et Tokens.
- **`views/`** : Interfaces utilisateur améliorées avec boutons de synchronisation manuelle et notifications en temps réel.
- **`data/cron.xml`** : Automatisation du "Polling" GitHub (vérification toutes les 10 min).
- **`security/`** : Restriction stricte des accès au groupe **Administrateur** (`base.group_system`).

## ⚙️ Configurations Obligatoires
Pour que le module soit opérationnel, rendez-vous dans **Signature Mobile > Configuration > Paramètres** :

1.  **Proxy Tor** : Utilisez le format `socks5h://tor:9050` (indispensable pour l'anonymat).
2.  **GitHub Token** : Un *Personal Access Token* avec les droits `repo` et `actions` (pour lire les dépôts privés).
3.  **Dépôt GitHub** : Automatisé via le Catalogue des Apps.
4.  **URL Coffre-fort (Vault)** : `http://vault:8200` (adresse Docker interne).
5.  **Token Vault** : Le token d'accès (`agh_master_token` ou restreint).

## 🔄 Mode de Fonctionnement (Workflow)
1.  **Build** : GitHub Actions compile l'app et génère un artefact nommé `*-build-info`.
2.  **Détection** : Utilisez le bouton **"Récupérer les derniers builds"** dans Odoo pour forcer une détection immédiate via Tor.
3.  **Validation** : Vérifiez le Hash SHA-256 récupéré.
4.  **Signature** : Cliquez sur **"Approuver et Signer"**. Odoo communique directement avec Vault (hors Tor) pour une sécurité maximale et éviter les erreurs de routage interne.
5.  **Traçabilité** : Chaque signature est enregistrée dans le chatter avec le hash de transaction Vault.

## 🔒 Sauvegarde Souveraine
Un script `backup_vault_keys.sh` est disponible à la racine du projet pour :
- Sauvegarder les clés de signature RSA-4096 individuellement.
- Effectuer une image complète de la base de données Vault.
**Procédure** : Exécutez `./backup_vault_keys.sh` régulièrement et stockez le dossier `backups` hors-ligne.

---
*Maintenu par Bilgassim - Infrastructure AGH Agency - Mai 2026*
