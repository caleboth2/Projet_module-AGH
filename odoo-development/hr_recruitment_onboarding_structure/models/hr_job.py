from odoo import models, fields, api

class HrJob(models.Model):
    _inherit = 'hr.job'

    agh_job_template_id = fields.Many2one('agh.job.template', string="Modèle d'annonce")

    @api.onchange('agh_job_template_id')
    def _onchange_agh_job_template_id(self):
        if self.agh_job_template_id:
            description = self.agh_job_template_id.description or ""
            if self.agh_job_template_id.requirements:
                description += "<h3>Prérequis</h3>" + self.agh_job_template_id.requirements
            self.description = description
