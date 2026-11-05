# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountEffetCommerce(models.Model):
    _name = 'account.effet.commerce'
    _description = 'Effet de commerce'
    _rec_name = 'name'
    _order = 'date_echeance desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('account.effet.commerce') or _('Nouveau'),
    )
    effet_type = fields.Selection(
        selection=[
            ('lc', 'Lettre de change'),
            ('bo', 'Billet a ordre'),
            ('cheque', 'Cheque'),
        ],
        string="Type d'effet",
        required=True,
        default='lc',
    )
    tireur_id = fields.Many2one('res.partner', string='Tireur', required=True)
    tire_id = fields.Many2one('res.partner', string='Tire')
    montant = fields.Monetary(string='Montant', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    date_creation = fields.Date(string='Date creation', default=fields.Date.today, required=True)
    date_echeance = fields.Date(string='Date echeance', required=True)
    interest_rate = fields.Float(string="Taux d'escompte (%)")
    date_remise = fields.Date(string='Date remise')
    discount_amount = fields.Monetary(
        string='Montant escompte',
        currency_field='currency_id',
        compute='_compute_discount',
        store=True,
    )
    net_amount = fields.Monetary(
        string='Montant net',
        currency_field='currency_id',
        compute='_compute_discount',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('remis', 'Remis'),
            ('encaisse', 'Encaisse'),
            ('impaye', 'Impaye'),
            ('annule', 'Annule'),
        ],
        string='Statut',
        default='draft',
        tracking=True,
        copy=False,
    )
    payment_id = fields.Many2one('account.payment', string='Paiement lie')
    invoice_id = fields.Many2one('account.move', string='Facture liee')
    observation = fields.Text(string='Observations')

    @api.depends('montant', 'interest_rate', 'date_creation', 'date_echeance')
    def _compute_discount(self):
        for effet in self:
            if effet.interest_rate and effet.date_creation and effet.date_echeance:
                days = (effet.date_echeance - effet.date_creation).days
                if days < 0:
                    days = 0
                effet.discount_amount = (effet.montant or 0.0) * (effet.interest_rate / 100.0) * days / 360.0
                effet.net_amount = (effet.montant or 0.0) - effet.discount_amount
            else:
                effet.discount_amount = 0.0
                effet.net_amount = effet.montant or 0.0

    def action_remettre_encaissement(self):
        for effet in self:
            effet.state = 'remis'
            effet.date_remise = fields.Date.today()

    def action_encaisser(self):
        for effet in self:
            effet.state = 'encaisse'

    def action_impayer(self):
        for effet in self:
            effet.state = 'impaye'
            current = effet.observation or ''
            note = _("Effet declare impaye le %s.") % fields.Date.today()
            effet.observation = current + ('\n' if current else '') + note

    def action_annuler(self):
        for effet in self:
            effet.state = 'annule'
