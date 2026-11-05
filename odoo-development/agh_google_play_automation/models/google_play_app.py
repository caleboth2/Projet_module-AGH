# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AghGooglePlayApp(models.Model):
    _name = 'agh.google.play.app'
    _description = 'Google Play Application'
    _inherit = ['mail.thread']
    _order = 'name asc'

    name = fields.Char(string='Nom de l\'application', required=True)
    package_name = fields.Char(string='Package Name (ex: com.agh.mobile)', required=True)
    service_account_json = fields.Text(string='Clé Service Account JSON')
    active = fields.Boolean(default=True)
    track_ids = fields.One2many('agh.google.play.track', 'app_id', string='Tracks & Releases')
    track_count = fields.Integer(string='Nombre de Releases', compute='_compute_track_count')

    @api.depends('track_ids')
    def _compute_track_count(self):
        for record in self:
            record.track_count = len(record.track_ids)

    def action_sync_google_play(self):
        """Simule la synchronisation des APKs et status depuis l'API Google Play Developer."""
        for app in self:
            app.message_post(body=_("Synchronisation API Google Play exécutée avec succès pour %s.") % app.package_name)
        return True
