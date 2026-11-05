from datetime import date

from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    employee_count = fields.Integer(
        string="Employees",
        compute="_compute_turnover",
        store=True,
    )

    departure_count = fields.Integer(
        string="Departures",
        compute="_compute_turnover",
        store=True,
    )

    turnover_rate = fields.Float(
        string="Turnover (%)",
        compute="_compute_turnover",
        store=True,
        group_operator="avg",
    )

    @api.depends(
        "member_ids",
        "member_ids.active",
        "member_ids.departure_date",
    )
    def _compute_turnover(self):

        current_year = date.today().year
        start_date = date(current_year, 1, 1)

        Employee = self.env["hr.employee"]

        for department in self:

            employees = Employee.search([
                ("department_id", "=", department.id),
                ("active", "=", True),
            ])

            departures = Employee.search([
                ("department_id", "=", department.id),
                ("departure_date", "!=", False),
                ("departure_date", ">=", start_date),
            ])

            employee_count = len(employees)
            departure_count = len(departures)

            department.employee_count = employee_count
            department.departure_count = departure_count

            if employee_count:
                department.turnover_rate = (
                    departure_count / employee_count
                ) * 100.0
            else:
                department.turnover_rate = 0.0