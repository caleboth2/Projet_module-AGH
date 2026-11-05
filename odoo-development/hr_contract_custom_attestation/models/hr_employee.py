from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    reference_period_months = fields.Integer(
        string="Reference Period (Months)",
        default=3,
        help="Reference period used for attestation generation.",
    )