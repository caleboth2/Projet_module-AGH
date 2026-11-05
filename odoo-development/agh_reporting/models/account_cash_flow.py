from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class AccountCashFlowReport(models.TransientModel):
    _name = 'account.cash.flow.report'
    _description = 'Tableau de flux de trésorerie'

    date_from = fields.Date(string='Date début', required=True)
    date_to = fields.Date(string='Date fin', required=True)
    method = fields.Selection([
        ('direct', 'Méthode directe'),
        ('indirect', 'Méthode indirecte'),
    ], string='Méthode', default='indirect')
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company
    )
    cash_flow_data = fields.Text(string='Données flux')

    def action_generate(self):
        self.ensure_one()
        if self.method == 'direct':
            data = self._generate_direct_method()
        else:
            data = self._generate_indirect_method()
        self.cash_flow_data = str(data)
        return self.env.ref('agh_reporting.report_flux_tresorerie').report_action(self)

    def _get_payments_amount(self, payment_type):
        payments = self.env['account.payment'].search([
            ('payment_type', '=', payment_type),
            ('state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ])
        return sum(payments.mapped('amount'))

    def _get_move_lines_debit(self, prefixes):
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

    def _get_move_lines_credit(self, prefixes):
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

    def _generate_direct_method(self):
        encaissements = self._get_payments_amount('inbound')
        decaissements_fournisseurs = self._get_payments_amount('outbound')
        decaissements_personnel = 0.0
        autres_decaissements = 0.0
        flux_exploitation = encaissements - (decaissements_fournisseurs + decaissements_personnel + autres_decaissements)
        return {
            'method': 'direct',
            'encaissements_clients': encaissements,
            'decaissements_fournisseurs': decaissements_fournisseurs,
            'decaissements_personnel': decaissements_personnel,
            'autres_decaissements': autres_decaissements,
            'flux_exploitation': flux_exploitation,
            'flux_investissement': self._get_investment_cash_flow(),
            'flux_financement': self._get_financing_cash_flow(),
        }

    def _generate_indirect_method(self):
        produits = self._get_move_lines_credit(['71', '72', '74', '75', '76', '78'])
        charges = self._get_move_lines_debit(['61', '62', '63', '64', '65', '68', '69'])
        resultat_net = produits - charges
        dotations = self._get_move_lines_debit(['68'])
        provisions = self._get_move_lines_debit(['69'])
        bfr_variation = 0.0
        flux_exploitation = resultat_net + dotations + provisions - bfr_variation
        return {
            'method': 'indirect',
            'resultat_net': resultat_net,
            'dotations': dotations,
            'provisions': provisions,
            'bfr_variation': bfr_variation,
            'flux_exploitation': flux_exploitation,
            'flux_investissement': self._get_investment_cash_flow(),
            'flux_financement': self._get_financing_cash_flow(),
        }

    def _get_investment_cash_flow(self):
        acquisitions = self._get_move_lines_debit(['21', '22', '23', '24'])
        cessions = self._get_move_lines_credit(['751'])
        return -acquisitions + cessions

    def _get_financing_cash_flow(self):
        capital = self._get_move_lines_credit(['111'])
        emprunts = self._get_move_lines_credit(['16'])
        dividendes = self._get_move_lines_debit(['116'])
        return capital + emprunts - dividendes
