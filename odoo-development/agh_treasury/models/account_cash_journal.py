# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    agh_reconcile_tolerance = fields.Float(
        string='Tolerance rapprochement (%)',
        default=0.01,
        help='Tolerance d\'ecart pour rapprochement automatique',
    )
    agh_reconcile_rules = fields.Text(
        string='Regles rapprochement',
        help='Une regle (regex) par ligne',
    )
    agh_last_cash_count_date = fields.Date(string='Date dernier comptage')
    agh_last_cash_count_amount = fields.Monetary(
        string='Dernier solde compte',
        currency_field='currency_id',
    )
