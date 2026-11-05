{
    'name': 'AGH Gumroad Analytics',
    'version': '18.0.2.0.0',
    'category': 'Marketing',
    'summary': "Analyse souveraine des ventes Gumroad (IA locale Ollama + archivage)",
    'description': """
AGH Gumroad Analytics (V2)
==========================
- Tous les modèles préfixés `agh.gumroad.*`
- Souveraineté IA : appel d'Ollama local (http://host.docker.internal:11434), zéro fuite cloud
- Archivage : chaque vente liée à un `res.partner` + JSON Gumroad brut conservé pour audit
- Knowledge : publication auto dans la catégorie "Analyses Commerciales / Gumroad"
- Bug prix corrigé : Gumroad renvoie le `price` des ventes en cents TOTAL (taxes incluses).
    """,
    'author': 'AGH Consulting',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'project',
        'hr_timesheet',
        'agh_gumroad_connector',
    ],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/ir_config_parameter.xml',
        'views/gumroad_product_views.xml',
        'views/gumroad_sale_views.xml',
        'views/gumroad_metric_views.xml',
        'views/gumroad_report_views.xml',
        'views/project_project_views.xml',
        'wizard/gumroad_sync_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
