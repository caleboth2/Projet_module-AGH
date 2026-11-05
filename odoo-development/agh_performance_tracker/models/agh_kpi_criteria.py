# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AghKpiCriteria(models.Model):
    """Référentiel des critères KPI (extensible par l'admin)."""
    _name = 'agh.kpi.criteria'
    _description = 'Critère KPI de Performance'
    _order = 'sequence, name'

    name = fields.Char(string='Critère', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Ordre', default=10)
    description = fields.Text(string='Description', translate=True)
    team_category = fields.Selection(
        selection=[
            ('all', 'Tous'),
            ('rh', 'RH'),
            ('mk', 'Marketing'),
            ('qa', 'QA'),
            ('dev', 'DEV'),
            ('other', 'Autre'),
        ],
        string='Équipe concernée',
        default='all',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Le code de critère doit être unique.'),
    ]


class AghPerformanceSummary(models.Model):
    """Vue agrégée des performances par département / période."""
    _name = 'agh.performance.summary'
    _description = 'Synthèse de Performance'
    _auto = False
    _order = 'avg_score desc'

    employee_id = fields.Many2one('hr.employee', string='Collaborateur', readonly=True)
    department_id = fields.Many2one('hr.department', string='Département', readonly=True)
    team_category = fields.Char(string='Équipe', readonly=True)
    evaluation_count = fields.Integer(string="Nb d'évaluations", readonly=True)
    avg_score = fields.Float(string='Score moyen', readonly=True, digits=(5, 2))
    avg_percent = fields.Float(string='Score moyen (%)', readonly=True, digits=(5, 1))
    last_evaluation = fields.Date(string='Dernière évaluation', readonly=True)

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS agh_performance_summary;
            CREATE VIEW agh_performance_summary AS (
                SELECT
                    ROW_NUMBER() OVER ()            AS id,
                    e.id                            AS employee_id,
                    e.department_id                 AS department_id,
                    k.team_category                 AS team_category,
                    COUNT(k.id)                     AS evaluation_count,
                    AVG(k.score_total)              AS avg_score,
                    AVG(k.score_total_percent)      AS avg_percent,
                    MAX(k.date_evaluation)          AS last_evaluation
                FROM agh_kpi_evaluation k
                JOIN hr_employee e ON e.id = k.employee_id
                WHERE k.state IN ('done', 'validated')
                GROUP BY e.id, e.department_id, k.team_category
            )
        """)
