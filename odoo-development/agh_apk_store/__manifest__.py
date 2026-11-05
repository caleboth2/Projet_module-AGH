{
    'name': 'AGH APK Store',
    'version': '18.0.1.0.0',
    'category': 'eCommerce',
    'summary': 'Gestion de la vente des APK et Bundles',
    'depends': ['website_sale', 'payment', 'portal', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/apk_license_views.xml',
        'views/portal_templates.xml',
        'data/mail_template_license.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'agh_apk_store/static/src/js/apk_portal.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}