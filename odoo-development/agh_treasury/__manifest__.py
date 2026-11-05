# -*- coding: utf-8 -*-
{
    'name': 'AGH Treasury - Gestion de Tresorerie',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Treasury',
    'summary': 'Gestion complete de tresorerie multi-devises, rapprochement bancaire et previsions',
    'description': """
Module de gestion de tresorerie complet:
- Gestion multi-devises (MAD, EUR, USD)
- Import releves bancaires (OFX, CSV, CAMT.053)
- Rapprochement bancaire automatique
- Effets de commerce (Lettre de change, Billet a ordre)
- Previsions de tresorerie 30 / 60 / 90 jours
- Alertes seuil minimum
    """,
    'author': 'Agh Data Agency',
    'website': 'https://agh-data-agency-holding.netlify.app',
    'depends': [
        'base',
        'account',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/treasury_forecast_data.xml',
        'views/account_bank_account_views.xml',
        'views/account_recurring_payment_views.xml',
        'views/treasury_dashboard_views.xml',
        'views/account_effet_views.xml',
        'wizard/wizard_bank_reconcile.xml',
        'wizard/wizard_import_statement.xml',
        'wizard/wizard_cash_count.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['ofxparse'],
    },
    'assets': {
        'web.assets_backend': [
            'agh_treasury/static/src/scss/treasury.scss',
        ],
    },
}
