{
    'name': 'Normalisation & Séquençage des Contrats par Département',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Contracts',
    'summary': 'Génération automatique de références uniques de contrats par département',
    'description': """
        Module Odoo 18 pour la gestion RH :
        - Génération automatique d'une référence de contrat normalisée (ex: REF-RECRUT-2026-004)
        - Incrémentation basée sur le département de l'employé lors de la validation du contrat
    """,
    'depends': ['hr', 'hr_contract'],
    'data': [
        'views/hr_department_views.xml',
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}