# -*- coding: utf-8 -*-
{
    'name': 'AGH Centralized Bug & Crash Analytics Aggregator',
    'version': '18.0.1.0.0',
    'category': 'Quality / Maintenance',
    'summary': 'Remontée centralisée des crashs applicatifs sous forme de tickets Odoo',
    'author': 'AGH Holding',
    'website': 'https://github.com/AGH-Data-Agency-Holding/odoo-development',
    'depends': ['base', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/crash_report_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
