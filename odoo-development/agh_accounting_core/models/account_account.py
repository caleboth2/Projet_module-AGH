# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    """
    Extension du compte comptable Odoo pour les besoins du PCM marocain.
    Ajout du type PCM, gestion analytique par défaut, et verrouillage de période.
    """
    _inherit = 'account.account'

    # ── Type PCM ─────────────────────────────────────────────────────────────
    pcm_account_type = fields.Selection([
        ('immobilisation', 'Immobilisation'),
        ('amortissement', 'Amortissement / Dépréciation'),
        ('stock', 'Stock'),
        ('creance_client', 'Créance client'),
        ('dette_fournisseur', 'Dette fournisseur'),
        ('tresorerie', 'Trésorerie'),
        ('capital', 'Capital et réserves'),
        ('emprunt', 'Emprunt et dettes financières'),
        ('charge_exploitation', "Charge d'exploitation"),
        ('charge_financiere', 'Charge financière'),
        ('charge_exceptionnelle', 'Charge exceptionnelle'),
        ('produit_exploitation', "Produit d'exploitation"),
        ('produit_financier', 'Produit financier'),
        ('produit_exceptionnel', 'Produit exceptionnel'),
        ('tva_collectee', 'TVA collectée'),
        ('tva_deductible', 'TVA déductible'),
        ('resultat', 'Résultat'),
        ('analytique', 'Compte analytique'),
        ('autre', 'Autre'),
    ], string='Type PCM', index=True,
        help="Classification selon le Plan Comptable Marocain.")

    # ── Analytique ───────────────────────────────────────────────────────────
    analytical_default_id = fields.Many2one(
        'account.analytic.account',
        string='Axe analytique par défaut',
        help="Axe analytique imputé automatiquement lors de la saisie "
             "d'une écriture sur ce compte."
    )

    analytic_distribution_default = fields.Json(
        string='Répartition analytique par défaut',
        help="Distribution analytique par défaut (JSON) pour ce compte."
    )

    # ── Verrouillage ─────────────────────────────────────────────────────────
    lock_date_restriction = fields.Selection([
        ('none', 'Aucune restriction'),
        ('soft', 'Verrouillage souple (avertissement)'),
        ('hard', 'Verrouillage strict (blocage)'),
    ], string='Restriction de période', default='none',
        help="Niveau de restriction de saisie sur les périodes clôturées.")

    # ── Flags ────────────────────────────────────────────────────────────────
    is_tax_account = fields.Boolean(
        string='Compte de TVA',
        default=False,
        help="Ce compte est dédié à la TVA (collectée ou déductible)."
    )

    is_ras_account = fields.Boolean(
        string='Compte RAS',
        default=False,
        help="Compte de retenue à la source (4456xx)."
    )

    is_immobilisation = fields.Boolean(
        string='Compte d\'immobilisation',
        compute='_compute_is_immobilisation', store=True,
        help="Calculé automatiquement si le compte commence par 2."
    )

    # ── Amortissement ────────────────────────────────────────────────────────
    depreciation_method = fields.Selection([
        ('linear', 'Linéaire'),
        ('degressive', 'Dégressif'),
    ], string='Méthode d\'amortissement', default='linear')

    depreciation_rate = fields.Float(
        string='Taux d\'amortissement (%)',
        digits=(5, 2),
        help="Taux annuel d'amortissement pour ce type d'immobilisation."
    )

    # ── Computed ─────────────────────────────────────────────────────────────
    pcm_class = fields.Char(
        string='Classe PCM',
        compute='_compute_pcm_class', store=True, size=1
    )

    pcm_class_label = fields.Char(
        string='Libellé classe PCM',
        compute='_compute_pcm_class', store=True
    )

    # ── Constrains & computes ────────────────────────────────────────────────
    @api.depends('code')
    def _compute_pcm_class(self):
        labels = {
            '1': "Financement permanent",
            '2': "Actif immobilisé",
            '3': "Actif circulant",
            '4': "Passif circulant",
            '5': "Trésorerie",
            '6': "Charges",
            '7': "Produits",
            '8': "Résultats",
            '9': "Comptes analytiques",
        }
        for account in self:
            if account.code and account.code[0].isdigit():
                cls = account.code[0]
                account.pcm_class = cls
                account.pcm_class_label = labels.get(cls, '')
            else:
                account.pcm_class = False
                account.pcm_class_label = ''

    @api.depends('code')
    def _compute_is_immobilisation(self):
        for account in self:
            account.is_immobilisation = bool(
                account.code and account.code.startswith('2')
            )

    @api.constrains('code')
    def _check_pcm_code(self):
        for account in self:
            if account.code and not account.code[0].isdigit():
                raise ValidationError(
                    _("Le code du compte '%s' doit commencer par un chiffre "
                      "conformément au Plan Comptable Marocain.") % account.code
                )
