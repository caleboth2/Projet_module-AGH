{
    'name': 'Sovereign Mobile Signer',
    'version': '1.0',
    'summary': 'Gestion souveraine de la signature d\'applications mobiles via Tor',
    'category': 'Security',
    'author': 'AGH Agency',
    'website': 'https://agh-agency.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/mobile_app_views.xml',
        'views/sign_request_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
