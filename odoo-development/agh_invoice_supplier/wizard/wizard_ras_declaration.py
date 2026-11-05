# -*- coding: utf-8 -*-
import calendar
from datetime import date, datetime

from odoo import _, fields, models
from odoo.exceptions import UserError


class WizardRASDeclaration(models.TransientModel):
    _name = 'wizard.ras.declaration'
    _description = 'Wizard Declaration RAS'

    month = fields.Selection(
        selection=[
            ('01', 'Janvier'), ('02', 'Fevrier'), ('03', 'Mars'),
            ('04', 'Avril'), ('05', 'Mai'), ('06', 'Juin'),
            ('07', 'Juillet'), ('08', 'Aout'), ('09', 'Septembre'),
            ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Decembre'),
        ],
        string='Mois',
        required=True,
        default=lambda self: datetime.now().strftime('%m'),
    )
    year = fields.Integer(
        string='Annee',
        required=True,
        default=lambda self: datetime.now().year,
    )

    def action_generate_declaration(self):
        self.ensure_one()
        month_int = int(self.month)
        year_int = int(self.year)
        last_day = calendar.monthrange(year_int, month_int)[1]
        date_start = date(year_int, month_int, 1)
        date_end = date(year_int, month_int, last_day)

        ras_records = self.env['account.ras.maroc'].search([
            ('declaration_id', '=', False),
            ('date', '>=', date_start),
            ('date', '<=', date_end),
        ])
        if not ras_records:
            raise UserError(_("Aucune retenue a la source trouvee pour cette periode."))

        declaration = self.env['account.ras.declaration'].create({
            'name': "RAS-%s-%s" % (year_int, self.month),
            'month': self.month,
            'year': year_int,
            'ras_ids': [(6, 0, ras_records.ids)],
        })

        return {
            'name': _('Declaration RAS'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.ras.declaration',
            'view_mode': 'form',
            'res_id': declaration.id,
        }
