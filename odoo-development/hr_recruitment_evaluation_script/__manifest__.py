{
    'name': 'Grille d’évaluation des candidats',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Évaluation des candidats avec score sur 20',
    'description': """
        Ajoute une grille d’évaluation sur les candidatures :
        - Critères avec cases à cocher
        - Calcul automatique du score sur 20
        - Recommandation Passé ou Rejeté
        - Script d’entretien configurable
    """,
    'author': 'AGH Data Agency',
    'license': 'LGPL-3',

    'depends': [
        'hr_recruitment',
        'mail',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/evaluation_criteria_data.xml',
        'views/evaluation_criteria_views.xml',
        'views/hr_applicant_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}