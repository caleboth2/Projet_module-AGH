# -*- coding: utf-8 -*-
"""
Wizard de clôture d'une année fiscale (PCM Maroc).

Reproduit la séquence vidéo « Clôture d'une Année Fiscale dans Odoo » :
  1. Vérification des dates de l'exercice
  2. Calcul du résultat de l'exercice (produits cl.7 - charges cl.6)
  3. Génération automatique de l'écriture d'affectation du résultat (OD)
       Bénéfice : Débit 1191 / Crédit 1161
       Perte    : Débit 1169 / Crédit 1199
  4. Publication de l'écriture
  5. Verrouillage de la date comptable pour tous les utilisateurs
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class WizardClotureAnnuelle(models.TransientModel):
    _name = 'wizard.cloture.annuelle'
    _description = "Wizard de clôture annuelle PCM"

    fiscal_year_id = fields.Many2one(
        'account.fiscal.year', string="Exercice à clôturer", required=True
    )
    date_from = fields.Date(related='fiscal_year_id.date_from', readonly=True)
    date_to = fields.Date(related='fiscal_year_id.date_to', readonly=True)
    company_id = fields.Many2one(
        'res.company', string="Société",
        default=lambda s: s.env.company, required=True
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )

    journal_id = fields.Many2one(
        'account.journal', string="Journal d'OD",
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda s: s.env['account.journal'].search(
            [('type', '=', 'general'),
             ('company_id', '=', s.env.company.id)], limit=1
        ),
        required=True,
    )

    total_produits = fields.Monetary(
        compute='_compute_resultat', string="Total produits", currency_field='currency_id')
    total_charges = fields.Monetary(
        compute='_compute_resultat', string="Total charges", currency_field='currency_id')
    resultat = fields.Monetary(
        compute='_compute_resultat', string="Résultat de l'exercice", currency_field='currency_id')
    is_benefit = fields.Boolean(compute='_compute_resultat', string="Bénéfice")

    lock_date = fields.Date(
        string="Date de verrouillage (tous utilisateurs)",
        help="Toutes les écritures à cette date et avant seront verrouillées.",
    )

    move_id = fields.Many2one('account.move', string="Écriture générée", readonly=True)
    state = fields.Selection([
        ('draft', 'Vérification'),
        ('done', 'Clôturée'),
    ], default='draft')

    # ── Calcul du résultat ────────────────────────────────────────────────
    @api.depends('fiscal_year_id', 'company_id')
    def _compute_resultat(self):
        for w in self:
            if not w.fiscal_year_id:
                w.total_produits = w.total_charges = w.resultat = 0.0
                w.is_benefit = False
                continue
            domain = [
                ('date', '>=', w.date_from),
                ('date', '<=', w.date_to),
                ('company_id', '=', w.company_id.id),
                ('parent_state', '=', 'posted'),
            ]
            prod = self.env['account.move.line'].search(
                domain + [('account_id.code', '=like', '7%')]
            )
            charge = self.env['account.move.line'].search(
                domain + [('account_id.code', '=like', '6%')]
            )
            w.total_produits = sum(prod.mapped('credit')) - sum(prod.mapped('debit'))
            w.total_charges = sum(charge.mapped('debit')) - sum(charge.mapped('credit'))
            w.resultat = w.total_produits - w.total_charges
            w.is_benefit = w.resultat >= 0

    # ── Étape 1 : préparer / vérifier ─────────────────────────────────────
    def action_check(self):
        self.ensure_one()
        if not self.fiscal_year_id:
            raise UserError(_("Veuillez sélectionner un exercice fiscal."))
        # Vérifier l'absence d'écritures en brouillon sur la période
        drafts = self.env['account.move'].search_count([
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'draft'),
        ])
        if drafts:
            raise UserError(_(
                "Il reste %s écritures en brouillon sur l'exercice. "
                "Veuillez les valider ou les annuler avant la clôture."
            ) % drafts)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ── Étape 2 : générer l'écriture d'affectation + verrouiller ─────────
    def action_close(self):
        self.ensure_one()
        if self.move_id:
            raise UserError(_("Cet exercice a déjà été clôturé."))
        self._compute_resultat()

        AccountAccount = self.env['account.account']

        def _get(code):
            return AccountAccount.search(
                [('code', '=like', f'{code}%'),
                 ('company_id', '=', self.company_id.id)], limit=1)

        montant = abs(self.resultat)
        if not montant:
            raise UserError(_("Le résultat de l'exercice est nul, aucune affectation nécessaire."))

        if self.is_benefit:
            cpt_resultat = _get('1191')   # Résultat net bénéficiaire
            cpt_affect = _get('1161')     # Report à nouveau bénéficiaire
            if not (cpt_resultat and cpt_affect):
                raise UserError(_(
                    "Comptes 1191 / 1161 introuvables. Vérifiez votre plan PCM."
                ))
            lines = [
                (0, 0, {'name': _("Affectation résultat — Bénéfice"),
                        'account_id': cpt_resultat.id,
                        'debit': montant, 'credit': 0.0}),
                (0, 0, {'name': _("Affectation résultat — Bénéfice"),
                        'account_id': cpt_affect.id,
                        'debit': 0.0, 'credit': montant}),
            ]
        else:
            cpt_resultat = _get('1199')   # Résultat net déficitaire
            cpt_affect = _get('1169')     # Report à nouveau déficitaire
            if not (cpt_resultat and cpt_affect):
                raise UserError(_(
                    "Comptes 1199 / 1169 introuvables. Vérifiez votre plan PCM."
                ))
            lines = [
                (0, 0, {'name': _("Affectation résultat — Perte"),
                        'account_id': cpt_affect.id,
                        'debit': montant, 'credit': 0.0}),
                (0, 0, {'name': _("Affectation résultat — Perte"),
                        'account_id': cpt_resultat.id,
                        'debit': 0.0, 'credit': montant}),
            ]

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'ref': _("Affectation du résultat — Exercice %s") % self.fiscal_year_id.name,
            'pcm_move_type': 'cloture',
            'company_id': self.company_id.id,
            'line_ids': lines,
        })
        move.action_post()
        self.move_id = move

        # Verrouillage de la période
        if self.lock_date or self.date_to:
            self.company_id.sudo().write({
                'agh_fiscalyear_lock_date': self.lock_date or self.date_to,
            })

        self.state = 'done'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',
        }
