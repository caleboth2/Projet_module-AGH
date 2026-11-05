{
    'name': 'AGH Gumroad Connector',
    'version': '18.0.2.0.0',
    'category': 'Marketing',
    'summary': "Connecteur souverain Gumroad <-> Odoo (AGH Consulting)",
    'description': """
AGH Gumroad Connector (V2)
==========================
- Modèle renommé sous le préfixe `agh.gumroad.connector`
- Test de connexion à l'API Gumroad via Access Token
- Base pour la souveraineté des données de vente (extension par agh_gumroad_analytics)
    """,
    'author': 'AGH Consulting',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/gumroad_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
