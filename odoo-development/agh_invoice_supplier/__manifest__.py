# -*- coding: utf-8 -*-
{
    'name': 'AGH - Gestion Fournisseurs Maroc',
    'version': '18.0.1.1.0',
    'category': 'Accounting/Supplier Invoice',
    'summary': "Gestion complète des fournisseurs : achats, factures, paiements, RAS, rapprochement 3 voies",
    'description': """
Gestion complète des fournisseurs pour une société marocaine
============================================================

- Fiche fournisseur enrichie : ICE, IF, RC, CNSS, Patente, RAS, fournisseur stratégique
- Demandes de prix (RFQ) → Bons de commande → Réceptions
- Factures fournisseurs avec validation multi-niveaux (Comptable → Achats → DAF)
- Avoirs fournisseurs et paiements fournisseurs
- Rapprochement 3 voies (BC / BR / Facture) avec écart paramétrable
- Retenue à la source (RAS) :
    * Calcul automatique sur lignes de facture
    * Déclaration mensuelle
    * Génération des certificats PDF
- Conformité fiscale marocaine
    """,
    'author': 'AGH Data Agency',
    'website': 'https://agh-data-agency-holding.netlify.app',
    'depends': [
        'base',
        'account',
        'purchase',
        'stock',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/ras_tax_data.xml',
        'views/account_ras_views.xml',
        'views/account_move_supplier_views.xml',
        'views/res_partner_supplier_views.xml',
        'wizard/wizard_3way_match.xml',
        'wizard/wizard_ras_declaration.xml',
        'report/ras_certificate_report.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
