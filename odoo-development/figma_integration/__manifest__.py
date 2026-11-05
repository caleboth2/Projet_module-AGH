{
    'name': 'Figma Integration',

    'version': '1.0',

    'summary': 'Figma integration for Odoo 18',

    'license': 'LGPL-3',

    'depends': [
        'base',
        'project',
        'mail',
    ],

    'data': [

        'security/ir.model.access.csv',

        'views/figma_team_views.xml',
        'views/figma_project_views.xml',
        'views/figma_design_views.xml',
        'views/project_task_views.xml',

        'views/figma_menu.xml',

        'data/cron.xml',
    ],

    'installable': True,

    'application': True,
}