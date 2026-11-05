# -*- coding: utf-8 -*-
import re
from datetime import timedelta

from odoo import _, fields, models


class WizardBankReconcile(models.TransientModel):
    _name = 'wizard.bank.reconcile'
    _description = 'Wizard rapprochement bancaire automatique'

    statement_id = fields.Many2one('account.bank.statement', string='Releve bancaire', required=True)
    match_threshold = fields.Float(string='Seuil de matching (%)', default=85.0)
    include_old_transactions = fields.Boolean(string='Inclure transactions anciennes', default=True)
    days_lookback = fields.Integer(string="Jours d'historique", default=90)
    result_summary = fields.Text(string='Resume', readonly=True)

    def action_reconcile(self):
        self.ensure_one()
        statement = self.statement_id
        matched_count = 0
        unmatched_lines = []
        results = []

        rules = self._get_reconcile_rules(statement.journal_id)

        for line in statement.line_ids:
            if line.is_reconciled:
                matched_count += 1
                continue
            matched = self._find_match(line, rules)
            if matched:
                self._create_reconciliation(line, matched)
                matched_count += 1
                results.append("OK %s - %s: rapproche a %.0f%%" % (
                    line.date, line.payment_ref or '', matched['confidence']
                ))
            else:
                unmatched_lines.append(line)
                results.append("KO %s - %s: non rapproche" % (
                    line.date, line.payment_ref or ''
                ))

        total_lines = len(statement.line_ids)
        success_rate = (matched_count / total_lines * 100) if total_lines > 0 else 0
        summary_lines = [
            "=== RAPPROCHEMENT BANCAIRE ===",
            "Releve: %s" % (statement.name or ''),
            "Taux de matching: %.1f%% (objectif: %s%%)" % (success_rate, self.match_threshold),
            "",
            "Operations rapprochees: %s/%s" % (matched_count, total_lines),
            "Operations non rapprochees: %s" % len(unmatched_lines),
            "",
            "Details:",
        ]
        summary_lines.extend(results)
        self.result_summary = "\n".join(summary_lines)

        if success_rate < self.match_threshold:
            return {
                'warning': {
                    'title': _('Taux de rapprochement insuffisant'),
                    'message': _("Le taux de rapprochement (%.1f%%) est inferieur au seuil configure (%s%%).") % (
                        success_rate, self.match_threshold
                    ),
                }
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.bank.reconcile',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def _get_reconcile_rules(self, journal):
        rules = {
            'patterns': [],
            'amount_tolerance': journal.agh_reconcile_tolerance or 0.01,
        }
        if journal.agh_reconcile_rules:
            for line in journal.agh_reconcile_rules.split('\n'):
                if line.strip():
                    rules['patterns'].append(line.strip())
        return rules

    def _find_match(self, statement_line, rules):
        if not statement_line.date or not statement_line.journal_id:
            return None
        # Look for unreconciled move lines on the journal's accounts
        accounts = []
        if statement_line.journal_id.default_account_id:
            accounts.append(statement_line.journal_id.default_account_id.id)
        if statement_line.journal_id.suspense_account_id:
            accounts.append(statement_line.journal_id.suspense_account_id.id)
        domain = [
            ('reconciled', '=', False),
            ('date', '>=', statement_line.date - timedelta(days=self.days_lookback)),
            ('date', '<=', statement_line.date + timedelta(days=self.days_lookback)),
        ]
        if accounts:
            domain.append(('account_id', 'in', accounts))
        account_moves = self.env['account.move.line'].search(domain, limit=200)

        best_match = None
        best_score = 0
        for move in account_moves:
            score = self._calculate_match_score(statement_line, move, rules)
            if score > best_score and score >= self.match_threshold:
                best_score = score
                best_match = {'move': move, 'confidence': score}
        return best_match

    def _calculate_match_score(self, statement_line, move_line, rules):
        score = 0.0
        amount_diff = abs((statement_line.amount or 0.0) - (move_line.balance or 0.0))
        base_amount = abs(statement_line.amount or 0.0) or 1.0
        if amount_diff <= base_amount * (rules['amount_tolerance'] / 100.0):
            score += 40
        elif amount_diff <= base_amount * 0.05:
            score += 20

        date_diff = abs((statement_line.date - move_line.date).days)
        if date_diff <= 1:
            score += 20
        elif date_diff <= 3:
            score += 15
        elif date_diff <= 7:
            score += 10
        elif date_diff <= 14:
            score += 5

        ref_match = self._match_reference(
            statement_line.payment_ref or '',
            move_line.name or '',
            rules['patterns'],
        )
        score += ref_match * 30

        if statement_line.partner_id and move_line.partner_id:
            if statement_line.partner_id.id == move_line.partner_id.id:
                score += 10
            elif self._similar_names(statement_line.partner_id.name, move_line.partner_id.name):
                score += 5

        return score

    def _match_reference(self, ref1, ref2, patterns):
        if not ref1 or not ref2:
            return 0.0
        ref1u = ref1.upper()
        ref2u = ref2.upper()
        if ref1u == ref2u:
            return 1.0
        if ref1u in ref2u or ref2u in ref1u:
            return 0.8
        for pattern in patterns:
            try:
                if re.search(pattern, ref1u, re.IGNORECASE) and re.search(pattern, ref2u, re.IGNORECASE):
                    return 0.7
            except re.error:
                pass
        return 0.0

    def _similar_names(self, name1, name2):
        if not name1 or not name2:
            return False
        words1 = set(w for w in name1.upper().split() if len(w) > 3)
        words2 = set(w for w in name2.upper().split() if len(w) > 3)
        if words1 and words2:
            common = words1.intersection(words2)
            if len(common) / max(len(words1), len(words2)) > 0.5:
                return True
        return False

    def _create_reconciliation(self, statement_line, match):
        statement_line.write({
            'agh_match_method': 'auto',
            'agh_match_confidence': match['confidence'],
            'agh_match_reference': match['move'].name or '',
        })
