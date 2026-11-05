# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    """
    Extension des journaux comptables pour le PCM marocain.
    Journaux préconfigurés : VTE, ACH, BQ, CAI, OD, PAI.
    """
    _inherit = 'account.journal'

    # ── Type de journal PCM ──────────────────────────────────────────────────
    pcm_journal_type = fields.Selection([
        ('vente', 'Journal des ventes (VTE)'),
        ('achat', 'Journal des achats (ACH)'),
        ('banque', 'Journal de banque (BQ)'),
        ('caisse', 'Journal de caisse (CAI)'),
        ('od', 'Opérations diverses (OD)'),
        ('paie', 'Journal de paie (PAI)'),
        ('immob', 'Journal des immobilisations (IMB)'),
        ('extourne', 'Journal des extournes (EXT)'),
    ], string='Type journal PCM')

    # ── Clôture ──────────────────────────────────────────────────────────────
    lock_posted_entries = fields.Boolean(
        string='Verrouiller les écritures validées',
        default=True,
        help="Empêche la modification des écritures comptabilisées."
    )

    requires_counterpart = fields.Boolean(
        string='Contrepartie obligatoire',
        default=True,
        help="Exige une contrepartie pour équilibrer les écritures."
    )

    # ── Numérotation ─────────────────────────────────────────────────────────
    sequence_prefix_pcm = fields.Char(
        string='Préfixe séquence PCM',
        size=10,
        help="Ex.: VTE, ACH, BQ01… Utilisé pour la numérotation DGI."
    )

    # ── Banque ───────────────────────────────────────────────────────────────
    bank_account_currency_id = fields.Many2one(
        related='bank_account_id.currency_id',
        string='Devise du compte bancaire',
        readonly=True
    )

    is_multicurrency = fields.Boolean(
        string='Multi-devises',
        default=False,
        help="Ce journal gère des opérations en devises étrangères (EUR, USD…)."
    )

    # ── Analytique ───────────────────────────────────────────────────────────
    default_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Axe analytique par défaut',
        help="Axe analytique appliqué par défaut sur toutes les lignes de ce journal."
    )

    # ── Validation ───────────────────────────────────────────────────────────
    @api.constrains('pcm_journal_type', 'type')
    def _check_pcm_journal_consistency(self):
        mapping = {
            'vente': 'sale',
            'achat': 'purchase',
            'banque': 'bank',
            'caisse': 'cash',
            'od': 'general',
            'paie': 'general',
            'immob': 'general',
            'extourne': 'general',
        }
        for journal in self:
            if journal.pcm_journal_type:
                expected = mapping.get(journal.pcm_journal_type)
                if expected and journal.type != expected:
                    raise ValidationError(
                        _("Le type de journal Odoo '%s' est incompatible avec le "
                          "type PCM '%s' (attendu : '%s').") % (
                            journal.type, journal.pcm_journal_type, expected)
                    )

    def get_journal_dashboard_datas(self):
        """Surcharge pour ajouter les indicateurs PCM au tableau de bord."""
        data = super().get_journal_dashboard_datas()
        self.ensure_one()
        data['pcm_journal_type'] = self.pcm_journal_type or ''
        data['sequence_prefix_pcm'] = self.sequence_prefix_pcm or ''
        return data
