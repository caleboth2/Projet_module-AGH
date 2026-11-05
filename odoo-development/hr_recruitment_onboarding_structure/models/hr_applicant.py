from odoo import models, fields

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    agh_stage_structure = fields.Html(related='stage_id.agh_stage_structure', string="Trame de l'étape", readonly=True)
