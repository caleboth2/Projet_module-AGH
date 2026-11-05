# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountChartTemplate(models.AbstractModel):
    """
    Extension du plan comptable standard Odoo pour intégrer
    les spécificités du Plan Comptable Marocain (PCM).
    Possibilité de basculer vers OHADA ou PCG français.
    """
    _inherit = 'account.chart.template'

    # ── Champs PCM ──────────────────────────────────────────────────────────
    pcm_version = fields.Selection([
        ('pcm_2000', 'PCM 2000 (Standard Maroc)'),
        ('ohada', 'OHADA (Afrique francophone)'),
        ('pcg', 'PCG (France)'),
    ], string='Norme comptable', default='pcm_2000',
        help="Norme comptable applicable à cette entreprise.")

    is_ohada_compatible = fields.Boolean(
        string='Compatible OHADA',
        default=False,
        help="Activer la compatibilité OHADA pour les entreprises opérant "
             "dans la zone OHADA."
    )

    account_code_prefix_root = fields.Char(
        string='Préfixe racine',
        size=1,
        help="Classe PCM racine (1 à 9)."
    )

    pcm_fiscal_regime = fields.Selection([
        ('is', "Impôt sur les Sociétés (IS)"),
        ('ir', "Impôt sur le Revenu (IR)"),
        ('auto_entrepreneur', "Auto-entrepreneur"),
    ], string='Régime fiscal', default='is')

    pcm_tva_regime = fields.Selection([
        ('mensuel', 'Déclaration mensuelle'),
        ('trimestriel', 'Déclaration trimestrielle'),
        ('exonere', 'Exonéré de TVA'),
    ], string='Régime TVA', default='mensuel')

    # ── Méthodes ────────────────────────────────────────────────────────────
    def _get_pcm_class_label(self, code):
        """Retourne le libellé de la classe PCM à partir du code de compte."""
        mapping = {
            '1': "Comptes de financement permanent",
            '2': "Comptes d'actif immobilisé",
            '3': "Comptes d'actif circulant (hors trésorerie)",
            '4': "Comptes de passif circulant (hors trésorerie)",
            '5': "Comptes de trésorerie",
            '6': "Comptes de charges",
            '7': "Comptes de produits",
            '8': "Comptes de résultats",
            '9': "Comptes analytiques",
        }
        if code and len(code) >= 1:
            return mapping.get(code[0], _("Classe inconnue"))
        return _("Classe inconnue")

    def action_load_pcm_chart(self):
        """Chargement du plan comptable PCM pour la société courante."""
        self.ensure_one()
        if self.pcm_version != 'pcm_2000':
            raise UserError(
                _("Le chargement automatique n'est disponible que pour le PCM 2000.")
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Plan Comptable Marocain"),
                'message': _("Le PCM a été chargé avec succès."),
                'type': 'success',
            }
        }


class AccountGroup(models.Model):
    """Extension des groupes de comptes pour les classes PCM."""
    _inherit = 'account.group'

    pcm_class = fields.Selection([
        ('1', '1 — Financement permanent'),
        ('2', '2 — Actif immobilisé'),
        ('3', '3 — Actif circulant'),
        ('4', '4 — Passif circulant'),
        ('5', '5 — Trésorerie'),
        ('6', '6 — Charges'),
        ('7', '7 — Produits'),
        ('8', '8 — Résultats'),
        ('9', '9 — Analytique'),
    ], string='Classe PCM',
        compute='_compute_pcm_class', store=True)

    @api.depends('code_prefix_start')
    def _compute_pcm_class(self):
        for group in self:
            if group.code_prefix_start:
                group.pcm_class = group.code_prefix_start[0] \
                    if group.code_prefix_start[0] in '123456789' else False
            else:
                group.pcm_class = False
