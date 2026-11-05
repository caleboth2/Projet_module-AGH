# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WizardCashCount(models.TransientModel):
    _name = 'wizard.cash.count'
    _description = 'Wizard comptage de caisse'

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal de caisse',
        required=True,
        domain=[('type', '=', 'cash')],
    )
    expected_amount = fields.Monetary(string='Solde attendu', currency_field='currency_id')
    counted_amount = fields.Monetary(string='Solde compte', required=True, currency_field='currency_id')
    difference = fields.Monetary(string='Ecart', compute='_compute_difference', currency_field='currency_id')
    observation = fields.Text(string='Observations')
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id')

    @api.depends('expected_amount', 'counted_amount')
    def _compute_difference(self):
        for wizard in self:
            wizard.difference = (wizard.counted_amount or 0.0) - (wizard.expected_amount or 0.0)

    def action_validate(self):
        self.ensure_one()
        self.journal_id.write({
            'agh_last_cash_count_date': fields.Date.today(),
            'agh_last_cash_count_amount': self.counted_amount,
        })
        return {'type': 'ir.actions.act_window_close'}
