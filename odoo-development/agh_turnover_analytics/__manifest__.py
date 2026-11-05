{
    "name": "AGH Turnover Analytics",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "summary": "Automatic turnover calculation by department",

    "author": "AGH",
    "license": "AGPL-3",

    "depends": [
        "hr",
        "hr_contract",
    ],

    "data": [
        "views/hr_department_views.xml",
        "views/turnover_graph_views.xml",
    ],

    "installable": True,
    "application": False,
}