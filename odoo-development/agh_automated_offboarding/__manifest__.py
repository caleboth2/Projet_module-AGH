# -*- coding: utf-8 -*-
{
    'name': 'AGH Automated Onboarding & Offboarding Access Governance',
    'version': '18.0.1.0.0',
    'category': 'Human Resources / Security',
    'summary': 'Gestion automatique de la création et révocation des accès Odoo, GitHub Org et Vault à la création/suppression des employés',
    'author': 'AGH Holding',
    'website': 'https://github.com/AGH-Data-Agency-Holding/odoo-development',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/offboarding_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
