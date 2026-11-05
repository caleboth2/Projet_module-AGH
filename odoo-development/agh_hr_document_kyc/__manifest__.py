{
    'name': 'AGH Documents RH - KYC',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Analyse et validation KYC des documents RH',
    'description': """
        Gestion des documents officiels des employés :
        - Téléversement de pièces justificatives
        - Analyse OCR
        - Extraction des informations importantes
        - Validation ou rejet des documents
        - Suivi du statut KYC
    """,
    'author': 'AGH Data Agency',
    'license': 'LGPL-3',

    'depends': [
        'hr',
        'hr_document_inventory_alert',
        'mail',
    ],

    'data': [
    'security/ir.model.access.csv',
    'views/hr_employee_document_views.xml',
],

    'installable': True,
    'application': True,
    'auto_install': False,
}