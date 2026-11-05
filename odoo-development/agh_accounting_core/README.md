# 🇲🇦 AGH Comptabilité Maroc — Suite Odoo 18 Community

> Suite logicielle complète pour la gestion comptable, fiscale et RH d'une entreprise marocaine, conforme **Plan Comptable Marocain (PCM)** et exigences **DGI / CNSS**.
>
> Compatible **Odoo 18 Community** — aucune dépendance Enterprise.
>
> Auteur : **AGH Data Agency**

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Liste des modules](#liste-des-modules)
3. [Organisation des menus](#organisation-des-menus)
4. [Prérequis](#prérequis)
5. [Installation](#installation)
6. [Ordre d'installation des modules](#ordre-dinstallation-des-modules)
7. [Configuration initiale de la société](#configuration-initiale-de-la-société)
8. [Notes de version](#notes-de-version)
9. [Dépendances Python externes](#dépendances-python-externes)
10. [Dépannage](#dépannage)
11. [Licence & Contact](#licence--contact)

---

## Vue d'ensemble

La suite **AGH Comptabilité Maroc** comprend **9 modules Odoo 18** indépendants mais conçus pour fonctionner ensemble :

| Domaine | Modules |
|---|---|
| 🧮 Exercice fiscal | `account_fiscal_year` |
| 🏦 Comptabilité (PCM) | `agh_accounting_core` |
| 🧾 Facturation | `agh_invoice_customer`, `agh_invoice_supplier` |
| 💰 Trésorerie & effets | `agh_treasury` |
| 🏛️ Fiscalité (TVA / IS / IR / CM / TP) | `agh_fiscal_maroc` |
| 📊 Reporting (Bilan, CPC, KPI) | `agh_reporting` |
| ⚙️ Automatisation | `agh_automation` |
| 👤 RH / Attestations | `agh_employee_certificate` |

---

## Liste des modules

### 1. `account_fiscal_year` — Exercice fiscal & clôture
Gestion des exercices comptables, dates de verrouillage et assistant de clôture annuelle.

### 2. `agh_accounting_core` — Cœur comptable PCM
Plan Comptable Marocain à 4 chiffres, journaux préconfigurés (VT, AC, BQ, CS, OD), devise MAD par défaut, champs marocains sur la fiche société (ICE, IF, RC, CNSS, Patente).

### 3. `agh_invoice_customer` — Facturation client
Numérotation séquentielle légale `FAC-YYYY-NNNN`, mentions obligatoires ICE/IF, modèles PDF marocains, gestion des avoirs, tableau de bord recouvrement, relances automatiques.

### 4. `agh_invoice_supplier` — Facturation fournisseur
Saisie rapide avec OCR, contrôle 3 voies (BC → BR → facture), retenue à la source (RAS), préparation virements bancaires.

### 5. `agh_treasury` — Trésorerie & effets de commerce
Multi-banques, import relevés (CSV / OFX / MT940), rapprochement assisté, portefeuille d'effets de commerce, prévisions à 30/60/90 jours.

### 6. `agh_fiscal_maroc` — Fiscalité marocaine
Déclarations TVA (CA3), IS avec 4 acomptes trimestriels, Cotisation Minimale (0,5 % du CA), Taxe Professionnelle, calendrier fiscal DGI, export SIMPL-TVA.

### 7. `agh_reporting` — Reporting financier
**Bilan Comptable PCM** (raccourci direct dans le menu Comptabilité), CPC, tableau de flux de trésorerie, balance âgée clients/fournisseurs, grand-livre, KPIs (CA, MB, DSO, DPO, BFR).

### 8. `agh_automation` — Alertes & planificateur
Crons préconfigurés, règles d'alertes configurables, dashboard de supervision, logs d'exécution.

### 9. `agh_employee_certificate` — Attestations RH
Génération PDF des attestations (Travail, Salaire, Stage, Congé, Fin de Contrat, Prise en Charge), gestion complète des stagiaires (`intern.profile`), envoi email automatique. **Tous les menus sont intégrés sous Employees → Attestations.**

---

## Organisation des menus

Les menus ont été réorganisés pour une meilleure ergonomie :

### 👤 Employees → Attestations
- **Attestations Employés** — émission et suivi des attestations RH (`hr.certificate`)
- **Attestations Stagiaires** — gestion des fiches stagiaires et de leurs attestations (`intern.profile`)

> ⚠️ Auparavant, « Attestations Stagiaires » apparaissait comme un module séparé au niveau supérieur du menu principal. Il est désormais correctement intégré au menu standard **Employees**.

### 🧮 Comptabilité
Le menu **Comptabilité** (`account.menu_finance`) regroupe désormais :

- **Clients** — factures, avoirs, paiements
- **Fournisseurs** — factures, avoirs, paiements
- **Comptabilité** — pièces, écritures, exercices
- **Bilan Comptable** ✅ *(nouveau raccourci direct, conforme PCM)*
- **Trésorerie** — comptes bancaires, effets de commerce, prévisions
- **Reporting AGH**
  - États financiers : Bilan PCM, CPC, Tableau de flux de trésorerie
  - Balances : Balance âgée clients, Balance âgée fournisseurs, Grand-livre
  - Tableau de bord KPIs
  - Planification rapports
  - Configuration KPIs
- **Configuration** — Plan comptable, journaux, taxes

### 🏛️ Fiscalité Maroc (menu autonome)
- TVA → Déclarations TVA, Demandes de remboursement
- Impôt sur les Sociétés → Déclarations IS
- Cotisation Minimale
- Taxe Professionnelle
- Calendrier fiscal

### 🧾 Facturation Client (menu autonome)
- Factures → Factures Clients, Tableau de bord Recouvrement
- Clients

### 🏬 Fournisseurs AGH (menu autonome)
- Factures Fournisseurs
- Retenue à la Source → Retenues, Déclarations mensuelles, Génération
- Rapprochement 3 voies

---

## Prérequis

| Outil | Version minimale |
|---|---|
| Odoo | 18.0 Community |
| Python | 3.10+ |
| PostgreSQL | 14+ |
| OS | Ubuntu 22.04+ / Debian 12+ |
| RAM | 4 Go (8 Go recommandé) |
| Disque | 10 Go libres |

---

## Installation

### Méthode 1 — Manuelle

```bash
# 1. Décompresser l'archive dans le dossier d'addons personnalisés
unzip AGH_Comptabilite_Maroc.zip -d /opt/odoo/custom_addons/

# 2. Installer les dépendances Python
pip3 install pdfplumber pytesseract pillow ofxparse pandas python-dateutil

# 3. Ajouter le chemin dans odoo.conf
# addons_path = /usr/lib/python3/dist-packages/odoo/addons,/opt/odoo/custom_addons/AGH_Comptabilite_Maroc

# 4. Redémarrer Odoo et mettre à jour la liste des applications
sudo systemctl restart odoo
# ou
./odoo-bin -c odoo.conf -u all
```

Puis, dans l'interface :

1. Activer le **mode développeur** (Réglages → Activer le mode développeur)
2. Aller dans **Apps → Mettre à jour la liste des applications**
3. Rechercher `agh_` et installer les modules dans l'ordre ci-dessous

### Méthode 2 — Docker

Si vous utilisez la stack Docker fournie :

```bash
# Copier les modules dans le dossier monté
cp -r AGH_Comptabilite_Maroc/* ./custom_addons/

# Redémarrer le conteneur
docker-compose restart web

# Installer les dépendances Python dans le conteneur
docker-compose exec web pip install pdfplumber pytesseract pillow ofxparse pandas python-dateutil
docker-compose restart web
```

---

## Ordre d'installation des modules

⚠️ **Respecter cet ordre pour éviter les erreurs de dépendances :**

| # | Module | Description |
|---|---|---|
| 1 | `account_fiscal_year` | Gère l'exercice fiscal et la clôture annuelle |
| 2 | `agh_accounting_core` | Cœur — Plan Comptable Marocain, journaux, dates de verrouillage |
| 3 | `agh_invoice_customer` | Facturation client (BL → BC → facture, modèles) |
| 4 | `agh_invoice_supplier` | Facturation fournisseur (réception, RAS, OCR) |
| 5 | `agh_treasury` | Trésorerie, effets de commerce, rapprochement |
| 6 | `agh_fiscal_maroc` | TVA, IS, IR, CNSS, CM, Taxe Professionnelle |
| 7 | `agh_reporting` | Bilan, CPC, flux, balance âgée, grand-livre, KPI |
| 8 | `agh_automation` | Alertes, scheduler de rapports, rappels |
| 9 | `agh_employee_certificate` | Attestations RH (employés + stagiaires) |

---

## Configuration initiale de la société

Avant d'utiliser la suite, configurer la société dans **Réglages → Sociétés** :

- **Devise** : MAD (Dirham marocain)
- **Pays** : Maroc
- **ICE**, **IF**, **RC**, **CNSS**, **Patente** : à renseigner sur la fiche société (champs ajoutés par `agh_accounting_core`)
- **Date de verrouillage** : à définir après la première déclaration TVA validée (exigence DGI)

---

## Notes de version

### v18.0.2.2.0 — Corrections d'installation Odoo 18 + gestion fournisseurs complète

**🐛 Corrections techniques (compatibilité Odoo 18 stricte)**

- ✅ **`ir.cron`** : suppression du champ `numbercall` retiré dans Odoo 18 (`agh_fiscal_maroc/data/sequence_data.xml`)
- ✅ **`account.tax`** : ajout des **groupes de TVA** (`tax_group_id` désormais obligatoire) — création de 3 groupes (TVA Collectée / Déductible / Exonérée) et liaison sur les 11 taxes marocaines (`agh_fiscal_maroc/data/tax_data.xml`)
- ✅ **Références XML** : correction des `external ID not found` dans `agh_reporting/views/menu_views.xml` — les références internes au même module n'utilisent plus de préfixe erroné (les anciens préfixes `reporting_dashboard_views.*` et `report_scheduler_views.*` correspondaient à des noms de fichiers, pas à des modules)
- ✅ Toutes les actions des menus Reporting sont désormais déclarées explicitement avant les `<menuitem>` qui les utilisent

**✨ Gestion complète des fournisseurs (`agh_invoice_supplier`)**

Le menu « Fournisseurs AGH » est renommé **« Fournisseurs »** et structuré pour couvrir tout le cycle achat :

```
Fournisseurs
├── Tableau de bord
├── Fournisseurs
│   ├── Liste des fournisseurs (filtre supplier_rank > 0)
│   └── Produits / Articles fournisseurs
├── Achats
│   ├── Demandes de prix
│   ├── Bons de commande
│   └── Réceptions (Bons de réception)
├── Factures & Paiements
│   ├── Factures Fournisseurs
│   ├── Avoirs Fournisseurs
│   ├── Paiements Fournisseurs
│   └── Rapprochement 3 voies
└── Retenue à la Source
    ├── Retenues à la source
    ├── Déclarations mensuelles
    └── Générer une déclaration
```

- ✅ Vue fiche fournisseur enrichie : onglet **« Informations Maroc & RAS »** (ICE, IF, RC, CNSS, Patente, soumission RAS, type & taux RAS, fournisseur stratégique)
- ✅ Vue liste fournisseurs : colonnes ICE, IF, RAS, stratégique
- ✅ Vue recherche : filtres « Soumis à RAS » et « Fournisseurs stratégiques », recherche par ICE / IF

### v18.0.2.1.0 — Réorganisation des menus

- ✅ **Attestations Stagiaires** : déplacé du niveau supérieur vers **Employees → Attestations → Attestations Stagiaires**
- ✅ **Attestations Employés** (`hr.certificate`) : ajout d'un menu dédié sous **Employees → Attestations → Attestations Employés**
- ✅ **Bilan Comptable** : ajout d'un raccourci direct dans le menu **Comptabilité**
- 🐛 Aplatissement des dossiers imbriqués `agh_fiscal_maroc/agh_fiscal_maroc/` et `agh_reporting/agh_reporting/`
- 🧹 Nettoyage des `__pycache__`

---

## Dépendances Python externes

```bash
pip install pdfplumber pytesseract pillow ofxparse pandas python-dateutil
```

| Bibliothèque | Module qui l'utilise | Usage |
|---|---|---|
| `pdfplumber` | `agh_invoice_supplier` | Extraction texte PDF |
| `pytesseract` | `agh_invoice_supplier` | OCR images / factures scannées |
| `pillow` | `agh_invoice_supplier` | Traitement images |
| `ofxparse` | `agh_treasury` | Import relevés OFX |
| `pandas` | `agh_treasury` | Import relevés CSV |
| `python-dateutil` | `agh_treasury` | Parsing dates flexibles |

Pour Tesseract (OCR), installer aussi le binaire système :

```bash
sudo apt install -y tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara
```

---

## Dépannage

**Module absent de la liste des applications**
```bash
# Vérifier que le chemin addons_path inclut le dossier AGH_Comptabilite_Maroc
# Puis :
./odoo-bin -c odoo.conf --update-list
```

**Le menu « Attestations Stagiaires » apparaît toujours en haut**
Mettre à jour le module après remplacement des fichiers :
```bash
./odoo-bin -c odoo.conf -u agh_employee_certificate -d <votre_base>
```

**« Bilan Comptable » introuvable dans le menu Comptabilité**
S'assurer que `agh_reporting` est bien installé (pas seulement chargé), puis :
```bash
./odoo-bin -c odoo.conf -u agh_reporting -d <votre_base>
```

**Erreur XML au chargement**
```bash
# Tester un fichier XML hors d'Odoo
python3 -c "import xml.etree.ElementTree as ET; ET.parse('chemin/vers/vue.xml')"
```

**Bibliothèque Python manquante (ex. `ModuleNotFoundError: No module named 'pdfplumber'`)**
```bash
pip install pdfplumber pytesseract pillow ofxparse pandas python-dateutil
sudo systemctl restart odoo
```

**Accès refusé sur un modèle**
Vérifier `security/ir.model.access.csv` du module concerné.

---

## Licence & Contact

- **Auteur** : AGH Data Agency
- **Site web** : https://agh-data-agency-holding.netlify.app
- **Licence** : LGPL-3
- **Odoo version** : 18.0 Community Edition
- **Conforme** : Plan Comptable Marocain (PCM) • DGI Maroc • CNSS • TVA • IS • IR
