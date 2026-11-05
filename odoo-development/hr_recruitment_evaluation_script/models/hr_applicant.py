from odoo import api, fields, models


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    evaluation_line_ids = fields.One2many(
        comodel_name='hr.applicant.evaluation.line',
        inverse_name='applicant_id',
        string='Grille d’évaluation',
    )

    evaluation_score = fields.Float(
        string='Score obtenu',
        compute='_compute_evaluation_score',
        store=True,
    )

    evaluation_max_score = fields.Float(
        string='Score maximum',
        compute='_compute_evaluation_score',
        store=True,
    )

    evaluation_score_20 = fields.Float(
        string='Score sur 20',
        compute='_compute_evaluation_score',
        store=True,
    )

    evaluation_recommendation = fields.Selection(
        selection=[
            ('pending', 'À évaluer'),
            ('passed', 'Passé'),
            ('rejected', 'Rejeté'),
        ],
        string='Recommandation',
        compute='_compute_evaluation_recommendation',
        store=True,
    )

    evaluation_comment = fields.Text(
        string='Commentaire général',
    )

    @api.depends(
        'evaluation_line_ids.score',
        'evaluation_line_ids.criteria_id.max_score',
    )
    def _compute_evaluation_score(self):
        for applicant in self:
            lines = applicant.evaluation_line_ids
            applicant.evaluation_score = sum(lines.mapped('score'))
            applicant.evaluation_max_score = sum(
                lines.mapped('criteria_id.max_score')
            )

            if applicant.evaluation_max_score:
                applicant.evaluation_score_20 = (
                    applicant.evaluation_score
                    / applicant.evaluation_max_score
                    * 20
                )
            else:
                applicant.evaluation_score_20 = 0.0

    @api.depends(
        'evaluation_line_ids',
        'evaluation_line_ids.is_passed',
        'evaluation_score_20',
    )
    def _compute_evaluation_recommendation(self):
        for applicant in self:
            if not applicant.evaluation_line_ids:
                applicant.evaluation_recommendation = 'pending'
            elif applicant.evaluation_score_20 >= 10:
                applicant.evaluation_recommendation = 'passed'
            else:
                applicant.evaluation_recommendation = 'rejected'