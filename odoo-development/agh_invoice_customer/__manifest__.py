{
    'name': 'AGH Invoice Customer - Facturation Marocaine',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Customer Invoice',
    'summary': "Gestion complete du cycle de facturation client conforme aux obligations legales marocaines",
    'description': """
Module de facturation client conforme aux obligations legales marocaines:
- Numerotation legale DGI (FAC-YYYY-NNNN)
- Gestion des acomptes avec lettrage automatique
- Relances automatiques des impayes
- Envoi email avec PDF certifie
- Tableau de bord recouvrement
- Conformite TVA Maroc
    """,
    'author': 'Agh Data Agency',
    'website': 'https://agh-data-agency-holding.netlify.app',
    # NOTE: account_accountant retire car module Enterprise non disponible en Community.
    'depends': [
        'base',
        'mail',
        'account',
        'sale',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/email_template_data.xml',
        'views/account_move_views.xml',
        'views/account_dashboard_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
        'report/report_invoice_maroc.xml',
        'wizard/wizard_send_invoice.xml',
        'wizard/wizard_relance_impaye.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'agh_invoice_customer/static/src/scss/dashboard.scss',
            'agh_invoice_customer/static/src/js/dashboard.js',
        ],
    },
}
