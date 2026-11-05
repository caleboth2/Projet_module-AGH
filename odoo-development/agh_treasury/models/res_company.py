# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    agh_treasury_alert_email = fields.Char(string='Email alertes tresorerie')
    agh_default_reconcile_tolerance = fields.Float(
        string='Tolerance rapprochement par defaut (%)',
        default=0.01,
    )
    agh_forecast_horizon_days = fields.Integer(
        string='Horizon prevision (jours)',
        default=90,
    )
    agh_min_bank_balance = fields.Monetary(
        string='Solde bancaire minimum',
        currency_field='currency_id',
        help='Seuil minimum pour les alertes',
    )
