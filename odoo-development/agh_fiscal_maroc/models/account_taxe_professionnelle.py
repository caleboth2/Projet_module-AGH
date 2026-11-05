# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountTaxeProfessionnelle(models.Model):
    _name = 'account.taxe.professionnelle'
    _description = 'Taxe Professionnelle Maroc'
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

    # Catégorie d'activité (Code Général des Impôts Maroc)
    category = fields.Selection(
        selection=[
            ('a', 'Catégorie A'),
            ('b', 'Catégorie B'),
            ('c', 'Catégorie C'),
        ],
        string="Catégorie",
        default='a',
    )
    activity_description = fields.Char(string="Description activité")
    location = fields.Char(string="Lieu d'exercice")

    # Bases de calcul
    rental_value = fields.Monetary(
        string="Valeur locative", currency_field='currency_id'
    )
    fixed_assets_value = fields.Monetary(
        string="Valeur immobilisations", currency_field='currency_id'
    )
    total_base = fields.Monetary(
        string="Base totale TP",
        compute='_compute_total_base',
        store=True,
        currency_field='currency_id',
    )

    # Taux et calcul
    municipal_rate = fields.Float(string="Taux communal (%)", default=10.0)
    regional_rate = fields.Float(string="Taux régional (%)", default=5.0)

    municipal_tp = fields.Monetary(
        string="TP communale",
        compute='_compute_tp_amounts',
        store=True,
        currency_field='currency_id',
    )
    regional_tp = fields.Monetary(
        string="TP régionale",
        compute='_compute_tp_amounts',
        store=True,
        currency_field='currency_id',
    )
    total_tp = fields.Monetary(
        string="Total TP",
        compute='_compute_tp_amounts',
        store=True,
        currency_field='currency_id',
    )

    # Exonération
    is_exonerated = fields.Boolean(string="Exonéré (5 premières années)")
    exoneration_end_date = fields.Date(string="Fin exonération")

    # Paiement
    payment_date = fields.Date(string="Date paiement", copy=False)
    payment_ref = fields.Char(string="Référence paiement", copy=False)

    line_ids = fields.One2many(
        'account.taxe.professionnelle.line',
        'tp_id',
        string="Détail",
    )

    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'account.taxe.professionnelle'
                ) or _('New')
        return super().create(vals_list)

    @api.depends('rental_value', 'fixed_assets_value')
    def _compute_total_base(self):
        for record in self:
            record.total_base = record.rental_value + record.fixed_assets_value

    @api.depends('total_base', 'municipal_rate', 'regional_rate', 'is_exonerated')
    def _compute_tp_amounts(self):
        for record in self:
            if record.is_exonerated:
                record.municipal_tp = 0.0
                record.regional_tp = 0.0
                record.total_tp = 0.0
            else:
                record.municipal_tp = record.total_base * (record.municipal_rate / 100.0)
                record.regional_tp = record.total_base * (record.regional_rate / 100.0)
                record.total_tp = record.municipal_tp + record.regional_tp

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


class AccountTaxeProfessionnelleLine(models.Model):
    _name = 'account.taxe.professionnelle.line'
    _description = 'Ligne Taxe Professionnelle'

    tp_id = fields.Many2one(
        'account.taxe.professionnelle',
        string="TP",
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        related='tp_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='tp_id.currency_id',
        store=True,
    )
    description = fields.Char(string="Description")
    base_amount = fields.Monetary(string="Base", currency_field='currency_id')
    rate = fields.Float(string="Taux (%)")
    amount = fields.Monetary(
        string="Montant",
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('base_amount', 'rate')
    def _compute_amount(self):
        for record in self:
            record.amount = record.base_amount * (record.rate / 100.0)
