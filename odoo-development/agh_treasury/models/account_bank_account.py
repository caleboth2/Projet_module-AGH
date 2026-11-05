# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountBankAccount(models.Model):
    _name = 'account.bank.account'
    _description = 'Compte bancaire detaille (Tresorerie AGH)'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Nom du compte', required=True)
    bank_name = fields.Char(string='Banque', required=True)
    iban = fields.Char(string='IBAN', size=34)
    bic = fields.Char(string='BIC / SWIFT', size=11)
    rib = fields.Char(string='RIB (Maroc)', size=24)
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal comptable',
        domain=[('type', 'in', ['bank', 'cash'])],
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
        required=True,
    )
    current_balance = fields.Monetary(
        string='Solde courant',
        currency_field='currency_id',
        compute='_compute_balance',
    )
    last_statement_date = fields.Date(
        string='Date dernier releve',
        compute='_compute_last_statement_date',
    )
    minimum_balance = fields.Monetary(
        string='Solde minimum',
        currency_field='currency_id',
        help='Seuil minimum a maintenir',
    )
    has_alert = fields.Boolean(
        string='Alerte active',
        compute='_compute_has_alert',
    )
    active = fields.Boolean(string='Actif', default=True)

    @api.depends('journal_id')
    def _compute_balance(self):
        for account in self:
            account.current_balance = account.journal_id.current_statement_balance                   if account.journal_id and hasattr(account.journal_id, 'current_statement_balance')                   else 0.0

    @api.depends('journal_id')
    def _compute_last_statement_date(self):
        for account in self:
            if account.journal_id:
                statement = self.env['account.bank.statement'].search(
                    [('journal_id', '=', account.journal_id.id)],
                    order='date desc',
                    limit=1,
                )
                account.last_statement_date = statement.date if statement else False
            else:
                account.last_statement_date = False

    @api.depends('current_balance', 'minimum_balance')
    def _compute_has_alert(self):
        for account in self:
            account.has_alert = (
                bool(account.minimum_balance)
                and (account.current_balance or 0.0) < account.minimum_balance
            )

    def action_view_statements(self):
        self.ensure_one()
        return {
            'name': _('Releves bancaires'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'view_mode': 'list,form',
            'domain': [('journal_id', '=', self.journal_id.id)] if self.journal_id else [],
        }
