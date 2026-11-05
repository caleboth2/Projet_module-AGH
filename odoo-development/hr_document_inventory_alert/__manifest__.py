{
    'name': 'Inventaire et Alertes Documents Manquants',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Gestion des documents obligatoires des employés',
    'description': """
        Gestion des documents obligatoires par type de contrat,
        inventaire des documents employés et alertes en cas de document manquant.
    """,
    'depends': [
        'hr',
        'hr_contract',
        'mail',
    ],
    'data': [
    'security/ir.model.access.csv',
    'views/hr_document_type_views.xml',
    'views/hr_document_inventory_views.xml',
            ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}