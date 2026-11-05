{
    "name": "AGH Offboarding Security",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "summary": "Automated Offboarding & Access Revocation",
    "author": "AGH",
    "license": "AGPL-3",
    "depends": [
        "hr",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
        "views/offboarding_views.xml",
    ],
    "installable": True,
    "application": True,
}