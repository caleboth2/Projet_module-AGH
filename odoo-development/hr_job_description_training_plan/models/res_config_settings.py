from odoo import models, fields

from .hr_job import DEFAULT_INTERNSHIP_DURATION, DEFAULT_WORK_SCHEDULE

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    job_default_internship_duration = fields.Char(
        string="Durée de stage par défaut",
        config_parameter='hr_job_description_training_plan.default_internship_duration',
        default=DEFAULT_INTERNSHIP_DURATION,
    )

    job_default_work_schedule = fields.Char(
        string="Horaires par défaut",
        config_parameter='hr_job_description_training_plan.default_work_schedule',
        default=DEFAULT_WORK_SCHEDULE,
    )