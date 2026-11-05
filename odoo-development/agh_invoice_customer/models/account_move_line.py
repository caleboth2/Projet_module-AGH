# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    agh_is_acompte_line = fields.Boolean(
        string="Ligne d'acompte",
        default=False,
    )
    agh_original_invoice_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string="Ligne facture d'origine",
        ondelete='set null',
    )
    agh_tva_maroc_type = fields.Selection(
        selection=[
            ('normal', "TVA Normale 20%"),
            ('reduit', "TVA Reduite 14%"),
            ('super_reduit', "TVA Super Reduite 10%"),
            ('exonere', "Exonere"),
            ('hors_champ', "Hors Champ"),
        ],
        string="Type TVA Maroc",
        compute='_compute_tva_maroc_type',
        store=False,
    )

    @api.depends('tax_ids', 'tax_ids.amount')
    def _compute_tva_maroc_type(self):
        for line in self:
            tva_type = 'exonere'
            if line.tax_ids:
                # On considere le taux le plus eleve applique sur la ligne.
                rates = line.tax_ids.mapped('amount')
                tax_rate = max(rates) if rates else 0.0
                if tax_rate == 20:
                    tva_type = 'normal'
                elif tax_rate == 14:
                    tva_type = 'reduit'
                elif tax_rate == 10:
                    tva_type = 'super_reduit'
                elif tax_rate == 0:
                    tva_type = 'exonere'
                else:
                    tva_type = 'hors_champ'
            line.agh_tva_maroc_type = tva_type
