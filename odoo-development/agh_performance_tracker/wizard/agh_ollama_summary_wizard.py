# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AghOllamaSummaryWizard(models.TransientModel):
    _name = 'agh.ollama.summary.wizard'
    _description = 'Wizard – Résumé IA Ollama'

    evaluation_id = fields.Many2one(
        'agh.kpi.evaluation',
        string='Évaluation',
        required=True,
        readonly=True,
    )
    employee_name = fields.Char(
        related='evaluation_id.employee_id.name',
        string='Collaborateur',
        readonly=True,
    )
    score_summary = fields.Char(
        string='Score',
        compute='_compute_score_summary',
    )
    ollama_url = fields.Char(
        string='URL Ollama',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'agh_performance.ollama_url', 'http://localhost:11434'
        ),
    )
    ollama_model = fields.Char(
        string='Modèle',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'agh_performance.ollama_model', 'llama3'
        ),
    )
    preview_prompt = fields.Text(
        string='Aperçu du prompt',
        compute='_compute_preview_prompt',
    )

    @api.depends('evaluation_id')
    def _compute_score_summary(self):
        for rec in self:
            ev = rec.evaluation_id
            if ev:
                rec.score_summary = f"{ev.score_total}/20 ({ev.score_total_percent:.1f}%)"
            else:
                rec.score_summary = ''

    @api.depends('evaluation_id')
    def _compute_preview_prompt(self):
        for rec in self:
            if rec.evaluation_id:
                rec.preview_prompt = rec.evaluation_id._build_ollama_prompt()
            else:
                rec.preview_prompt = ''

    def action_generate(self):
        self.ensure_one()
        config = self.env['ir.config_parameter'].sudo()
        config.set_param('agh_performance.ollama_url', self.ollama_url)
        config.set_param('agh_performance.ollama_model', self.ollama_model)
        return self.evaluation_id.action_generate_ollama_summary()
