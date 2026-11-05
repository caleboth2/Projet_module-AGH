# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ollama_url = fields.Char(
        string='URL Ollama',
        config_parameter='agh_performance.ollama_url',
        default='http://localhost:11434',
        help="URL de base du service Ollama local (ex: http://localhost:11434).",
    )
    ollama_model = fields.Char(
        string='Modèle Ollama',
        config_parameter='agh_performance.ollama_model',
        default='llama3',
        help="Nom du modèle Ollama à utiliser (ex: llama3, mistral, phi3).",
    )
    ollama_timeout = fields.Integer(
        string='Timeout Ollama (s)',
        config_parameter='agh_performance.ollama_timeout',
        default=60,
        help="Délai maximum d'attente pour la réponse Ollama (en secondes).",
    )
