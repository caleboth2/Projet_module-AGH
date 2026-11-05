from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class AccountBalanceAged(models.TransientModel):
    _name = 'account.balance.aged'
    _description = 'Balance âgée clients/fournisseurs'

    partner_type = fields.Selection([
        ('customer', 'Clients'),
        ('supplier', 'Fournisseurs'),
    ], string='Type', required=True, default='customer')
    date_at = fields.Date(string='Date arrêté', required=True, default=fields.Date.today)
    period_length = fields.Integer(string='Période (jours)', default=30)
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company
    )
    aged_balance_lines = fields.Text(string='Lignes balance âgée')

    def action_generate(self):
        self.ensure_one()
        if self.partner_type == 'customer':
            partner_domain = [('customer_rank', '>', 0)]
            account_type = 'asset_receivable'
        else:
            partner_domain = [('supplier_rank', '>', 0)]
            account_type = 'liability_payable'

        partners = self.env['res.partner'].search(partner_domain)
        lines = []

        for partner in partners:
            move_lines = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('account_id.account_type', '=', account_type),
                ('reconciled', '=', False),
                ('date', '<=', self.date_at),
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
            ])
            if move_lines:
                total = sum(move_lines.mapped('balance'))
                aging = self._compute_aging(move_lines)
                lines.append({
                    'partner_id': partner.id,
                    'partner_name': partner.name or '',
                    'total': total,
                    'current': aging['current'],
                    'days_30': aging['days_30'],
                    'days_60': aging['days_60'],
                    'days_90': aging['days_90'],
                    'days_90_plus': aging['days_90_plus'],
                })

        self.aged_balance_lines = str(lines)
        return self.env.ref('agh_reporting.report_balance_agee').report_action(self)

    def _compute_aging(self, move_lines):
        aging = {
            'current': 0.0,
            'days_30': 0.0,
            'days_60': 0.0,
            'days_90': 0.0,
            'days_90_plus': 0.0,
        }
        today = self.date_at
        for line in move_lines:
            ref_date = line.date_maturity or line.date
            if ref_date:
                days_due = (today - ref_date).days
            else:
                days_due = 0

            amount = abs(line.balance)
            if days_due <= 0:
                aging['current'] += amount
            elif days_due <= self.period_length:
                aging['days_30'] += amount
            elif days_due <= self.period_length * 2:
                aging['days_60'] += amount
            elif days_due <= self.period_length * 3:
                aging['days_90'] += amount
            else:
                aging['days_90_plus'] += amount
        return aging


class AccountGeneralLedger(models.TransientModel):
    _name = 'account.general.ledger'
    _description = 'Grand-livre général'

    date_from = fields.Date(string='Date début', required=True)
    date_to = fields.Date(string='Date fin', required=True)
    account_ids = fields.Many2many('account.account', string='Comptes')
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company
    )

    def action_generate(self):
        self.ensure_one()
        accounts = self.account_ids
        if not accounts:
            accounts = self.env['account.account'].search([
                ('company_ids', 'in', self.company_id.id),
            ])
        ledger_data = []
        for account in accounts:
            move_lines = self.env['account.move.line'].search([
                ('account_id', '=', account.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
            ], order='date, move_id')
            if move_lines:
                debit_total = sum(move_lines.mapped('debit'))
                credit_total = sum(move_lines.mapped('credit'))
                balance = debit_total - credit_total
                ledger_data.append({
                    'account_id': account.id,
                    'account_code': account.code,
                    'account_name': account.name,
                    'debit': debit_total,
                    'credit': credit_total,
                    'balance': balance,
                })
        return self.env.ref('agh_reporting.report_grand_livre').report_action(self)
