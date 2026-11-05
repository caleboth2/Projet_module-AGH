# 🛡️ Guide de Sécurité : Responsable Signature (CISO)
## Gestion des Clés et Signature Mobile

Ce guide détaille les procédures souveraines pour valider et signer les applications mobiles de l'organisation AGH via l'infrastructure isolée.

---

### 1. Politique de Signature
- **Aucune signature automatique** : Chaque build GitHub doit être validé visuellement dans Odoo.
- **Isolement** : La communication avec le coffre-fort Vault se fait exclusivement sur le réseau Docker interne. Tor est utilisé uniquement pour les appels GitHub.
- **Types de Clés** : Utilisation systématique de clés **RSA-4096** générées localement.

### 2. Procédure de Signature (Workflow)
1. **Synchronisation** : Allez dans **Signature Mobile > Demandes** et cliquez sur **[Récupérer les derniers builds]**.
2. **Contrôle du Hash** : Odoo affiche le Hash SHA-256 calculé par GitHub. Si vous avez un doute, comparez-le avec les logs de l'Action GitHub correspondante.
3. **Approbation** : Cliquez sur **[Approuver et Signer]**. Le système enregistre l'auteur de la signature et le token de transaction Vault dans le chatter.

### 3. Sauvegarde et Portabilité (Crucial)
Vos clés sont stockées dans le volume `./vault_data`. En cas de crash serveur sans backup, vos applications sur le Play Store ne pourront plus être mises à jour avec la même identité.

**Procédure de Backup Mensuelle :**
1. Exécutez le script à la racine : `bash backup_vault_keys.sh`.
2. Vérifiez la présence du fichier `.backup.json` pour chaque application.
3. Copiez le dossier `backups/` sur un support physique sécurisé (Clé USB chiffrée).

### 4. Ajout d'une nouvelle Application
1. **Vault** : Créez la clé asymétrique dans le coffre :
   `vault write -f transit/keys/NOM_APP type=rsa-4096 exportable=true allow_plaintext_backup=true`
2. **Odoo** : Ajoutez l'app dans le **Catalogue des Apps** avec le même nom de clé.
3. **GitHub** : Copiez le fichier `.github/workflows/build_aab.yml` dans le nouveau repo.

### 5. Maintenance des Jeton (Secrets)
Si vous soupçonnez une fuite :
1. Révoquez le **Token GitHub** sur votre compte organisationnel.
2. Changez le **VAULT_DEV_ROOT_TOKEN_ID** dans le fichier `.env` et redémarrez les conteneurs.

---
**Responsable Infrastructure** : Bilgassim
**Dernière Révision** : 29 Mai 2026
