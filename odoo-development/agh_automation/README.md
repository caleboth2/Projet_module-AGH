# AGH Automation (`agh_automation`)

## 🛡️ Présentation
Le module **AGH Automation** est le "moteur de pilotage" financier et opérationnel de l'instance Odoo. Il automatise les processus métiers récurrents et cruciaux de l'agence, permettant à la Direction de se concentrer sur l'analyse plutôt que sur l'exécution manuelle.

Il gère notamment les relances, les alertes de trésorerie, la conformité fiscale marocaine (TVA), et la surveillance de l'état de santé (KPIs) de l'entreprise.

## 🏗️ Architecture du Code
Le module est structuré pour garantir la traçabilité et l'exécution asynchrone des tâches (Cron) :

- **`models/agh_scheduled_action.py`** : Le cœur de l'exécution. Contient la logique des crons (clôture mensuelle, export TVA DGI, sauvegardes DB).
- **`models/agh_alert_rule.py`** : Moteur de règles configurables permettant de déclencher des notifications basées sur des conditions (ex: factures en retard, échéances fournisseurs).
- **`models/agh_automation_config.py`** : Paramètres globaux de l'automatisation (seuils, adresses e-mail de notification).
- **`models/agh_workflow_log.py`** : Système de journalisation (logs) assurant une traçabilité parfaite de chaque exécution automatique.
- **`data/ir_cron_data.xml` & `alert_rules_data.xml`** : Les tâches planifiées et règles par défaut pré-embarquées à l'installation.
- **`views/automation_dashboard_views.xml`** : Interface de pilotage macro pour la Direction Générale.

## 🔗 Dépendances
Le module se connecte au cœur de l'écosystème AGH et nécessite :
- `base_automation` : Moteur de base d'Odoo.
- `mail` : Pour l'envoi des alertes et relances.
- `account` : Pour l'accès à la comptabilité standard.
- `agh_invoice_customer` : Pour interagir avec les flux de facturation spécifiques de l'agence.
- `agh_fiscal_maroc` : Requis pour déclencher les automatisations légales (Export DGI).

## 🚀 Évolutions & Améliorations Futures (Roadmap)
Dans le cadre de la transition vers une architecture "Auto-Pilotée" (Agentic Workflow), ce module servira de socle pour l'intégration de l'Intelligence Artificielle :

1.  **Intégration de l'Agent IA "Chaser"** :
    *   *Aujourd'hui* : Les règles d'alerte envoient des e-mails ou créent des tickets de manière rigide (règles métier classiques).
    *   *Demain* : L'Agent Chaser utilisera les données de `agh_alert_rule` pour analyser le contexte d'un retard (client difficile, historique des échanges) et générer/adapter automatiquement le ton de la relance.
2.  **Couplage avec le "Master Director Dashboard"** :
    *   Les logs d'automatisation et les KPIs calculés ici alimenteront le tableau de bord de Santé Opérationnelle (Croisement Coûts / Vélocité technique).
3.  **Résolution Active** :
    *   Permettre aux scripts d'automatisation de déclencher des Webhooks pour couper/restaurer des accès (en lien avec le futur module *Automated Offboarding*).

---
*Maintenu par Bilgassim - Infrastructure AGH Agency - Mai 2026*
