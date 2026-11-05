# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Extension de la pièce comptable (account.move) pour le PCM marocain.
    - Contrôle débit/crédit
    - Piste d'audit horodatée
    - Gestion des exercices et périodes
    - Écritures de régularisation
    - Comptabilité analytique
    """
    _inherit = 'account.move'

    # ── Exercice / Période ───────────────────────────────────────────────────
    fiscal_year_id = fields.Many2one(
        'account.fiscal.year',
        string='Exercice comptable',
        compute='_compute_fiscal_year', store=True,
        help="Exercice comptable déterminé à partir de la date de pièce."
    )

    # ── Contrôle équilibre ───────────────────────────────────────────────────
    debit_total = fields.Monetary(
        string='Total débit',
        compute='_compute_debit_credit_total',
        currency_field='currency_id'
    )

    credit_total = fields.Monetary(
        string='Total crédit',
        compute='_compute_debit_credit_total',
        currency_field='currency_id'
    )

    balance_ok = fields.Boolean(
        string='Écriture équilibrée',
        compute='_compute_debit_credit_total',
        help="Vrai si débit = crédit."
    )

    # ── Type d'écriture PCM ──────────────────────────────────────────────────
    pcm_move_type = fields.Selection([
        ('normal', 'Écriture normale'),
        ('regularisation', 'Écriture de régularisation'),
        ('cloture', 'Écriture de clôture'),
        ('ouverture', "Écriture d'ouverture"),
        ('extourne', 'Extourne'),
        ('immobilisation', 'Immobilisation'),
        ('amortissement', 'Dotation aux amortissements'),
    ], string='Type d\'écriture PCM', default='normal')

    is_regularisation = fields.Boolean(
        string='Écriture de régularisation',
        default=False,
        help="Charges constatées d'avance, produits à recevoir, etc."
    )

    regularisation_type = fields.Selection([
        ('cca', "Charges constatées d'avance"),
        ('pca', "Produits constatés d'avance"),
        ('far', "Fournisseurs — factures à recevoir"),
        ('car', "Clients — avoirs à établir"),
        ('cpay', 'Charges à payer'),
        ('prec', 'Produits à recevoir'),
    ], string='Type de régularisation')

    extourne_date = fields.Date(
        string='Date d\'extourne',
        help="Si renseignée, une extourne sera générée à cette date."
    )

    extourne_move_id = fields.Many2one(
        'account.move',
        string='Écriture d\'extourne',
        readonly=True, copy=False
    )

    # ── Piste d'audit ────────────────────────────────────────────────────────
    audit_trail_ids = fields.One2many(
        'account.move.audit',
        'move_id',
        string='Piste d\'audit',
        readonly=True
    )

    last_modified_by = fields.Many2one(
        'res.users',
        string='Dernière modification par',
        readonly=True
    )

    last_modified_date = fields.Datetime(
        string='Date dernière modification',
        readonly=True
    )

    # ── Analytique ───────────────────────────────────────────────────────────
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Axe analytique principal',
        help="Axe analytique propagé sur toutes les lignes de la pièce."
    )

    # ── Computed ─────────────────────────────────────────────────────────────
    @api.depends('date', 'company_id')
    def _compute_fiscal_year(self):
        FiscalYear = self.env['account.fiscal.year']
        for move in self:
            if move.date and move.company_id:
                fy = FiscalYear.search([
                    ('date_from', '<=', move.date),
                    ('date_to', '>=', move.date),
                    ('company_id', '=', move.company_id.id),
                ], limit=1)
                move.fiscal_year_id = fy
            else:
                move.fiscal_year_id = False

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_debit_credit_total(self):
        for move in self:
            lines = move.line_ids
            move.debit_total = sum(lines.mapped('debit'))
            move.credit_total = sum(lines.mapped('credit'))
            move.balance_ok = abs(move.debit_total - move.credit_total) < 0.01

    # ── Override write/create pour audit ─────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            move._log_audit('create', "Création de la pièce comptable.")
        return moves

    def write(self, vals):
        # Enregistrer l'état avant modification pour l'audit
        pre_states = {move.id: move.state for move in self}
        result = super().write(vals)
        for move in self:
            changes = []
            if 'state' in vals and pre_states.get(move.id) != vals['state']:
                changes.append(
                    _("État changé : %s → %s") % (pre_states[move.id], vals['state'])
                )
            if changes or 'line_ids' in vals:
                move._log_audit('write', ' | '.join(changes) if changes else _("Modification des lignes."))
                move.last_modified_by = self.env.uid
                move.last_modified_date = fields.Datetime.now()
        return result

    def _log_audit(self, action, description):
        """Enregistre une entrée dans la piste d'audit."""
        self.ensure_one()
        self.env['account.move.audit'].sudo().create({
            'move_id': self.id,
            'action': action,
            'description': description,
            'user_id': self.env.uid,
            'date': fields.Datetime.now(),
            'move_state': self.state,
        })

    # ── Contrôles avant validation ────────────────────────────────────────────
    def action_post(self):
        for move in self:
            # 1. Contrôle équilibre débit/crédit
            if not move.balance_ok:
                raise UserError(
                    _("La pièce '%s' n'est pas équilibrée : Débit %s ≠ Crédit %s.") % (
                        move.name, move.debit_total, move.credit_total)
                )
            # 2. Contrôle de la date de verrouillage
            move._check_agh_lock_date()
        result = super().action_post()
        # Générer l'extourne si demandée
        for move in self.filtered(lambda m: m.extourne_date and not m.extourne_move_id):
            move._generate_extourne()
        return result

    def _check_agh_lock_date(self):
        """Empêche la création/validation d'écritures avant la date de verrouillage."""
        for move in self:
            company = move.company_id or self.env.company
            lock = company.agh_fiscalyear_lock_date
            if lock and move.date and move.date <= lock:
                raise UserError(_(
                    "Impossible de valider la pièce '%s' : la période est verrouillée "
                    "jusqu'au %s pour tous les utilisateurs."
                ) % (move.name or '/', lock))
            period_lock = company.agh_period_lock_date
            if (period_lock and move.date and move.date <= period_lock
                    and not self.env.user.has_group('account.group_account_manager')):
                raise UserError(_(
                    "Impossible de valider la pièce '%s' : la période est verrouillée "
                    "jusqu'au %s pour les utilisateurs non comptables."
                ) % (move.name or '/', period_lock))

    def _generate_extourne(self):
        """Génère l'écriture d'extourne à la date indiquée."""
        self.ensure_one()
        extourne = self.copy({
            'date': self.extourne_date,
            'ref': _("Extourne de %s") % (self.ref or self.name),
            'pcm_move_type': 'extourne',
            'extourne_date': False,
        })
        # Inverser débit/crédit
        for line in extourne.line_ids:
            line.write({
                'debit': line.credit,
                'credit': line.debit,
            })
        self.extourne_move_id = extourne
        _logger.info("Extourne %s générée pour %s.", extourne.name, self.name)


class AccountMoveAudit(models.Model):
    """Piste d'audit horodatée de toutes les modifications des pièces comptables."""
    _name = 'account.move.audit'
    _description = 'Piste d\'audit — Écritures comptables'
    _order = 'date desc'

    move_id = fields.Many2one(
        'account.move', string='Pièce comptable',
        required=True, ondelete='cascade', index=True
    )
    action = fields.Selection([
        ('create', 'Création'),
        ('write', 'Modification'),
        ('cancel', 'Annulation'),
        ('post', 'Validation'),
        ('reset', 'Remise en brouillon'),
    ], string='Action', required=True)
    description = fields.Text(string='Description')
    user_id = fields.Many2one('res.users', string='Utilisateur', required=True)
    date = fields.Datetime(string='Date/Heure', required=True)
    move_state = fields.Char(string='État de la pièce')
    ip_address = fields.Char(string='Adresse IP', size=45)

    @api.model_create_multi
    def create(self, vals_list):
        # Enrichir avec l'IP si disponible
        request = self.env.context.get('request')
        ip = getattr(request, 'httprequest', None)
        ip = getattr(ip, 'remote_addr', '') if ip else ''
        for vals in vals_list:
            if ip:
                vals['ip_address'] = ip
        return super().create(vals_list)
