# 📚 Knowledge Plus IA – App Factory
**Module Odoo 18 · Version 5.0.0**

Module complet de gestion des connaissances BA/Marketing pour l'App Factory.

---

## ✅ Fonctionnalités incluses

| Domaine | Fonctionnalités |
|---|---|
| **Articles** | CRUD, workflow validation, versionnage automatique, archivage |
| **Kanban Agile** | Vue Kanban groupée par statut, progression tâches, priorités |
| **Documents** | Pièces jointes PDF/Word/Excel par article |
| **Chat** | Canal Discuss dédié par article |
| **CDC / BA** | Cahiers des charges complets, exigences MoSCoW, fichiers joints |
| **Liaison Projet** | Articles ↔ Tâches ↔ Projets, couverture documentaire |
| **IA (Claude)** | Résumés, synthèses réunion, templates BA/Marketing, suggestions |

---

## 🚀 Installation

### Prérequis
- Odoo **18.0** Community ou Enterprise
- Module `knowledge` activé (natif Odoo)
- Modules `project` et `mail` (inclus par défaut)
- Python : package `requests` (`pip install requests`)

### Étapes

1. **Copier le module** dans votre dossier addons :
   ```bash
   cp -r knowledge_plus_final_v3/ /path/to/odoo/addons/
   ```
   Ou dans un dossier d'addons personnalisé déclaré dans `odoo.conf` :
   ```ini
   addons_path = /odoo/addons,/path/to/custom_addons
   ```

2. **Mettre à jour la liste des modules** :
   ```bash
   # Via interface Odoo :
   Paramètres → Activer le mode développeur → Apps → "Mettre à jour la liste des apps"

   # Via CLI :
   ./odoo-bin -d NOM_DB -u all --stop-after-init
   ```

3. **Installer le module** :
   - Apps → Rechercher "Knowledge Plus IA" → Installer

4. **Configurer l'Assistant IA** (optionnel mais recommandé) :
   - Knowledge Plus IA → ⚙️ Configuration → 🤖 Assistant IA
   - Créer un profil avec votre clé API Anthropic
   - Obtenez votre clé sur [console.anthropic.com](https://console.anthropic.com)
   - Seuls les administrateurs (groupe `base.group_system`) peuvent voir la clé

---

## 🔑 Configuration de l'IA

```
Knowledge Plus IA
  └── ⚙️ Configuration
        └── 🤖 Assistant IA
              ├── Nom du profil : "Assistant IA App Factory"
              ├── Modèle : Claude Sonnet 4 (recommandé)
              ├── Clé API : sk-ant-api03-...
              └── Tokens max : 1500
```

### Modèles disponibles
| Modèle | Usage recommandé |
|---|---|
| `claude-sonnet-4-20250514` | Résumés, templates, synthèses (recommandé) |
| `claude-opus-4-20250514` | Analyses complexes, CDC détaillés |
| `claude-haiku-4-5-20251001` | Suggestions rapides, petits résumés |

---

## 🗂️ Structure du module

```
knowledge_plus_final_v3/
├── __manifest__.py          # Déclaration du module
├── __init__.py
├── models/
│   ├── knowledge_article.py     # Modèle principal articles
│   ├── knowledge_category.py    # Catégories hiérarchiques
│   ├── knowledge_tag.py         # Tags intelligents
│   ├── knowledge_workflow.py    # Configuration workflow
│   ├── knowledge_document.py    # Documents joints
│   ├── knowledge_ai_assistant.py # Assistant IA (Claude)
│   ├── project_task.py          # Extension tâche projet
│   ├── project_project.py       # Extension projet (smart button CDC)
│   └── ba_specification.py      # Cahiers des charges BA
├── wizard/
│   ├── archive_wizard.py        # Archivage avec motif
│   ├── export_pdf_wizard.py     # Export PDF
│   └── knowledge_ai_wizard.py   # Wizards IA (réunion, template, suggestions)
├── views/
│   ├── knowledge_article_views.xml  # Formulaire + Liste + Kanban
│   ├── knowledge_ai_views.xml       # Config IA + Wizards
│   ├── ba_specification_views.xml   # CDC complet (Kanban inclus)
│   ├── project_task_views.xml       # Extension tâche
│   ├── project_project_views.xml    # Smart button CDC sur projet
│   ├── knowledge_category_views.xml
│   ├── knowledge_tag_views.xml
│   ├── knowledge_workflow_views.xml
│   └── knowledge_menu_views.xml     # Menus complets
├── security/
│   └── ir.model.access.csv          # Droits d'accès
└── data/
    ├── workflow_data.xml            # Config workflow par défaut
    └── ba_sequence.xml              # Séquence CDC/YYYY/0001
```

---

## 📖 Utilisation

### Vue Kanban Agile
Accédez via **Knowledge Plus IA → 🏃 Kanban Agile**.
Les articles sont groupés par statut (Brouillon → En attente → Approuvé → Archivé).
Chaque carte affiche : priorité, catégorie, progression des tâches liées, icône IA si résumé généré.

### Créer un article avec template IA
1. Créer un article → onglet **🤖 Assistant IA**
2. Cliquer **📄 Template BA/Marketing**
3. Choisir le type (Étude de marché, Personas, User Stories…)
4. Décrire le contexte du projet
5. Générer → Insérer dans l'article

### Synthèse de réunion
1. Dans un article → onglet IA → **📋 Synthèse de réunion**
2. Coller vos notes brutes (bullet points, transcript Telegram…)
3. Générer → Insérer dans l'article

### Cahier des charges
**Knowledge Plus IA → 📋 CDC & Études BA → Tous les CDC**
- Créer un CDC lié à un projet
- Ajouter les exigences avec priorité MoSCoW
- Joindre les fichiers Excel/Word/PDF
- Soumettre à révision → Valider → Historique des versions automatique

---

## 🔧 Dépannage

| Problème | Solution |
|---|---|
| "Aucun assistant IA configuré" | Créer un profil dans Configuration → 🤖 Assistant IA |
| "La clé API n'est pas configurée" | Saisir la clé dans le profil IA (admin seulement) |
| Timeout IA | Vérifier la connectivité vers `api.anthropic.com` |
| Module non trouvé | Vérifier `addons_path` dans `odoo.conf` |
| Erreur d'import | Vérifier que `requests` est installé : `pip install requests` |

---

## 📄 Licence
LGPL-3 · App Factory Team
