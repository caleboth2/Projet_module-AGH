# AGH Performance Tracker (PMS)

Module Odoo 18 de suivi des performances pour RH, Marketing, QA et DEV.

---

## Structure du module

```
agh_performance_tracker/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── agh_kpi_evaluation.py      # Modèle principal d'évaluation
│   ├── agh_kpi_criteria.py        # Critères KPI + vue synthèse SQL
│   └── res_config_settings.py     # Paramètres Ollama
├── wizard/
│   ├── __init__.py
│   ├── agh_ollama_summary_wizard.py
│   └── agh_ollama_summary_wizard_views.xml
├── views/
│   ├── agh_kpi_evaluation_views.xml    # Form, list, kanban, graph, pivot
│   ├── agh_kpi_criteria_views.xml      # Critères + synthèse
│   ├── agh_performance_dashboard_views.xml
│   ├── res_config_settings_views.xml
│   └── menu.xml
├── security/
│   ├── agh_performance_groups.xml
│   └── ir.model.access.csv
├── data/
│   └── agh_performance_data.xml        # Séquence, critères par défaut, paramètres
└── static/
    └── src/css/performance_tracker.css
```

---

## Modèle : `agh.kpi.evaluation`

| Champ               | Type          | Description                                      |
|---------------------|---------------|--------------------------------------------------|
| `employee_id`       | Many2one      | Collaborateur évalué                             |
| `manager_id`        | Many2one      | Manager évaluateur                               |
| `team_category`     | Selection     | RH / MK / QA / DEV / Autre                      |
| `period_start/end`  | Date          | Période couverte                                 |
| `score_assiduite`   | Selection 0-5 | Note assiduité (manuelle)                        |
| `score_quantite`    | Selection 0-5 | Note quantité (manuelle)                         |
| `score_qualite`     | Selection 0-5 | Note qualité (manuelle)                          |
| `tasks_total`       | Integer       | Nombre total de tâches                           |
| `tasks_on_time`     | Integer       | Tâches livrées à temps                           |
| `deadline_rate`     | Float         | Taux calculé automatiquement (%)                 |
| `score_deadline`    | Selection 0-5 | **Score calculé automatiquement**                |
| `score_total`       | Float         | Somme des 4 critères (max 20)                    |
| `score_total_percent` | Float       | Score en pourcentage                             |
| `performance_level` | Selection     | Top / Bon / Moyen / Insuffisant                  |
| `ollama_summary`    | Text          | Résumé généré par IA                             |
| `ollama_status`     | Selection     | not_generated / success / error / unavailable    |

---

## Calcul automatique du score Deadline

| Taux de livraison | Score |
|-------------------|-------|
| 0%                | 0     |
| 1% – 39%          | 1     |
| 40% – 59%         | 2     |
| 60% – 79%         | 3     |
| 80% – 94%         | 4     |
| 95% – 100%        | 5     |

---

## Intégration Ollama

Ollama est un service LLM local. Le module l'appelle via l'API REST `/api/generate`.

**Gestion des erreurs :**
- `urllib.error.URLError` → service indisponible (affichage d'avertissement, pas de crash)
- `json.JSONDecodeError` / réponse vide → erreur applicative (log + notification)
- Timeout configurable (défaut : 60s)

**Configuration :** Odoo → Configuration → Paramètres → section "AGH Performance Tracker"

---

## Installation

### Ubuntu (natif)

```bash
# 1. Copier le module dans le répertoire addons Odoo
cp -r agh_performance_tracker /opt/odoo/addons/

# 2. Redémarrer Odoo
sudo systemctl restart odoo

# 3. Activer le mode développeur dans Odoo
# Paramètres → Activer le mode développeur

# 4. Mettre à jour la liste des modules
# Applications → Mettre à jour la liste des applications

# 5. Installer le module
# Rechercher "AGH Performance Tracker" → Installer
```

### Docker Compose

```yaml
version: '3.8'
services:
  odoo:
    image: odoo:18.0
    ports:
      - "8069:8069"
    volumes:
      - ./agh_performance_tracker:/mnt/extra-addons/agh_performance_tracker
      - odoo-data:/var/lib/odoo
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    depends_on:
      - db
    command: -- --dev=reload

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
    volumes:
      - db-data:/var/lib/postgresql/data

  # Ollama (optionnel – si vous voulez l'IA)
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

volumes:
  odoo-data:
  db-data:
  ollama-data:
```

```bash
# Démarrer les services
docker-compose up -d

# Télécharger un modèle Ollama (ex: llama3)
docker exec -it <ollama_container> ollama pull llama3

# Dans Odoo, configurer l'URL Ollama :
# http://ollama:11434  (si même réseau Docker)
# http://localhost:11434  (si Ollama sur la machine hôte)
```

---

## Droits d'accès

| Groupe              | Lecture | Écriture | Création | Suppression |
|---------------------|---------|----------|----------|-------------|
| Utilisateur         | ✅      | ❌       | ❌       | ❌          |
| Évaluateur (Manager)| ✅      | ✅       | ✅       | ❌          |
| Admin RH            | ✅      | ✅       | ✅       | ✅          |
