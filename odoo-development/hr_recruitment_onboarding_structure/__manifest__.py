{
    'name': 'AGH Recruitment & Onboarding Structure',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Manage Job Templates and Recruitment Stage Structures',
    'description': """
        This module allows to:
        - Maintain a bank of job advertisement templates (Banque d'annonces).
        - Define interview and onboarding structures per recruitment stage.
    """,
    'author': 'AGH Data Agency Holding',
    'website': 'https://www.aghagency.com',
    'depends': ['hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'data/agh_job_template_data.xml',
        'views/agh_job_template_views.xml',
        'views/hr_job_views.xml',
        'views/hr_recruitment_stage_views.xml',
        'views/hr_applicant_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
