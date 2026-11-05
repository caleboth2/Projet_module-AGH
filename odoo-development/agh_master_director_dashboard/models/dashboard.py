from odoo import fields, models


class AghDirectorDashboard(models.Model):
    _name = "agh.director.dashboard"
    _description = "AGH Director Dashboard"

    name = fields.Char(
        string="Name",
        default="Master Director Dashboard",
        required=True,
    )
    total_hours = fields.Float(
        string="Total Hours",
        compute="_compute_dashboard",
    )

    development_cost_dh = fields.Float(
        string="Development Cost (DH)",
        compute="_compute_dashboard",
    )
    
    active_projects = fields.Integer(
        string="Active Projects",
        compute="_compute_dashboard",
    )
    
    total_tasks = fields.Integer(
        string="Total Tasks",
        compute="_compute_dashboard",
    )
    
    completed_tasks = fields.Integer(
        string="Completed Tasks",
        compute="_compute_dashboard",
    )
    
    open_tasks = fields.Integer(
        string="Open Tasks",
        compute="_compute_dashboard",
    )
    
    velocity_rate = fields.Float(
        string="Velocity (%)",
        compute="_compute_dashboard",
    )

    def _compute_dashboard(self):

        for rec in self:
    
            rec.total_hours = sum(
                self.env['account.analytic.line'].search([]).mapped('unit_amount')
            )
    
            rec.development_cost_dh = rec.total_hours * 200
    
            rec.active_projects = self.env[
                'project.project'
            ].search_count([
                ('active', '=', True)
            ])
    
            rec.total_tasks = self.env[
                'project.task'
            ].search_count([])
    
            rec.completed_tasks = self.env[
                'project.task'
            ].search_count([
                ('stage_id.name', '=', 'Done')
            ])
    
            rec.open_tasks = (
                rec.total_tasks - rec.completed_tasks
            )
    
            rec.velocity_rate = (
                (rec.completed_tasks / rec.total_tasks) * 100
                if rec.total_tasks else 0.0
            )