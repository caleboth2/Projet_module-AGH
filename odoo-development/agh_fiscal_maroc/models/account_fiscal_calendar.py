# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountFiscalCalendar(models.Model):
    _name = 'account.fiscal.calendar'
    _description = 'Calendrier fiscal Maroc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date'

    name = fields.Char(string="Désignation", required=True, tracking=True)
    declaration_type = fields.Selection(
        selection=[
            ('tva_monthly', 'TVA Mensuelle'),
            ('tva_quarterly', 'TVA Trimestrielle'),
            ('is_acompte_t1', 'IS - Acompte T1'),
            ('is_acompte_t2', 'IS - Acompte T2'),
            ('is_acompte_t3', 'IS - Acompte T3'),
            ('is_acompte_t4', 'IS - Acompte T4'),
            ('is_annual', 'IS Annuel'),
            ('cm_annual', 'Cotisation Minimale'),
            ('tp_annual', 'Taxe Professionnelle'),
            ('other', 'Autre'),
        ],
        string="Type de déclaration",
        required=True,
    )
    fiscal_year = fields.Char(string="Exercice fiscal", required=True)

    period_from = fields.Date(string="Période début")
    period_to = fields.Date(string="Période fin")
    due_date = fields.Date(string="Date limite", required=True, tracking=True)
    deadline = fields.Date(string="Date butoir")

    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        'res.users',
        string="Responsable",
        default=lambda self: self.env.user,
    )

    days_before_notify = fields.Integer(string="Jours avant notification", default=15)
    days_remaining = fields.Integer(
        string="Jours restants",
        compute='_compute_days_remaining',
    )

    is_done = fields.Boolean(string="Effectuée", default=False, tracking=True)
    notification_sent = fields.Boolean(string="Notification envoyée", default=False)
    declaration_id = fields.Reference(
        selection=[
            ('account.tva.declaration', 'Déclaration TVA'),
            ('account.is.declaration', 'Déclaration IS'),
            ('account.cotisation.minimale', 'Cotisation Minimale'),
            ('account.taxe.professionnelle', 'Taxe Professionnelle'),
        ],
        string="Déclaration liée",
    )

    notes = fields.Text(string="Notes")
    state = fields.Selection(
        selection=[
            ('upcoming', 'À venir'),
            ('soon', 'Bientôt'),
            ('overdue', 'En retard'),
            ('done', 'Terminée'),
        ],
        string="Statut",
        compute='_compute_state',
    )

    @api.depends('due_date')
    def _compute_days_remaining(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.due_date:
                record.days_remaining = (record.due_date - today).days
            else:
                record.days_remaining = 0

    @api.depends('due_date', 'is_done', 'days_before_notify')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.is_done:
                record.state = 'done'
            elif record.due_date:
                delta = (record.due_date - today).days
                if delta < 0:
                    record.state = 'overdue'
                elif delta <= (record.days_before_notify or 15):
                    record.state = 'soon'
                else:
                    record.state = 'upcoming'
            else:
                record.state = 'upcoming'

    def action_mark_done(self):
        for record in self:
            record.is_done = True

    def action_mark_undone(self):
        for record in self:
            record.is_done = False

    @api.model
    def _cron_notify_upcoming_deadlines(self):
        """Tâche planifiée : envoyer une notification pour les échéances proches."""
        today = fields.Date.context_today(self)
        records = self.search([
            ('is_done', '=', False),
            ('notification_sent', '=', False),
            ('due_date', '!=', False),
        ])
        for record in records:
            delta = (record.due_date - today).days
            threshold = record.days_before_notify or 15
            if 0 <= delta <= threshold and record.user_id:
                record.message_post(
                    body=_(
                        "Échéance fiscale proche : %(name)s — %(days)s jour(s) restant(s).",
                        name=record.name,
                        days=delta,
                    ),
                    partner_ids=record.user_id.partner_id.ids,
                )
                record.notification_sent = True
        return True
