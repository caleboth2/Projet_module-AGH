# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import fields, models
from odoo.tools import date_utils


class ResCompany(models.Model):
    _inherit = "res.company"

    fiscal_year_date_from = fields.Date(
        string="Start Date of the Fiscal Year",
        compute="_compute_fiscal_year_dates",
        compute_sudo=True,
    )
    fiscal_year_date_to = fields.Date(
        string="End Date of the Fiscal Year",
        compute="_compute_fiscal_year_dates",
        compute_sudo=True,
    )

    def _compute_fiscal_year_dates(self):
        """Compute the start/end of the fiscal year containing today."""
        today = fields.Date.today()
        for company in self:
            res = company.compute_fiscalyear_dates(today)
            company.fiscal_year_date_from = res.get("date_from")
            company.fiscal_year_date_to = res.get("date_to")

    def compute_fiscalyear_dates(self, current_date):
        """Override Odoo's standard fiscal year computation.

        Returns the start/end dates of the fiscal year containing
        ``current_date``. If a record of ``account.fiscal.year`` exists
        for that period it is used; otherwise we fall back to Odoo's
        default computation based on the company's last day/month.

        :param current_date: A datetime.date object.
        :return: A dict containing ``date_from``, ``date_to`` and
            optionally ``record`` (the matching account.fiscal.year).
        """
        self.ensure_one()
        AccountFiscalYear = self.env["account.fiscal.year"]

        fiscalyear = AccountFiscalYear._get_fiscal_year(
            self, current_date, current_date
        )
        if fiscalyear:
            return {
                "date_from": fiscalyear.date_from,
                "date_to": fiscalyear.date_to,
                "record": fiscalyear,
            }

        date_from, date_to = date_utils.get_fiscal_year(
            current_date,
            day=self.fiscalyear_last_day,
            month=int(self.fiscalyear_last_month),
        )

        # Reduce delta if a fiscal year record partially covers the period
        fiscalyear_from = AccountFiscalYear._get_fiscal_year(
            self, date_from, date_from
        )
        if fiscalyear_from:
            date_from = fiscalyear_from.date_to + timedelta(days=1)

        fiscalyear_to = AccountFiscalYear._get_fiscal_year(
            self, date_to, date_to
        )
        if fiscalyear_to:
            date_to = fiscalyear_to.date_from - timedelta(days=1)

        return {
            "date_from": date_from,
            "date_to": date_to,
        }
