# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AghCrashReport(models.Model):
    _name = 'agh.crash.report'
    _description = 'Rapport de Crash App'
    _order = 'create_date desc'

    name = fields.Char(string='Titre du crash', required=True)
    app_name = fields.Char(string='Nom de l\'app', required=True)
    package_name = fields.Char(string='Package Name')
    exception_type = fields.Char(string='Exception Type (ex: NullPointerException)')
    stack_trace = fields.Text(string='Stack Trace')
    occurrence_count = fields.Integer(string='Nombre de d\'occurrences', default=1)
    severity = fields.Selection([
        ('low', 'Faible'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('critical', '🔴 CRITIQUE'),
    ], string='Sévérité', default='high', required=True)
    state = fields.Selection([
        ('new', 'Nouveau'),
        ('in_progress', 'En cours de correction'),
        ('resolved', 'Résolu'),
        ('ignored', 'Ignoré'),
    ], string='Statut', default='new', required=True)
    task_id = fields.Many2one('project.task', string='Tâche / Ticket projet rattaché')

    def action_create_project_task(self):
        """Crée automatiquement un ticket/tâche Odoo pour le suivi du crash."""
        Task = self.env['project.task']
        for report in self:
            if not report.task_id:
                # Trouver un projet par défaut
                project = self.env['project.project'].search([], limit=1)
                task_vals = {
                    'name': _("BUG CRASH: %s (%s)") % (report.name, report.severity.upper()),
                    'description': _("Crash remonté le %s:\n\nException: %s\n\nStack Trace:\n%s") % (
                        fields.Datetime.now(), report.exception_type or '', report.stack_trace or ''
                    ),
                    'priority': '1' if report.severity in ('high', 'critical') else '0',
                }
                if project:
                    task_vals['project_id'] = project.id
                task = Task.create(task_vals)
                report.write({'task_id': task.id, 'state': 'in_progress'})
        return True
