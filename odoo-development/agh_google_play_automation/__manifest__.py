# -*- coding: utf-8 -*-
{
    'name': 'AGH Google Play Automation Pipeline',
    'version': '18.0.1.0.0',
    'category': 'Mobile / DevOps',
    'summary': 'Connecteur Odoo pour Google Play Console API et suivi des releases APK',
    'author': 'AGH Holding',
    'website': 'https://github.com/AGH-Data-Agency-Holding/odoo-development',
    'depends': ['base', 'mail', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/google_play_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
