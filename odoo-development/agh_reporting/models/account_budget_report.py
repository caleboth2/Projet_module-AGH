from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class AccountBudgetReport(models.TransientModel):
    _name = 'account.budget.report'
    _description = 'Suivi budgétaire'

    name = fields.Char(string='Nom budget')
    date_from = fields.Date(string='Date début', required=True)
    date_to = fields.Date(string='Date fin', required=True)
    budget_type = fields.Selection([
        ('revenue', 'Budget des revenus'),
        ('expense', 'Budget des dépenses'),
        ('both', 'Les deux'),
    ], string='Type', default='both')
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company
    )
    budget_line_ids = fields.One2many(
        'account.budget.line', 'budget_id', string='Lignes budgétaires'
    )
    variance_data = fields.Text(string='Données écarts')

    def action_generate(self):
        self.ensure_one()
        variances = []
        for line in self.budget_line_ids:
            actual = self._get_actual_amount(line.account_id)
            variance = {
                'account_id': line.account_id.id,
                'account_name': line.account_id.name,
                'budgeted': line.amount,
                'actual': actual,
                'variance': actual - line.amount,
                'variance_percent': ((actual - line.amount) / line.amount * 100) if line.amount else 0.0,
            }
            variances.append(variance)
        self.variance_data = str(variances)
        return {'type': 'ir.actions.act_window_close'}

    def _get_actual_amount(self, account):
        domain = [
            ('account_id', '=', account.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
        ]
        lines = self.env['account.move.line'].search(domain)
        if account.account_type in ('expense', 'expense_depreciation', 'expense_direct_cost'):
            return sum(lines.mapped('debit'))
        else:
            return sum(lines.mapped('credit'))


class AccountBudgetLine(models.TransientModel):
    _name = 'account.budget.line'
    _description = 'Ligne budgétaire'

    budget_id = fields.Many2one('account.budget.report', string='Budget')
    account_id = fields.Many2one('account.account', string='Compte', required=True)
    amount = fields.Monetary(string='Montant budgété', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='budget_id.company_id.currency_id',
        readonly=True,
    )
