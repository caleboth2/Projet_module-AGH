{
    'name': 'AGH Employee Certificate Generator',
    'version': '18.0.2.1.0',
    'category': 'Human Resources/Certificates',
    'summary': 'Génération des attestations employés et stagiaires (intégré au menu Employees)',
    'description': """
AGH Employee Certificate Generator
==================================

Génère toutes les attestations RH (Travail, Salaire, Stage, Congé,
Prise en Charge, Fin de Contrat) avec workflow complet et envoi email.

Intègre également la gestion des stagiaires (intern.profile) ainsi
que l'envoi automatique d'attestations à la fin des contrats.

Les menus sont intégrés directement dans le menu standard "Employees" :
- Employees > Attestations > Attestations Employés
- Employees > Attestations > Attestations Stagiaires
""",
    'author': 'AGH Data Agency Holding',
    'depends': ['base', 'hr', 'hr_contract', 'mail', 'knowledge_plus_final_v3'],
    'data': [
        'security/ir.model.access.csv',
        'data/certificate_template_data.xml',
        'data/intern_attestation_data.xml',
        'report/report_attestation_travail.xml',
        'report/report_attestation_salaire.xml',
        'report/report_attestation_stage.xml',
        'report/report_attestation_conge.xml',
        'report/report_attestation_fin.xml',
        'report/report_prise_en_charge.xml',
        'report/report_intern_attestation.xml',
        'report/report_employee_attestation_premium.xml',
        'wizard/wizard_generate_certificate.xml',
        'views/hr_certificate_views.xml',
        'views/intern_profile_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
