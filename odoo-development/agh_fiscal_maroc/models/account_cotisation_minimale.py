# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountCotisationMinimale(models.Model):
    _name = 'account.cotisation.minimale'
    _description = 'Cotisation Minimale Maroc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fiscal_year desc'

    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
    )

    fiscal_year = fields.Char(string="Exercice fiscal", required=True, tracking=True)

    state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('calculated', 'Calculée'),
            ('confirmed', 'Confirmée'),
            ('paid', 'Payée'),
            ('cancelled', 'Annulée'),
        ],
        string="Statut",
        default='draft',
        tracking=True,
        copy=False,
    )

    # Base de calcul
    total_revenue_ttc = fields.Monetary(
        string="Chiffre d'affaires TTC", currency_field='currency_id'
    )
    other_products = fields.Monetary(
        string="Autres produits", currency_field='currency_id'
    )
    total_base = fields.Monetary(
        string="Base totale CM",
        compute='_compute_total_base',
        store=True,
        currency_field='currency_id',
    )

    # Calcul CM
    cm_rate = fields.Float(string="Taux CM (%)", default=0.5)
    cm_amount = fields.Monetary(
        string="Montant CM",
        compute='_compute_cm_amount',
        store=True,
        currency_field='currency_id',
    )
    minimum_cm = fields.Monetary(
        string="CM minimum (3000 MAD)",
        default=3000.0,
        currency_field='currency_id',
    )
    cm_to_pay = fields.Monetary(
        string="CM à payer",
        compute='_compute_cm_to_pay',
        store=True,
        currency_field='currency_id',
    )

    # Comparaison avec IS
    is_amount = fields.Monetary(
        string="Montant IS", currency_field='currency_id'
    )
    is_higher_than_cm = fields.Boolean(
        string="IS > CM", compute='_compute_comparison'
    )
    final_tax_amount = fields.Monetary(
        string="Impôt retenu",
        compute='_compute_final_tax',
        store=True,
        currency_field='currency_id',
    )

    payment_date = fields.Date(string="Date paiement", copy=False)
    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'account.cotisation.minimale'
                ) or _('New')
        return super().create(vals_list)

    @api.depends('total_revenue_ttc', 'other_products')
    def _compute_total_base(self):
        for record in self:
            record.total_base = record.total_revenue_ttc + record.other_products

    @api.depends('total_base', 'cm_rate')
    def _compute_cm_amount(self):
        for record in self:
            record.cm_amount = record.total_base * (record.cm_rate / 100.0)

    @api.depends('cm_amount', 'minimum_cm')
    def _compute_cm_to_pay(self):
        for record in self:
            record.cm_to_pay = max(record.cm_amount, record.minimum_cm)

    @api.depends('is_amount', 'cm_amount')
    def _compute_comparison(self):
        for record in self:
            record.is_higher_than_cm = record.is_amount > record.cm_amount

    @api.depends('is_amount', 'cm_to_pay')
    def _compute_final_tax(self):
        for record in self:
            record.final_tax_amount = max(record.is_amount, record.cm_to_pay)

    def action_calculate(self):
        for record in self:
            record.state = 'calculated'

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_pay(self):
        for record in self:
            record.write({
                'state': 'paid',
                'payment_date': fields.Date.today(),
            })

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_draft(self):
        for record in self:
            record.state = 'draft'
