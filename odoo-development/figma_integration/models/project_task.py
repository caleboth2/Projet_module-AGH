from odoo import models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'

    figma_design_ids = fields.One2many(
        'agh.figma.design',
        'task_id',
        string="Figma Designs"
    )

    figma_design_count = fields.Integer(
        compute='_compute_figma_count'
    )

    def _compute_figma_count(self):

        for rec in self:
            rec.figma_design_count = len(rec.figma_design_ids)

    def action_open_figma_designs(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Figma Designs',
            'res_model': 'agh.figma.design',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
        }