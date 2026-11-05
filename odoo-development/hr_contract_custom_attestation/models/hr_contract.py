from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    reference_period_months = fields.Integer(
        string="Reference Period (Months)",
        default=3,
    )

    reference_period_end_date = fields.Date(
        string="Reference Period End Date",
        compute="_compute_reference_period",
        store=True,
    )

    is_reference_period_active = fields.Boolean(
        string="Reference Period Active",
        compute="_compute_reference_period",
        store=True,
    )

    @api.depends(
        "date_start",
        "reference_period_months",
    )
    def _compute_reference_period(self):

        today = fields.Date.today()

        for contract in self:

            contract.reference_period_end_date = False
            contract.is_reference_period_active = False

            if contract.date_start:

                end_date = (
                    contract.date_start
                    + relativedelta(
                        months=contract.reference_period_months
                    )
                )

                contract.reference_period_end_date = end_date

                contract.is_reference_period_active = (
                    today <= end_date
                )

    def action_print_custom_attestation(self):
        self.ensure_one()
    
        return self.env.ref(
            "hr_contract_custom_attestation.action_report_custom_attestation"
        ).report_action(self)
    