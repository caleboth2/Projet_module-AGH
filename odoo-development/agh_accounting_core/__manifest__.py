# -*- coding: utf-8 -*-
{
    'name': 'AGH Accounting Core — Plan Comptable Marocain',
    'version': '18.0.1.2.0',
    'category': 'Accounting/Core',
    'summary': 'Base comptable conforme au Plan Comptable Marocain (PCM)',
    'description': """
        Module socle de la comptabilité marocaine.
        - Plan Comptable Marocain (PCM) classes 1 à 9
        - Compatibilité OHADA / PCG
        - Gestion des exercices comptables et clôtures
        - Wizard de clôture annuelle (affectation du résultat)
        - Verrouillage de la période comptable
        - Journaux multiples préconfigurés
        - Comptabilité analytique multi-axes
        - Piste d'audit complète
        - Lettrage automatique et manuel
        - Écritures de régularisation
    """,
    'author': 'AGH Consulting',
    'website': 'https://www.agh-consulting.ma',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'base',
        'mail',
        'analytic',
        'account_fiscal_year',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_groups_pcm.xml',
        'data/account_chart_pcm.xml',
        'data/account_journal_pcm.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
        'wizard/wizard_cloture_annuelle.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'pre_init_hook': 'pre_init_hook',
}
