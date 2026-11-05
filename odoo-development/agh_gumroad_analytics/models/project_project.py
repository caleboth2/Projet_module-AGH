from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    gumroad_product_ids = fields.One2many('agh.gumroad.product', 'project_id',
                                          string='Gumroad Products')
    gumroad_revenue = fields.Float('Gumroad Revenue', compute='_compute_gumroad_kpis')
    gumroad_sales_count = fields.Integer('Gumroad Sales', compute='_compute_gumroad_kpis')
    gumroad_dev_cost = fields.Float('Estimated Dev Cost', compute='_compute_gumroad_kpis',
                                    help="Coût estimé via timesheets (heures * taux)")
    gumroad_roi = fields.Float('ROI (%)', compute='_compute_gumroad_kpis')
    gumroad_hourly_rate = fields.Float('Hourly Rate (cost)', default=50.0)

    @api.depends('gumroad_product_ids.sale_ids',
                 'timesheet_ids.unit_amount', 'gumroad_hourly_rate')
    def _compute_gumroad_kpis(self):
        for project in self:
            sales = project.gumroad_product_ids.mapped('sale_ids').filtered(lambda s: not s.refunded)
            revenue = sum(sales.mapped('total_price'))
            qty = sum(sales.mapped('quantity'))
            hours = sum(project.timesheet_ids.mapped('unit_amount')) if 'timesheet_ids' in project._fields else 0.0
            cost = hours * (project.gumroad_hourly_rate or 0.0)
            project.gumroad_revenue = revenue
            project.gumroad_sales_count = qty
            project.gumroad_dev_cost = cost
            project.gumroad_roi = ((revenue - cost) / cost * 100.0) if cost else 0.0
