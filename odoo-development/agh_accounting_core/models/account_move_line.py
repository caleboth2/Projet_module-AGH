# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    """
    Extension des lignes d'écriture comptable.
    - Lettrage automatique et manuel (avec gestion des écarts)
    - Analytique multi-axes
    - Champs PCM complémentaires
    """
    _inherit = 'account.move.line'

    # ── Lettrage ─────────────────────────────────────────────────────────────
    pcm_reconcile_ref = fields.Char(
        string='Référence de lettrage PCM',
        size=20, index=True,
        help="Référence utilisée pour le lettrage manuel ou automatique."
    )

    reconcile_amount = fields.Monetary(
        string='Montant lettré',
        compute='_compute_reconcile_amount',
        currency_field='currency_id'
    )

    ecart_reglement = fields.Monetary(
        string='Écart de règlement',
        currency_field='currency_id',
        help="Montant de l'écart constaté lors du lettrage (différence de change, "
             "escompte, arrondi)."
    )

    ecart_account_id = fields.Many2one(
        'account.account',
        string='Compte d\'écart',
        help="Compte imputé pour absorber l'écart de règlement."
    )

    # ── Analytique multi-axes ────────────────────────────────────────────────
    analytic_department_id = fields.Many2one(
        'account.analytic.account',
        string='Département',
        domain=[('plan_id.name', '=', 'Département')]
    )

    analytic_project_id = fields.Many2one(
        'account.analytic.account',
        string='Projet',
        domain=[('plan_id.name', '=', 'Projet')]
    )

    analytic_cost_center_id = fields.Many2one(
        'account.analytic.account',
        string='Centre de coût',
        domain=[('plan_id.name', '=', 'Centre de coût')]
    )

    # ── PCM ──────────────────────────────────────────────────────────────────
    pcm_class = fields.Char(
        string='Classe PCM',
        related='account_id.pcm_class',
        store=True, readonly=True
    )

    is_tax_line = fields.Boolean(
        string='Ligne TVA',
        related='account_id.is_tax_account',
        store=True, readonly=True
    )

    # ── Computed ─────────────────────────────────────────────────────────────
    @api.depends('matched_debit_ids.amount', 'matched_credit_ids.amount')
    def _compute_reconcile_amount(self):
        for line in self:
            debit_matched = sum(line.matched_debit_ids.mapped('amount'))
            credit_matched = sum(line.matched_credit_ids.mapped('amount'))
            line.reconcile_amount = debit_matched + credit_matched

    # ── Contraintes ──────────────────────────────────────────────────────────
    @api.constrains('debit', 'credit')
    def _check_debit_credit(self):
        for line in self:
            if line.debit < 0:
                raise ValidationError(
                    _("Le débit ne peut pas être négatif sur la ligne '%s'."
                      " Utilisez le crédit pour les montants négatifs.") % line.name
                )
            if line.credit < 0:
                raise ValidationError(
                    _("Le crédit ne peut pas être négatif sur la ligne '%s'."
                      " Utilisez le débit pour les montants négatifs.") % line.name
                )
            if line.debit > 0 and line.credit > 0:
                raise ValidationError(
                    _("Une ligne d'écriture ne peut pas avoir à la fois un débit "
                      "et un crédit non nuls (ligne : '%s').") % line.name
                )

    # ── Lettrage avec gestion des écarts ─────────────────────────────────────
    def reconcile(self):
        """Surcharge pour gérer les écarts de règlement PCM."""
        result = super().reconcile()
        # Vérification des écarts après lettrage standard
        for line in self.filtered(lambda l: l.ecart_reglement and not l.reconciled):
            if line.ecart_account_id:
                line._create_ecart_entry()
        return result

    def _create_ecart_entry(self):
        """Crée l'écriture d'écart de règlement."""
        self.ensure_one()
        if not self.ecart_reglement or not self.ecart_account_id:
            return

        move_vals = {
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'ref': _("Écart de règlement — %s") % (self.move_id.name or ''),
            'pcm_move_type': 'normal',
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_id.id,
                    'name': _("Écart de règlement"),
                    'debit': self.ecart_reglement if self.ecart_reglement > 0 else 0,
                    'credit': -self.ecart_reglement if self.ecart_reglement < 0 else 0,
                }),
                (0, 0, {
                    'account_id': self.ecart_account_id.id,
                    'name': _("Contrepartie écart de règlement"),
                    'debit': -self.ecart_reglement if self.ecart_reglement < 0 else 0,
                    'credit': self.ecart_reglement if self.ecart_reglement > 0 else 0,
                }),
            ]
        }
        ecart_move = self.env['account.move'].create(move_vals)
        ecart_move.action_post()

    # ── Propagation analytique depuis la pièce ────────────────────────────────
    @api.onchange('move_id')
    def _onchange_move_analytic(self):
        """Propage l'axe analytique de la pièce sur la ligne."""
        if self.move_id and self.move_id.analytic_account_id:
            self.analytic_distribution = {
                str(self.move_id.analytic_account_id.id): 100
            }
