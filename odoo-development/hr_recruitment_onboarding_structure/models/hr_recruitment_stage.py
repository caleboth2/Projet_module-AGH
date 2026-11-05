from odoo import models, fields

class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    agh_stage_structure = fields.Html(string="Trame d'entretien / Onboarding", help="Structure ou questions types pour cette étape.")
