# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Account Fiscal Year",
    "summary": "Create and manage Account Fiscal Years",
    "description": """
Account Fiscal Year
===================
Allows to create and edit fiscal years (exercices comptables) from the
Accounting menu. The start and end dates of the current fiscal year
are then available on the company list and form views.

Compatible with Odoo 18 Community.
    """,
    "version": "18.0.1.0.0",
    "development_status": "Production/Stable",
    "category": "Accounting",
    "website": "https://github.com/OCA/account-financial-tools",
    "author": "Agile Business Group, Camptocamp SA, "
              "Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/account_fiscal_year_rule.xml",
        "views/account_fiscal_year_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
