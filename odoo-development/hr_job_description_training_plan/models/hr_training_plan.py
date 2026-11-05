from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrJobTrainingLine(models.Model):
    _name = 'hr.job.training.line'
    _description = 'Ligne du Plan de Formation'

    job_id = fields.Many2one('hr.job', string='Poste de travail', required=True, ondelete='cascade')
    name = fields.Char(string='Formation / Compétence', required=True)

    # POINT #4 : Ajout d'une catégorie pour éviter que ce soit trop générique
    category = fields.Selection([
        ('skill', 'Compétence Technique'),
        ('soft_skill', 'Savoir-être (Soft Skill)'),
        ('certification', 'Certification'),
        ('tool', 'Outil / Logiciel'),
        ('other', 'Autre')
    ], string='Catégorie', default='skill', required=True)

    description = fields.Text(string='Description / Objectifs')
    duration_hours = fields.Integer(string='Durée (Heures)')
    is_mandatory = fields.Boolean(string='Obligatoire', default=True)

    # POINT #3 : Validation (Vérifier que la durée est supérieure à 0)
    @api.constrains('duration_hours')
    def _check_duration_hours(self):
        for record in self:
            if record.duration_hours <= 0:
                raise ValidationError("La durée de la formation doit être supérieure à 0.")