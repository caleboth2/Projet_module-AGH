{
    'name': 'Web No Geolocation',
    'version': '18.0.1.0.0',
    'category': 'Web',
    'summary': 'Désactive la géolocalisation pour le pointage (compatible Tor)',
    'description': """
        Ce module permet de :
        - Désactiver les contraintes de géolocalisation lors du pointage.
        - Autoriser l'accès aux fonctionnalités de présence sans coordonnées GPS.
        - Idéal pour les environnements de haute sécurité ou l'utilisation via Tor.
    """,
    'author': 'AGH Consulting',
    'depends': ['web', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'web_no_geolocation/static/src/js/no_geolocation.js',
        ],
        'hr_attendance.assets_public_kiosk_app': [
            'web_no_geolocation/static/src/js/no_geolocation.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
