# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPayment(models.Model):
    """Ajout du champ inverse pour la relation One2many sur account.move."""
    _inherit = 'account.payment'

    agh_invoice_id = fields.Many2one(
        comodel_name='account.move',
        string="Facture liee",
        ondelete='set null',
        help="Facture client a laquelle cet acompte / paiement est rattache.",
    )
