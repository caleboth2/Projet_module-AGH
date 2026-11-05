# -*- coding: utf-8 -*-
{
    'name': 'AGH Financial & Operational Health Score Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Management / Dashboards',
    'summary': 'Vue macro croisant coûts dev, vélocité technique et statut APK avec agents IA Ollama (QA, PM, SecOps)',
    'author': 'AGH Holding',
    'website': 'https://github.com/AGH-Data-Agency-Holding/odoo-development',
    'depends': ['base', 'project', 'agh_google_play_automation', 'agh_crash_analytics_aggregator', 'agh_automated_offboarding'],
    'data': [
        'security/ir.model.access.csv',
        'views/health_score_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
