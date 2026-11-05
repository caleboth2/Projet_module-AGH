from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AccountKPI(models.Model):
    _name = 'account.kpi'
    _description = 'Indicateurs de performance (KPIs)'
    _rec_name = 'name'

    name = fields.Char(string='Nom KPI', required=True)
    kpi_code = fields.Char(string='Code KPI', required=True)
    formula = fields.Text(string='Formule', help="Référence à une méthode de calcul")
    unit = fields.Selection([
        ('amount', 'Montant (MAD)'),
        ('percentage', 'Pourcentage (%)'),
        ('days', 'Jours'),
        ('ratio', 'Ratio'),
    ], string='Unité', default='amount')
    target_value = fields.Float(string='Valeur cible')
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company
    )


class AccountKPIDashboard(models.TransientModel):
    _name = 'account.kpi.dashboard'
    _description = 'Tableau de bord KPIs'

    date_from = fields.Date(
        string='Date début',
        default=lambda self: fields.Date.today() - relativedelta(months=1)
    )
    date_to = fields.Date(
        string='Date fin',
        default=lambda self: fields.Date.today()
    )
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company
    )

    ca = fields.Float(string="Chiffre d'affaires", compute='_compute_kpis', store=False)
    mb = fields.Float(string='Marge brute', compute='_compute_kpis', store=False)
    taux_mb = fields.Float(string='Taux marge (%)', compute='_compute_kpis', store=False)
    dso = fields.Float(string='DSO (jours)', compute='_compute_kpis', store=False)
    dpo = fields.Float(string='DPO (jours)', compute='_compute_kpis', store=False)
    bfr = fields.Float(string='BFR (MAD)', compute='_compute_kpis', store=False)
    taux_impayes = fields.Float(string="Taux d'impayés (%)", compute='_compute_kpis', store=False)
    tresorerie = fields.Float(string='Trésorerie disponible', compute='_compute_kpis', store=False)
    resultat_net = fields.Float(string='Résultat Net', compute='_compute_kpis', store=False)

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_kpis(self):
        for dashboard in self:
            if not dashboard.date_from or not dashboard.date_to:
                dashboard.ca = 0.0
                dashboard.mb = 0.0
                dashboard.taux_mb = 0.0
                dashboard.dso = 0.0
                dashboard.dpo = 0.0
                dashboard.bfr = 0.0
                dashboard.taux_impayes = 0.0
                dashboard.tresorerie = 0.0
                dashboard.resultat_net = 0.0
                continue
            dashboard.ca = dashboard._get_ca()
            dashboard.mb = dashboard._get_mb()
            dashboard.taux_mb = (dashboard.mb / dashboard.ca * 100) if dashboard.ca else 0.0
            dashboard.dso = dashboard._get_dso()
            dashboard.dpo = dashboard._get_dpo()
            dashboard.bfr = dashboard._get_bfr()
            dashboard.taux_impayes = dashboard._get_taux_impayes()
            dashboard.tresorerie = dashboard._get_tresorerie()
            dashboard.resultat_net = dashboard._get_resultat_net()

    def _get_account_balance_by_type(self, account_type, unreconciled=True):
        domain = [
            ('account_id.account_type', '=', account_type),
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
        ]
        if unreconciled:
            domain.append(('reconciled', '=', False))
        lines = self.env['account.move.line'].search(domain)
        return sum(lines.mapped('balance'))

    def _get_move_lines_credit_by_prefix(self, prefixes):
        total = 0.0
        for prefix in prefixes:
            domain = [
                ('account_id.code', '=like', prefix + '%'),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
            ]
            lines = self.env['account.move.line'].search(domain)
            total += sum(lines.mapped('credit'))
        return total

    def _get_move_lines_debit_by_prefix(self, prefixes):
        total = 0.0
        for prefix in prefixes:
            domain = [
                ('account_id.code', '=like', prefix + '%'),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
            ]
            lines = self.env['account.move.line'].search(domain)
            total += sum(lines.mapped('debit'))
        return total

    def _get_ca(self):
        return self._get_move_lines_credit_by_prefix(['71', '72', '74', '75', '76', '78'])

    def _get_mb(self):
        ca = self._get_ca()
        cout_ventes = self._get_move_lines_debit_by_prefix(['61'])
        return ca - cout_ventes

    def _get_days_range(self):
        if self.date_from and self.date_to:
            return (self.date_to - self.date_from).days or 1
        return 1

    def _get_dso(self):
        ca = self._get_ca()
        if not ca:
            return 0.0
        encours = self._get_account_balance_by_type('asset_receivable', unreconciled=True)
        days = self._get_days_range()
        ca_annualized = ca * (365.0 / days)
        return (encours / ca_annualized * 365) if ca_annualized else 0.0

    def _get_dpo(self):
        achats = self._get_move_lines_debit_by_prefix(['61', '62'])
        if not achats:
            return 0.0
        encours = abs(self._get_account_balance_by_type('liability_payable', unreconciled=True))
        days = self._get_days_range()
        achats_annualized = achats * (365.0 / days)
        return (encours / achats_annualized * 365) if achats_annualized else 0.0

    def _get_bfr(self):
        creances = self._get_account_balance_by_type('asset_receivable', unreconciled=True)
        dettes = abs(self._get_account_balance_by_type('liability_payable', unreconciled=True))
        stocks_domain = [
            ('account_id.code', '=like', '3%'),
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
        ]
        stock_lines = self.env['account.move.line'].search(stocks_domain)
        stocks = sum(stock_lines.mapped('debit')) - sum(stock_lines.mapped('credit'))
        return stocks + creances - dettes

    def _get_taux_impayes(self):
        ca = self._get_ca()
        if not ca:
            return 0.0
        unpaid_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('state', '=', 'posted'),
            ('invoice_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ])
        total_unpaid = sum(unpaid_invoices.mapped('amount_residual'))
        return (total_unpaid / ca * 100) if ca else 0.0

    def _get_tresorerie(self):
        domain = [
            ('account_id.account_type', 'in', ['asset_cash', 'asset_bank_and_cash']),
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
        ]
        lines = self.env['account.move.line'].search(domain)
        return sum(lines.mapped('debit')) - sum(lines.mapped('credit'))

    def _get_resultat_net(self):
        produits = self._get_move_lines_credit_by_prefix(['71', '72', '74', '75', '76', '78'])
        charges = self._get_move_lines_debit_by_prefix(['61', '62', '63', '64', '65', '68', '69'])
        return produits - charges

    def action_refresh(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.kpi.dashboard',
            'view_mode': 'form',
            'target': 'main',
            'res_id': self.id,
        }

    def action_export_excel(self):
        pass

    def action_export_pdf(self):
        pass
