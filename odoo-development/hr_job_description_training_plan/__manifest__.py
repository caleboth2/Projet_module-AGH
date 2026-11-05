{
    'name': 'Fiches de Poste & Plans de Formation',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Gestion avancée des fiches de poste de stage et plans de formation',
    'description': """
        Ce module permet de :
        - Gérer les spécificités des fiches de poste (stages, durée, horaires)
        - Définir des plans de formation par poste avec catégories
        - Paramétrer les valeurs par défaut globales pour la compagnie
    """,
    'depends': ['hr'],
    'data': [
     'views/res_config_settings_views.xml',
     'views/hr_job_views.xml',
    'security/ir.model.access.csv',
     ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}