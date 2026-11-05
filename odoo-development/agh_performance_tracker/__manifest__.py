# -*- coding: utf-8 -*-
{
    'name': 'AGH Performance Tracker (PMS)',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Évaluation des performances RH, MK, QA, DEV avec IA Ollama',
    'description': """
        Module de suivi des performances (PMS) pour AGH Data Agency Holding.
        
        Fonctionnalités :
        - Évaluation des collaborateurs sur 4 critères (0-5)
        - Calcul automatique du score Deadline
        - Résumé IA via Ollama (local LLM)
        - Tableaux de bord et rapports
        - Identification des top performers
    """,
    'author': 'AGH Data Agency Holding',
    'website': 'https://www.agh-data.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'project',
        'hr_timesheet',
    ],
    'data': [
        'security/agh_performance_groups.xml',
        'security/ir.model.access.csv',
        'data/agh_performance_data.xml',
        'views/agh_kpi_evaluation_views.xml',
        'views/agh_kpi_criteria_views.xml',
        'views/agh_performance_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
        'wizard/agh_ollama_summary_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'agh_performance_tracker/static/src/css/performance_tracker.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
