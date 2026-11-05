# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    agh_effet_id = fields.Many2one(
        'account.effet.commerce',
        string='Effet de commerce',
        help='Effet associe a ce paiement',
    )
    agh_original_currency_amount = fields.Monetary(
        string='Montant devise origine',
        help="Montant dans la devise d'origine du paiement",
    )
    agh_exchange_rate = fields.Float(
        string='Taux de change applique',
        help='Taux de change utilise pour la conversion',
    )
    agh_exchange_difference = fields.Monetary(
        string='Ecart de change',
        compute='_compute_exchange_difference',
        store=True,
    )
    agh_payment_method_ext = fields.Selection(
        selection=[
            ('cash', 'Especes'),
            ('check', 'Cheque'),
            ('transfer', 'Virement bancaire'),
            ('effet', 'Effet de commerce'),
            ('dd', 'Prelevement automatique'),
        ],
        string='Moyen de paiement (etendu)',
    )
    agh_check_number = fields.Char(string='N. Cheque')
    agh_check_issuer = fields.Char(string='Emetteur cheque')
    agh_transfer_reference = fields.Char(string='Reference virement')

    @api.depends('amount', 'agh_original_currency_amount')
    def _compute_exchange_difference(self):
        for payment in self:
            if payment.agh_original_currency_amount:
                payment.agh_exchange_difference = (
                    (payment.amount or 0.0) - payment.agh_original_currency_amount
                )
            else:
                payment.agh_exchange_difference = 0.0

    def action_register_effet(self):
        self.ensure_one()
        return {
            'name': _('Enregistrer effet'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.effet.commerce',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_id': self.id,
                'default_tireur_id': self.partner_id.id,
                'default_montant': self.amount,
                'default_currency_id': self.currency_id.id,
            },
        }
