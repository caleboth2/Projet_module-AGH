{
    'name': 'GitHub Sovereign Integration (V2)',
    'version': '18.0.2.0.0',
    'category': 'Project',
    'summary': 'Mirroring ZIP, Historique complet des Issues et Gouvernance Souveraine (agh)',
    'description': """
        Module de réplication GitHub pour la pérennité de la propriété intellectuelle :
        - Renommage des modèles en agh.github.* pour la souveraineté.
        - Mirroring complet des dépôts en format ZIP stocké en base de données.
        - Importation intégrale de l'historique des issues et de leurs commentaires.
        - Gestion centralisée via des Connecteurs GitHub globaux.
    """,
    'license': 'LGPL-3',
    'depends': ['base', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/github_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
