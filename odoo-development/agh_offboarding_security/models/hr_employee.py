from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def action_start_offboarding(self):
        self.ensure_one()

        offboarding = self.env["agh.offboarding"].create({
            "name": f"OFF-{self.name}",
            "employee_id": self.id,
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": "agh.offboarding",
            "view_mode": "form",
            "res_id": offboarding.id,
            "target": "current",
        }