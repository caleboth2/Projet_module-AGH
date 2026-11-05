# -*- coding: utf-8 -*-
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class AccountTreasuryForecast(models.Model):
    _name = 'account.treasury.forecast'
    _description = 'Prevision de tresorerie'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc'

    name = fields.Char(
        string='Nom prevision',
        default=lambda self: "Prevision %s" % datetime.now().strftime('%Y-%m-%d'),
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('in_progress', 'En cours'),
            ('done', 'Terminee'),
        ],
        string='Statut',
        default='draft',
        tracking=True,
        copy=False,
    )
    date = fields.Date(string='Date prevision', required=True, default=fields.Date.today)
    horizon = fields.Selection(
        selection=[
            ('30', '30 jours'),
            ('60', '60 jours'),
            ('90', '90 jours'),
        ],
        string='Horizon',
        required=True,
        default='30',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='company_id.currency_id',
        store=True,
    )

    forecast_line_ids = fields.One2many(
        'account.treasury.forecast.line',
        'forecast_id',
        string='Lignes de prevision',
    )

    total_inflow = fields.Monetary(
        string='Total encaissements',
        compute='_compute_totals',
        currency_field='currency_id',
        store=True,
    )
    total_outflow = fields.Monetary(
        string='Total decaissements',
        compute='_compute_totals',
        currency_field='currency_id',
        store=True,
    )
    net_flow = fields.Monetary(
        string='Flux net',
        compute='_compute_totals',
        currency_field='currency_id',
        store=True,
    )
    ending_balance = fields.Monetary(
        string='Solde final prevu',
        compute='_compute_ending_balance',
        currency_field='currency_id',
        store=True,
    )

    alert_threshold = fields.Monetary(
        string='Seuil alerte',
        currency_field='currency_id',
        default=10000,
    )
    has_alert = fields.Boolean(
        string='Alerte active',
        compute='_compute_has_alert',
        store=True,
    )

    @api.depends('forecast_line_ids.amount', 'forecast_line_ids.type')
    def _compute_totals(self):
        for forecast in self:
            inflow = sum(forecast.forecast_line_ids.filtered(lambda l: l.type == 'inflow').mapped('amount'))
            outflow = sum(forecast.forecast_line_ids.filtered(lambda l: l.type == 'outflow').mapped('amount'))
            forecast.total_inflow = inflow
            forecast.total_outflow = outflow
            forecast.net_flow = inflow - outflow

    @api.depends('net_flow', 'company_id')
    def _compute_ending_balance(self):
        for forecast in self:
            start_balance = forecast._get_starting_balance()
            forecast.ending_balance = start_balance + (forecast.net_flow or 0.0)

    @api.depends('ending_balance', 'alert_threshold')
    def _compute_has_alert(self):
        for forecast in self:
            forecast.has_alert = (forecast.ending_balance or 0.0) < (forecast.alert_threshold or 0.0)

    def _get_starting_balance(self):
        self.ensure_one()
        bank_journals = self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash']),
            ('company_id', '=', self.company_id.id),
        ])
        total = 0.0
        for journal in bank_journals:
            balance = getattr(journal, 'current_statement_balance', 0.0) or 0.0
            total += balance
        return total

    def action_generate_forecast(self):
        self.ensure_one()
        self.forecast_line_ids.unlink()
        end_date = self.date + relativedelta(days=int(self.horizon))
        Line = self.env['account.treasury.forecast.line']

        customer_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '>=', self.date),
            ('invoice_date_due', '<=', end_date),
            ('company_id', '=', self.company_id.id),
        ])
        for invoice in customer_invoices:
            Line.create({
                'forecast_id': self.id,
                'date': invoice.invoice_date_due,
                'type': 'inflow',
                'source_type': 'customer_invoice',
                'source_id': invoice.id,
                'amount': invoice.amount_residual,
                'description': "Facture client %s" % invoice.name,
                'partner_id': invoice.partner_id.id,
            })

        supplier_invoices = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '>=', self.date),
            ('invoice_date_due', '<=', end_date),
            ('company_id', '=', self.company_id.id),
        ])
        for invoice in supplier_invoices:
            Line.create({
                'forecast_id': self.id,
                'date': invoice.invoice_date_due,
                'type': 'outflow',
                'source_type': 'supplier_invoice',
                'source_id': invoice.id,
                'amount': invoice.amount_residual,
                'description': "Facture fournisseur %s" % invoice.name,
                'partner_id': invoice.partner_id.id,
            })

        self._generate_recurring_payments(end_date)
        self.state = 'in_progress'
        return True

    def _generate_recurring_payments(self, end_date):
        self.ensure_one()
        Line = self.env['account.treasury.forecast.line']
        recurring = self.env['account.recurring.payment'].search([
            ('active', '=', True),
            ('company_id', '=', self.company_id.id),
        ])
        for payment in recurring:
            current_date = payment.start_date
            frequency = max(payment.frequency or 1, 1)
            safety_iter = 0
            while current_date and current_date <= end_date and safety_iter < 240:
                Line.create({
                    'forecast_id': self.id,
                    'date': current_date,
                    'type': payment.type,
                    'source_type': 'recurring',
                    'amount': payment.amount,
                    'description': payment.name,
                    'partner_id': payment.partner_id.id if payment.partner_id else False,
                })
                current_date = current_date + relativedelta(months=frequency)
                safety_iter += 1

    def action_send_alert(self):
        self.ensure_one()
        return True


class AccountTreasuryForecastLine(models.Model):
    _name = 'account.treasury.forecast.line'
    _description = 'Ligne de prevision de tresorerie'
    _order = 'date'

    forecast_id = fields.Many2one(
        'account.treasury.forecast',
        string='Prevision',
        required=True,
        ondelete='cascade',
    )
    date = fields.Date(string='Date prevue', required=True)
    type = fields.Selection(
        selection=[
            ('inflow', 'Encaissement'),
            ('outflow', 'Decaissement'),
        ],
        string='Type',
        required=True,
    )
    source_type = fields.Selection(
        selection=[
            ('customer_invoice', 'Facture client'),
            ('supplier_invoice', 'Facture fournisseur'),
            ('recurring', 'Paiement recurrent'),
            ('manual', 'Manuel'),
        ],
        string='Source',
    )
    source_id = fields.Integer(string='ID Source')
    amount = fields.Monetary(string='Montant', currency_field='currency_id', required=True)
    probability = fields.Float(
        string='Probabilite (%)',
        default=100.0,
        help="Probabilite de realisation",
    )
    description = fields.Char(string='Description')
    partner_id = fields.Many2one('res.partner', string='Partenaire')
    currency_id = fields.Many2one('res.currency', related='forecast_id.currency_id', store=True)

    weighted_amount = fields.Monetary(
        string='Montant pondere',
        compute='_compute_weighted_amount',
        currency_field='currency_id',
        store=True,
    )

    @api.depends('amount', 'probability')
    def _compute_weighted_amount(self):
        for line in self:
            line.weighted_amount = (line.amount or 0.0) * ((line.probability or 0.0) / 100.0)


class AccountRecurringPayment(models.Model):
    _name = 'account.recurring.payment'
    _description = 'Paiement recurrent'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    type = fields.Selection(
        selection=[
            ('inflow', 'Encaissement'),
            ('outflow', 'Decaissement'),
        ],
        string='Type',
        required=True,
        default='outflow',
    )
    amount = fields.Monetary(string='Montant', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    partner_id = fields.Many2one('res.partner', string='Partenaire')
    start_date = fields.Date(string='Date debut', required=True, default=fields.Date.today)
    end_date = fields.Date(string='Date fin')
    frequency = fields.Integer(string='Frequence (mois)', default=1)
    account_id = fields.Many2one('account.account', string='Compte comptable')
    active = fields.Boolean(string='Actif', default=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )
