{
    'name': 'AGH Reporting - États Financiers Marocains',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'États financiers PCM Maroc, tableaux de bord KPIs et planification envoi automatique',
    'description': """
Module de reporting financier complet:
- Bilan comptable (PCM N/N-1)
- Compte de Produits et Charges (CPC)
- Tableau de flux de trésorerie (directe & indirecte)
- Balance âgée clients/fournisseurs
- Grand-livre détaillé
- KPIs tableau de bord (CA, MB, DSO, DPO, BFR)
- Planification envoi automatique des rapports
    """,
    'author': 'Agh Data Agency',
    'website': 'https://agh-data-agency-holding.netlify.app',
    'depends': ['base', 'account', 'mail', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/report_scheduler_data.xml',
        'data/kpi_config_data.xml',
        'views/reporting_dashboard_views.xml',
        'views/report_scheduler_views.xml',
        'views/menu_views.xml',
        'report/report_bilan_pcm.xml',
        'report/report_cpc_pcm.xml',
        'report/report_flux_tresorerie.xml',
        'report/report_balance_agee.xml',
        'report/report_grand_livre.xml',
        'wizard/wizard_report_scheduler.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'agh_reporting/static/src/js/kpi_dashboard.js',
            'agh_reporting/static/src/scss/reporting.scss',
        ],
    },
}
