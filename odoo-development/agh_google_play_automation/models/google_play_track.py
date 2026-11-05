# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AghGooglePlayTrack(models.Model):
    _name = 'agh.google.play.track'
    _description = 'Google Play Release Track'
    _order = 'version_code desc'

    app_id = fields.Many2one('agh.google.play.app', string='Application', required=True, ondelete='cascade')
    version_code = fields.Integer(string='Version Code', required=True)
    version_name = fields.Char(string='Version Name (ex: 1.0.4)', required=True)
    track_name = fields.Selection([
        ('draft', 'Brouillon'),
        ('internal', 'Internal Test'),
        ('alpha', 'Alpha Track'),
        ('beta', 'Beta Track'),
        ('production', 'Production'),
    ], string='Track Release', default='internal', required=True)
    status = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('in_review', 'En cours de validation'),
        ('approved', 'Approuvé / Publié'),
        ('rejected', 'Rejeté par Google'),
        ('halted', 'Interrompu / Bloqué'),
    ], string='Statut APK', default='draft', required=True)
    release_notes = fields.Text(string='Notes de version')
    active = fields.Boolean(default=True)
