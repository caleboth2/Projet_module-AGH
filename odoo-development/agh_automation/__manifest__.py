{
    'name': 'AGH Automation',
    'version': '18.0.2.3.0',
    'category': 'Technical / Automation',
    'summary': 'Automation des processus récurrents : relances, échéanciers, clôtures, exports, alertes financières',
    'description': """
Module d'automatisation pour la gestion des relances clients, alertes fournisseurs,
clôture mensuelle, export TVA DGI, sauvegarde DB, KPIs et règles d'alerte configurables.
    """,
    'author': 'AGH',
    'depends': [
        'base_automation',
        'mail',
        'account',
        'agh_invoice_customer',
        'agh_fiscal_maroc'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/alert_rules_data.xml',
        'views/agh_alert_rule_views.xml',
        'views/automation_dashboard_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'auto_install': False,
}
