# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AghHealthScoreDashboard(models.Model):
    _name = 'agh.health.score.dashboard'
    _description = 'Tableau de Bord Santé Financière & Opérationnelle'
    _order = 'date desc'

    name = fields.Char(string='Titre de l\'évaluation', required=True, default=lambda self: _("Santé Macro %s") % fields.Date.today())
    date = fields.Date(string='Date d\'évaluation', default=fields.Date.context_today, required=True)
    
    # Financial metrics
    dev_cost = fields.Float(string='Coût de Développement Cumulé (€/MAD)', default=125000.0)
    
    # Technical velocity
    completed_tasks_count = fields.Integer(string='Tâches Terminées (Sprint)', compute='_compute_velocity_metrics', store=True)
    velocity_score = fields.Float(string='Score de Vélocité (%)', compute='_compute_velocity_metrics', store=True)
    
    # Quality & Stability
    critical_crashes_count = fields.Integer(string='Crashs Critiques Ouverts', compute='_compute_quality_metrics')
    apk_release_status = fields.Char(string='Statut Release APK', compute='_compute_quality_metrics')
    
    # Global score
    health_score = fields.Float(string='Score Macro Global / 100', compute='_compute_health_score', store=True)
    health_status = fields.Selection([
        ('excellent', '💚 EXCELLENT (90-100)'),
        ('good', '💙 BON (75-89)'),
        ('warning', '💛 ATTENTION (50-74)'),
        ('critical', '🔴 CRITIQUE (<50)'),
    ], string='État de Santé', compute='_compute_health_score', store=True)

    # Agents IA feedback
    qa_agent_feedback = fields.Text(string='Analyse Agent IA QA')
    pm_agent_feedback = fields.Text(string='Analyse Agent IA PM')
    secops_agent_feedback = fields.Text(string='Analyse Agent IA SecOps')

    @api.depends('date')
    def _compute_velocity_metrics(self):
        for record in self:
            tasks = self.env['project.task'].search([('stage_id.fold', '=', True)])
            record.completed_tasks_count = len(tasks)
            record.velocity_score = min(100.0, 75.0 + len(tasks) * 2.5)

    @api.depends('date')
    def _compute_quality_metrics(self):
        for record in self:
            critical_crashes = self.env['agh.crash.report'].search_count([('severity', '=', 'critical'), ('state', '!=', 'resolved')])
            record.critical_crashes_count = critical_crashes
            
            latest_track = self.env['agh.google.play.track'].search([], order='version_code desc', limit=1)
            if latest_track:
                record.apk_release_status = f"v{latest_track.version_name} ({latest_track.track_name.upper()} - {latest_track.status})"
            else:
                record.apk_release_status = "Aucune release enregistrée"

    @api.depends('velocity_score', 'critical_crashes_count')
    def _compute_health_score(self):
        for record in self:
            base_score = record.velocity_score
            penalty = record.critical_crashes_count * 15.0
            final_score = max(0.0, min(100.0, base_score - penalty))
            record.health_score = final_score

            if final_score >= 90:
                record.health_status = 'excellent'
            elif final_score >= 75:
                record.health_status = 'good'
            elif final_score >= 50:
                record.health_status = 'warning'
            else:
                record.health_status = 'critical'

    def action_run_ai_agents_orchestration(self):
        """Lance l'orchestration des agents IA locaux (Ollama) pour QA, PM et SecOps."""
        for record in self:
            record.env['agh.ai.agent.orchestrator'].run_agent_pipeline(record)
        return True
