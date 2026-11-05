{
    "name": "HR Contract Custom Attestation",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "summary": "Custom Attestation Management",
    "author": "AGH",
    "license": "AGPL-3",
    "depends": [
        "hr",
        "hr_contract",
        "mail",
    ],
    "data": [
        
        "views/hr_contract_views.xml",
        "report/custom_attestation_report.xml",
        "report/custom_attestation_template.xml",
    ],
    "installable": True,
    "application": False,
}