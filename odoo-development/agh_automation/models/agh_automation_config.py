from datetime import datetime, time
from odoo import api, fields, models


class AghAutomationConfig(models.TransientModel):
    """Modele transient pour le tableau de bord d'automatisation.

    Ce modele agrege en lecture seule des indicateurs globaux
    (succes, erreurs, alertes actives, taches planifiees) et
    expose les dernieres executions du journal.
    """

    _name = 'agh.automation.config'
    _description = "Tableau de bord Automatisation"

    success_count_today = fields.Integer(
        string="Succes aujourd'hui",
        compute='_compute_dashboard_stats',
    )
    error_count_today = fields.Integer(
        string="Erreurs aujourd'hui",
        compute='_compute_dashboard_stats',
    )
    active_alerts_count = fields.Integer(
        string="Alertes actives",
        compute='_compute_dashboard_stats',
    )
    scheduled_jobs_count = fields.Integer(
        string="Taches planifiees",
        compute='_compute_dashboard_stats',
    )
    recent_log_ids = fields.Many2many(
        'agh.workflow.log',
        string="Dernieres executions",
        compute='_compute_dashboard_stats',
    )

    @api.depends_context('uid')
    def _compute_dashboard_stats(self):
        Log = self.env['agh.workflow.log'].sudo()
        Alert = self.env['agh.alert.rule'].sudo()
        Cron = self.env['ir.cron'].sudo()
        today_start = datetime.combine(fields.Date.today(), time.min)
        for rec in self:
            rec.success_count_today = Log.search_count([
                ('execution_date', '>=', today_start),
                ('status', '=', 'success'),
            ])
            rec.error_count_today = Log.search_count([
                ('execution_date', '>=', today_start),
                ('status', 'in', ('failed', 'warning')),
            ])
            rec.active_alerts_count = Alert.search_count([
                ('active', '=', True),
            ])
            rec.scheduled_jobs_count = Cron.search_count([
                ('active', '=', True),
            ])
            rec.recent_log_ids = Log.search([], limit=10)

    @api.model
    def action_open_dashboard(self):
        """Ouvre le tableau de bord en creant un enregistrement transient."""
        record = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': "Tableau de bord Automatisation",
            'res_model': 'agh.automation.config',
            'view_mode': 'form',
            'res_id': record.id,
            'target': 'current',
        }
