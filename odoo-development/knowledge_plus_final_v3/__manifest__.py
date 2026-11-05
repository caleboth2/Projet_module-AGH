{
    'name': 'Knowledge Plus IA – App Factory',
    'version': '18.0.5.0.0',
    'category': 'Knowledge',
    'summary': 'Base de connaissances BA/Marketing avec IA, Kanban Agile, CDC et templates',
    'description': """
        Module complet de gestion des connaissances pour l'App Factory :

        *** ARTICLES & WORKFLOW ***
        - Articles hiérarchisés avec workflow de validation (Brouillon → Validation → Approuvé)
        - Versionnage automatique avec historique
        - Documents joints (PDF, Excel, Word, Images)
        - Chat intégré par article (canal Discuss dédié)
        - Archivage avec motif et suppression définitive sécurisée

        *** INTÉGRATION PROJET AGILE ***
        - Vue Kanban des articles (méthode Agile)
        - Liaison bidirectionnelle Articles ↔ Tâches Projet
        - Suivi de couverture documentaire par tâche
        - Progression des tâches liées à chaque article

        *** CAHIERS DES CHARGES & ÉTUDES BA ***
        - CDC complets avec exigences MoSCoW
        - Fichiers joints (Excel, PDF, Word) avec versionnage
        - Smart button CDC sur les fiches Projet
        - Liaison Articles ↔ CDC ↔ Tâches

        *** ASSISTANT IA (Ollama Local) ***
        - Souveraineté totale : Utilisation de Llama 3 en local.
        - Résumés automatiques d'articles longs
        - Synthèse de réunion à partir de notes brutes
        - Détection intelligente du contenu manquant
        - Templates pré-remplis : Étude de marché, Personas, User Stories,
          Décisions stratégiques, Post-Mortem, Analyse concurrentielle
        - Configuration centralisée (URL locale, modèle)
    """,
    'author': 'App Factory Team',
    'website': 'https://www.yourcompany.com',
    'depends': ['mail', 'project', 'hr'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'security/ir.model.access.csv',
        'data/workflow_data.xml',
        'data/ba_sequence.xml',
        'data/agile_cron_data.xml',
        'views/knowledge_category_views.xml',
        'views/knowledge_tag_views.xml',
        'views/knowledge_article_views.xml',
        'views/knowledge_workflow_views.xml',
        'views/knowledge_ai_views.xml',
        'views/ba_specification_views.xml',
        'views/agile_epic_views.xml',
        'views/agile_sprint_views.xml',
        'views/agile_project_views.xml',
        'views/project_task_views.xml',
        'views/project_project_views.xml',
        'views/knowledge_menu_views.xml',
        'views/agile_menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'icon': '/knowledge_plus_final_v3/static/description/icon.png',
}
