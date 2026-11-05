from odoo import api, fields, models


class HrEvaluationCriteria(models.Model):
    _name = 'hr.evaluation.criteria'
    _description = 'Critère d’évaluation candidat'
    _order = 'sequence, id'

    name = fields.Char(
        string='Nom du critère',
        required=True,
    )

    description = fields.Text(
        string='Description',
    )

    max_score = fields.Float(
        string='Points maximum',
        default=4.0,
        required=True,
    )

    sequence = fields.Integer(
        string='Ordre',
        default=10,
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
    )


class HrApplicantEvaluationLine(models.Model):
    _name = 'hr.applicant.evaluation.line'
    _description = 'Ligne d’évaluation d’une candidature'
    _order = 'sequence, id'

    applicant_id = fields.Many2one(
        comodel_name='hr.applicant',
        string='Candidature',
        required=True,
        ondelete='cascade',
    )

    criteria_id = fields.Many2one(
        comodel_name='hr.evaluation.criteria',
        string='Critère',
        required=True,
        ondelete='restrict',
    )

    sequence = fields.Integer(
        string='Ordre',
        related='criteria_id.sequence',
        store=True,
    )

    is_passed = fields.Boolean(
        string='Validé',
    )

    score = fields.Float(
        string='Score obtenu',
        compute='_compute_score',
        store=True,
    )

    comment = fields.Text(
        string='Commentaire',
    )

    @api.depends('is_passed', 'criteria_id.max_score')
    def _compute_score(self):
        for line in self:
            line.score = line.criteria_id.max_score if line.is_passed else 0.0