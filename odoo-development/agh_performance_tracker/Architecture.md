# Documentation Technique & Architecture : agh_performance_tracker

## 1. Vision Générale
Le module **AGH Performance Tracker (PMS)** est une solution souveraine de gestion des performances intégrée à Odoo 18. Il permet d'évaluer les collaborateurs de manière objective en combinant des métriques automatisées (Projets, Timesheets) et une analyse qualitative assistée par une Intelligence Artificielle locale (Ollama).

## 2. Architecture Fonctionnelle

### 2.1 Modèle de Données Principal (`agh.kpi.evaluation`)
C'est le pivot du module. Il centralise :
- **Métriques de Temps** : Liées à `hr.employee` et filtrées par périodes (`period_start`, `period_end`).
- **KPI Quantitatifs (Automatisés)** :
    - **Quantité** : Heures réelles vs Heures théoriques (35h/sem).
    - **Assiduité** : Jours travaillés vs Jours ouvrés + Ponctualité (Seuil 09:15).
    - **Deadline** : Ratio de tâches livrées à temps dans `project.task`.
- **Analyse Qualitative** : Points forts, axes d'amélioration et résumé IA.

### 2.2 Intégration IA (Ollama)
L'architecture repose sur une IA locale pour garantir la confidentialité des données RH :
- **Service** : Ollama (API REST sur port 11434).
- **Modèle conseillé** : `llama3` ou `mistral`.
- **Flux** : Construction d'un prompt structuré (JSON) -> Appel asynchrone (via Wizard) -> Stockage du résumé dans `ollama_summary`.

## 3. Détails Techniques & Automatisations

### 3.1 Calculateur de KPIs (`action_compute_kpis`)
Cette méthode orchestre la récupération des données :
- **Tâches** : Recherche les tâches dont la `date_deadline` ou la `date_last_stage_update` tombe dans la période d'évaluation.
- **Feuilles de Temps** : Analyse les lignes `account.analytic.line` en utilisant les champs Datetime OCA (`date_time`) pour une précision à la minute.

### 3.2 Workflow de l'évaluation
1. **Draft** : Création et définition de la période.
2. **In Progress** : Phase de calcul (Bouton "Calculer les KPI") et saisie des commentaires qualitatifs.
3. **Done** : Finalisation par le manager.
4. **Validated** : Validation finale par l'admin RH (verrouillage des scores).

## 4. Sécurité et Accès
- **Utilisateur Performance** : Lecture seule de ses propres évaluations.
- **Évaluateur (Manager)** : Création et modification des évaluations de son équipe.
- **Admin RH** : Contrôle total et validation finale.

## 5. Handover (Passation)

### Installation & Dépendances
- **Dépendances Odoo** : `hr`, `project`, `hr_timesheet`, `mail`.
- **Dépendances OCA** : `hr_timesheet_begin_end`, `hr_timesheet_time_control_begin_end` (requis pour les champs Datetime).

### Configuration Post-Installation
1. Aller dans **Paramètres > Paramètres Généraux > AGH Performance Tracker**.
2. Configurer l'URL Ollama (ex: `http://localhost:11434`).
3. Saisir le nom du modèle local à utiliser.

### Maintenance
- **Séquençage** : Les références sont générées via la séquence `agh.kpi.evaluation`.
- **Logs** : Les erreurs de connexion Ollama sont tracées dans les logs Odoo et via des notifications UI (Service indisponible).

## 6. Évolutions Futures (Backlog)
- [ ] Connecter le module `agh_employee_certificate` pour générer des certificats de réussite automatique.
- [ ] Ajouter une vue Dashboard "Manager" pour comparer les performances inter-équipes.
- [ ] Intégrer l'analyse de sentiment sur les commentaires des tâches pour affiner le score de "Qualité".
