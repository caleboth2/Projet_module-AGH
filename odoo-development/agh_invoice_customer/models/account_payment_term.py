# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    agh_is_maroc_compliant = fields.Boolean(
        string="Conforme legislation marocaine",
        default=True,
        help="Indique si ce terme de paiement respecte la loi marocaine.",
    )
    agh_max_days = fields.Integer(
        string="Delai maximum (jours)",
        default=0,
        help="Delai maximum autorise par la loi marocaine.",
    )
    agh_penalty_rate = fields.Float(
        string="Taux penalite (%)",
        default=0.0,
        help="Taux d'interet de retard applicable.",
    )
