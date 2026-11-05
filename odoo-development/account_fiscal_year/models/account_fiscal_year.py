# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class AccountFiscalYear(models.Model):
    _name = "account.fiscal.year"
    _description = "Fiscal Year"
    _order = "date_from desc"

    name = fields.Char(
        string="Name",
        required=True,
    )
    date_from = fields.Date(
        string="Start Date",
        required=True,
        help="Start Date, included in the fiscal year.",
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
        help="Ending Date, included in the fiscal year.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.constrains("date_from", "date_to", "company_id")
    def _check_dates(self):
        """Check that dates are coherent and do not overlap with
        another fiscal year of the same company."""
        for fy in self:
            date_from = fy.date_from
            date_to = fy.date_to
            if date_to < date_from:
                raise ValidationError(
                    _("The ending date must not be prior to the starting date.")
                )

            domain = fy._get_overlapping_domain()
            overlapping_fy = self.search(domain, limit=1)
            if overlapping_fy:
                raise ValidationError(
                    _(
                        "This fiscal year '%(fy)s' overlaps with '%(other)s'.\n"
                        "Please correct the start and/or end dates "
                        "of your fiscal years."
                    ) % {
                        "fy": fy.display_name,
                        "other": overlapping_fy.display_name,
                    }
                )

    def _get_overlapping_domain(self):
        """Return a domain to find fiscal years overlapping with self
        for the same company."""
        self.ensure_one()
        company_domain = [
            ("id", "!=", self.id),
            ("company_id", "=", self.company_id.id),
        ]
        date_from = self.date_from
        date_to = self.date_to

        # Another FY contains our start date
        intersection_domain_from = [
            "&",
            ("date_from", "<=", date_from),
            ("date_to", ">=", date_from),
        ]
        # Another FY contains our end date
        intersection_domain_to = [
            "&",
            ("date_from", "<=", date_to),
            ("date_to", ">=", date_to),
        ]
        # Our FY contains another FY
        intersection_domain_contain = [
            "&",
            ("date_from", ">=", date_from),
            ("date_from", "<=", date_to),
        ]
        intersection_domain = expression.OR(
            [
                intersection_domain_from,
                intersection_domain_to,
                intersection_domain_contain,
            ]
        )
        return expression.AND([company_domain, intersection_domain])

    @api.model
    def _get_fiscal_year(self, company, date_from, date_to):
        """Return a fiscal year record for the given company that contains
        both dates, or an empty recordset if none matches."""
        return self.search(
            [
                ("company_id", "=", company.id),
                ("date_from", "<=", date_from),
                ("date_to", ">=", date_to),
            ],
            limit=1,
        )
