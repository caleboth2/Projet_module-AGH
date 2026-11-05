# -*- coding: utf-8 -*-
{
    'name': 'AGH Fiscalité Marocaine',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Gestion fiscale marocaine : TVA, IS, Cotisation Minimale, Taxe Professionnelle',
    'description': """
Module de fiscalité marocaine couvrant :
- TVA aux taux marocains (20%, 14%, 10%, 7%, 0%)
- Déclaration TVA mensuelle/trimestrielle
- Impôt sur les Sociétés (IS) avec acomptes trimestriels
- Cotisation Minimale (CM)
- Taxe Professionnelle (TP)
- Calendrier fiscal intégré
- Export DGI au format Excel/XML/CSV
    """,
    'author': 'Agh Data Agency',
    'website': 'https://agh-data-agency-holding.netlify.app',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/tax_data.xml',
        'data/fiscal_calendar_data.xml',
        'views/account_tax_views.xml',
        'views/tva_declaration_views.xml',
        'views/is_declaration_views.xml',
        'views/cotisation_minimale_views.xml',
        'views/taxe_professionnelle_views.xml',
        'views/fiscal_calendar_views.xml',
        'wizard/wizard_tva_export_views.xml',
        'wizard/wizard_is_acompte_views.xml',
        'report/report_liasse_fiscale.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
