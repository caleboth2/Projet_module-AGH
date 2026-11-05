# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Champs conformes a la DGI Maroc
    # ------------------------------------------------------------------
    agh_sequence_maroc = fields.Char(
        string="Numero sequentiel DGI",
        copy=False,
        readonly=True,
        index=True,
        help="Format: FAC-YYYY-NNNN conforme a la DGI",
    )
    agh_client_ref = fields.Char(
        string="Ref. Bon de commande client",
        help="Reference du bon de commande client",
    )
    agh_acompte_ids = fields.One2many(
        comodel_name='account.payment',
        inverse_name='agh_invoice_id',
        string="Acomptes lies",
        readonly=True,
    )
    agh_avoir_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='agh_original_invoice_id',
        string="Avoirs rattaches",
    )
    agh_original_invoice_id = fields.Many2one(
        comodel_name='account.move',
        string="Facture d'origine",
        ondelete='set null',
        help="Facture originale pour un avoir",
    )
    agh_relance_date = fields.Date(
        string="Date prochaine relance",
        compute='_compute_relance_date',
        store=True,
    )
    agh_relance_count = fields.Integer(
        string="Nombre de relances",
        default=0,
        readonly=True,
        copy=False,
    )
    agh_payment_state_ext = fields.Selection(
        selection=[
            ('draft', "Brouillon"),
            ('posted', "Valide"),
            ('partial', "Paye partiel"),
            ('paid', "Paye"),
            ('not_paid', "Non paye"),
            ('cancel', "Annule"),
        ],
        string="Etat paiement etendu",
        compute='_compute_payment_state_ext',
        store=True,
    )
    agh_email_sent = fields.Boolean(
        string="Email envoye",
        default=False,
        copy=False,
    )
    agh_receipt_confirmed = fields.Boolean(
        string="Accuse reception confirme",
        default=False,
        copy=False,
    )
    agh_acompte_amount = fields.Monetary(
        string="Montant acompte",
        currency_field='currency_id',
        compute='_compute_acompte_amount',
    )
    agh_rest_a_payer = fields.Monetary(
        string="Reste a payer",
        currency_field='currency_id',
        compute='_compute_rest_a_payer',
    )
    agh_dso_days = fields.Integer(
        string="DSO (jours)",
        compute='_compute_dso',
        store=True,
    )
    agh_late_days = fields.Integer(
        string="Jours de retard",
        compute='_compute_late_days',
        store=True,
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('invoice_date_due', 'payment_state', 'state')
    def _compute_late_days(self):
        today = fields.Date.context_today(self)
        for move in self:
            late = 0
            if (
                move.state == 'posted'
                and move.payment_state not in ('paid', 'reversed', 'invoicing_legacy')
                and move.invoice_date_due
            ):
                due_date = move.invoice_date_due
                if due_date < today:
                    late = (today - due_date).days
            move.agh_late_days = late

    @api.depends('invoice_date', 'payment_state', 'line_ids', 'line_ids.date',
                 'line_ids.credit', 'line_ids.account_type')
    def _compute_dso(self):
        for move in self:
            dso = 0
            if move.payment_state == 'paid' and move.invoice_date:
                payment_date = move._get_payment_date()
                if payment_date:
                    dso = (payment_date - move.invoice_date).days
            move.agh_dso_days = dso

    def _get_payment_date(self):
        """Recupere la date du dernier paiement encaisse sur la facture."""
        self.ensure_one()
        payment_lines = self.line_ids.filtered(
            lambda line: line.account_type == 'asset_receivable' and line.credit > 0
        )
        if payment_lines:
            return max(payment_lines.mapped('date'))
        return False

    @api.depends('amount_residual', 'payment_state')
    def _compute_rest_a_payer(self):
        for move in self:
            move.agh_rest_a_payer = move.amount_residual or 0.0

    @api.depends('agh_acompte_ids', 'agh_acompte_ids.amount')
    def _compute_acompte_amount(self):
        for move in self:
            move.agh_acompte_amount = sum(move.agh_acompte_ids.mapped('amount'))

    @api.depends('payment_state', 'state')
    def _compute_payment_state_ext(self):
        for move in self:
            if move.state == 'cancel':
                move.agh_payment_state_ext = 'cancel'
            elif move.state == 'draft':
                move.agh_payment_state_ext = 'draft'
            elif move.payment_state == 'paid':
                move.agh_payment_state_ext = 'paid'
            elif move.payment_state == 'partial':
                move.agh_payment_state_ext = 'partial'
            elif move.payment_state in ('not_paid', 'in_payment'):
                move.agh_payment_state_ext = 'not_paid'
            else:
                move.agh_payment_state_ext = 'posted'

    @api.depends('agh_relance_count', 'invoice_date_due', 'payment_state', 'state')
    def _compute_relance_date(self):
        """Calcule la date de prochaine relance (J+15, J+30, J+60)."""
        for move in self:
            relance_date = False
            if (
                move.state == 'posted'
                and move.payment_state in ('not_paid', 'partial', 'in_payment')
                and move.invoice_date_due
            ):
                count = move.agh_relance_count or 0
                offsets = {0: 15, 1: 30, 2: 60}
                if count in offsets:
                    relance_date = move.invoice_date_due + timedelta(days=offsets[count])
            move.agh_relance_date = relance_date

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.move_type in ('out_invoice', 'out_refund') and not move.agh_sequence_maroc:
                move._generate_maroc_sequence()
        return moves

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund') and not move.agh_sequence_maroc:
                move._generate_maroc_sequence()
        return res

    # ------------------------------------------------------------------
    # Numerotation marocaine FAC-YYYY-NNNN
    # ------------------------------------------------------------------
    def _generate_maroc_sequence(self):
        """Genere la sequence au format PREFIX-YYYY-NNNN."""
        for move in self:
            if move.agh_sequence_maroc:
                continue

            year = datetime.now().year
            journal = move.journal_id or self.env['account.journal'].search(
                [('type', '=', 'sale'), ('company_id', '=', move.company_id.id)],
                limit=1,
            )

            if journal:
                prefix = (journal.code or 'FAC').upper()
            else:
                prefix = 'FAC'

            domain = [
                ('agh_sequence_maroc', 'like', f'{prefix}-{year}-%'),
                ('move_type', '=', move.move_type),
                ('company_id', '=', move.company_id.id),
            ]
            last_move = self.sudo().search(domain, order='agh_sequence_maroc desc', limit=1)

            new_number = 1
            if last_move and last_move.agh_sequence_maroc:
                match = re.search(rf'{re.escape(prefix)}-{year}-(\d+)', last_move.agh_sequence_maroc)
                if match:
                    new_number = int(match.group(1)) + 1

            move.agh_sequence_maroc = f"{prefix}-{year}-{new_number:04d}"

    # ------------------------------------------------------------------
    # Actions metier
    # ------------------------------------------------------------------
    def action_send_invoice_email(self):
        self.ensure_one()
        return {
            'name': _("Envoyer la facture par email"),
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.send.invoice',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }

    def action_relance_impaye(self):
        self.ensure_one()
        return {
            'name': _("Relance pour impaye"),
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.relance.impaye',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
            },
        }

    def action_increment_relance(self):
        for move in self:
            move.agh_relance_count = (move.agh_relance_count or 0) + 1

    def action_reopen_canceled(self):
        """Reouvre une facture annulee (manager comptable uniquement)."""
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_("Seuls les managers comptables peuvent reouvrir une facture annulee."))
        if self.state == 'cancel':
            self.button_draft()

    # ------------------------------------------------------------------
    # Contraintes
    # ------------------------------------------------------------------
    @api.constrains('agh_sequence_maroc', 'state')
    def _check_sequence_maroc(self):
        pattern = re.compile(r'^[A-Z0-9]{2,8}-\d{4}-\d{4}$')
        for move in self:
            if move.agh_sequence_maroc and move.state == 'posted':
                if not pattern.match(move.agh_sequence_maroc):
                    raise ValidationError(_(
                        "La sequence doit etre au format: XXX-YYYY-NNNN\n"
                        "Exemple: FAC-2025-0042"
                    ))

    # ------------------------------------------------------------------
    # KPI Dashboard (appele depuis dashboard.js)
    # ------------------------------------------------------------------
    @api.model
    def get_invoice_dashboard_data(self):
        """Retourne les KPI agreges pour le tableau de bord."""
        Move = self.env['account.move']
        company = self.env.company

        domain_posted = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('company_id', '=', company.id),
        ]
        domain_unpaid = domain_posted + [
            ('payment_state', 'in', ('not_paid', 'partial', 'in_payment')),
        ]
        domain_overdue = domain_unpaid + [('agh_late_days', '>', 0)]

        posted_invoices = Move.search(domain_posted)
        unpaid_invoices = Move.search(domain_unpaid)
        overdue_invoices = Move.search(domain_overdue)

        total_ca = sum(posted_invoices.mapped('amount_total'))
        total_unpaid = sum(unpaid_invoices.mapped('amount_residual'))
        overdue_count = len(overdue_invoices)

        return {
            'totalCA': float(total_ca),
            'totalUnpaid': float(total_unpaid),
            'overdueCount': int(overdue_count),
            'currency': company.currency_id.symbol or '',
        }
