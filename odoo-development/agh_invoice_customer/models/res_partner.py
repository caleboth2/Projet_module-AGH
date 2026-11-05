# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------------------------------------------------------
    # Identification fiscale marocaine
    # ------------------------------------------------------------------
    agh_ice = fields.Char(
        string="ICE (Identifiant Commun Entreprise)",
        size=15,
        help="Identifiant Commun de l'Entreprise (15 chiffres).",
    )
    agh_if = fields.Char(
        string="Identifiant Fiscal (IF)",
        help="Numero d'Identifiant Fiscal attribue par la DGI.",
    )
    agh_rc = fields.Char(
        string="Registre de Commerce (RC)",
        help="Numero d'inscription au Registre de Commerce.",
    )
    agh_cnss = fields.Char(
        string="N. CNSS",
        help="Numero d'affiliation a la CNSS.",
    )
    agh_tp = fields.Char(
        string="Taxe Professionnelle (N.)",
        help="Numero de la Taxe Professionnelle (ex Patente).",
    )

    # ------------------------------------------------------------------
    # Parametres facturation / recouvrement
    # ------------------------------------------------------------------
    agh_payment_delay = fields.Integer(
        string="Delai de paiement (jours)",
        default=30,
    )
    agh_credit_limit = fields.Monetary(
        string="Limite de credit",
        currency_field='currency_id',
        help="Plafond maximum de credit accorde au client.",
    )
    agh_alert_exceed_limit = fields.Boolean(
        string="Alerter si depassement plafond",
        default=True,
    )
    agh_relance_auto = fields.Boolean(
        string="Relances automatiques",
        default=False,
    )
    agh_relance_emails = fields.Many2many(
        comodel_name='res.partner',
        relation='agh_partner_relance_emails_rel',
        column1='partner_id',
        column2='contact_id',
        string="Contacts relance",
        help="Contacts a inclure dans les emails de relance.",
    )
    agh_payment_incidents = fields.Text(
        string="Incidents de paiement",
        help="Historique libre des incidents de paiement.",
    )

    # ------------------------------------------------------------------
    # Statistiques recouvrement (computed)
    # ------------------------------------------------------------------
    agh_total_due = fields.Monetary(
        string="Total du",
        currency_field='currency_id',
        compute='_compute_agh_recouvrement_stats',
    )
    agh_overdue_amount = fields.Monetary(
        string="Dont en retard",
        currency_field='currency_id',
        compute='_compute_agh_recouvrement_stats',
    )
    agh_avg_payment_days = fields.Float(
        string="Delai moyen paiement (jours)",
        compute='_compute_agh_recouvrement_stats',
        digits=(8, 2),
    )
    agh_outstanding_amount = fields.Monetary(
        string="Encours client",
        currency_field='currency_id',
        compute='_compute_agh_recouvrement_stats',
    )
    agh_dso_average = fields.Float(
        string="DSO Moyen (jours)",
        compute='_compute_agh_recouvrement_stats',
        digits=(8, 2),
    )

    @api.depends('name')
    def _compute_agh_recouvrement_stats(self):
        Move = self.env['account.move']
        for partner in self:
            total_due = 0.0
            overdue_amount = 0.0
            dso_total = 0.0
            dso_count = 0

            if partner.id:
                unpaid = Move.search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ('not_paid', 'partial', 'in_payment')),
                ])
                total_due = sum(unpaid.mapped('amount_residual'))
                overdue_amount = sum(
                    unpaid.filtered(lambda m: (m.agh_late_days or 0) > 0).mapped('amount_residual')
                )

                paid = Move.search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', '=', 'paid'),
                ])
                for inv in paid:
                    if inv.agh_dso_days and inv.agh_dso_days > 0:
                        dso_total += inv.agh_dso_days
                        dso_count += 1

            avg_days = (dso_total / dso_count) if dso_count else 0.0

            partner.agh_total_due = total_due
            partner.agh_overdue_amount = overdue_amount
            partner.agh_outstanding_amount = total_due
            partner.agh_avg_payment_days = avg_days
            partner.agh_dso_average = avg_days
