from odoo import models, fields, api
from odoo.exceptions import ValidationError

DEFAULT_INTERNSHIP_DURATION = '1 à 3 mois'
DEFAULT_WORK_SCHEDULE = 'Lun - Sam : 10h-13h / 14h-18h'

class HrJob(models.Model):
    _inherit = 'hr.job'

    is_internship = fields.Boolean(string='Est un poste de stage', default=False)

    # Méthodes pour récupérer les valeurs par défaut depuis la configuration (Point #2)
    def _default_internship_duration(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'hr_job_description_training_plan.default_internship_duration',
            DEFAULT_INTERNSHIP_DURATION,
        )

    def _default_work_schedule(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'hr_job_description_training_plan.default_work_schedule',
            DEFAULT_WORK_SCHEDULE,
        )

    internship_duration = fields.Char(string='Durée du stage', default=_default_internship_duration)
    work_schedule = fields.Char(string='Horaires', default=_default_work_schedule)

    remuneration_status = fields.Selection([
        ('unpaid', 'Non rémunéré'),
        ('paid', 'Rémunéré'),
    ], string='Rémunération', default='unpaid')

    training_plan_ids = fields.One2many(
        'hr.job.training.line', 
        'job_id', 
        string='Plan de formation'
    )

    # POINT #3 : Validation (Si c'est un stage, la durée doit être remplie)
    @api.constrains('is_internship', 'internship_duration')
    def _check_internship_duration(self):
        for record in self:
            if record.is_internship and not record.internship_duration:
                raise ValidationError("Si le poste est défini comme un stage, vous devez obligatoirement préciser la 'Durée du stage'.")