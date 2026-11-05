# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    tva_type = fields.Selection(
        selection=[
            ('normal', 'TVA Normale'),
            ('deductible', 'TVA Déductible'),
            ('collecte', 'TVA Collectée'),
        ],
        string="Type TVA",
        default='normal',
    )

    moroccan_tva_rate = fields.Selection(
        selection=[
            ('20', '20% - Taux normal'),
            ('14', '14% - Transport, électricité, eau'),
            ('10', '10% - Hôtellerie, restauration, locations'),
            ('7', '7% - Produits de première nécessité, médicaments'),
            ('0', '0% - Exonéré'),
        ],
        string="Taux TVA Marocain",
    )

    is_tva_deductible = fields.Boolean(string="TVA Déductible", default=False)
    is_tva_collecte = fields.Boolean(string="TVA Collectée", default=False)


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    is_exoneration = fields.Boolean(string="Exonération TVA", default=False)
    exoneration_reason = fields.Char(string="Motif d'exonération")
    tax_clearance_id = fields.Char(string="N° Agrément fiscal")
