# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    agh_reconcile_rate = fields.Float(
        string='Taux rapprochement (%)',
        compute='_compute_reconcile_rate',
        store=True,
        help='Pourcentage de lignes rapprochees',
    )
    agh_total_matched = fields.Integer(
        string='Lignes rapprochees',
        compute='_compute_reconcile_rate',
        store=True,
    )
    agh_total_unmatched = fields.Integer(
        string='Lignes non rapprochees',
        compute='_compute_reconcile_rate',
        store=True,
    )

    @api.depends('line_ids', 'line_ids.is_reconciled')
    def _compute_reconcile_rate(self):
        for stmt in self:
            total = len(stmt.line_ids)
            matched = len(stmt.line_ids.filtered(lambda l: l.is_reconciled))
            stmt.agh_total_matched = matched
            stmt.agh_total_unmatched = total - matched
            stmt.agh_reconcile_rate = (matched / total * 100.0) if total > 0 else 0.0


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    agh_match_method = fields.Selection(
        selection=[
            ('manual', 'Manuel'),
            ('auto', 'Automatique'),
            ('rule', 'Regle'),
        ],
        string='Methode de rapprochement',
        default='manual',
    )
    agh_match_confidence = fields.Float(string='Confiance match (%)')
    agh_match_reference = fields.Char(string='Reference rapprochee')
    agh_is_reconciled = fields.Boolean(
        string='Rapproche (AGH)',
        compute='_compute_is_reconciled',
        store=True,
    )
    agh_is_duplicate = fields.Boolean(
        string='Doublon possible',
        compute='_compute_is_duplicate',
        store=True,
    )

    @api.depends('is_reconciled')
    def _compute_is_reconciled(self):
        for line in self:
            line.agh_is_reconciled = bool(line.is_reconciled)

    @api.depends('amount', 'date', 'partner_id')
    def _compute_is_duplicate(self):
        for line in self:
            if not line.date or not line.amount:
                line.agh_is_duplicate = False
                continue
            domain = [
                ('id', '!=', line.id),
                ('amount', '=', line.amount),
                ('date', '>=', line.date - timedelta(days=3)),
                ('date', '<=', line.date + timedelta(days=3)),
            ]
            if line.partner_id:
                domain.append(('partner_id', '=', line.partner_id.id))
            line.agh_is_duplicate = bool(self.search_count(domain))
