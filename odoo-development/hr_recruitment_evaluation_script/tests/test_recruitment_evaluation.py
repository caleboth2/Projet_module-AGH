from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRecruitmentEvaluation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.job = cls.env['hr.job'].create({
            'name': 'Poste de test',
        })

        cls.candidate = cls.env['hr.candidate'].create({
            'partner_name': 'Candidat Test',
        })

        cls.criteria = cls.env['hr.evaluation.criteria'].create([
            {
                'name': 'Formation',
                'max_score': 4.0,
                'sequence': 10,
            },
            {
                'name': 'Expérience',
                'max_score': 4.0,
                'sequence': 20,
            },
            {
                'name': 'Communication',
                'max_score': 4.0,
                'sequence': 30,
            },
            {
                'name': 'Motivation',
                'max_score': 4.0,
                'sequence': 40,
            },
            {
                'name': 'Disponibilité',
                'max_score': 4.0,
                'sequence': 50,
            },
        ])

    def _create_applicant(self):
        return self.env['hr.applicant'].create({
            'candidate_id': self.candidate.id,
            'job_id': self.job.id,
        })

    def test_score_20_and_passed_recommendation(self):
        applicant = self._create_applicant()

        self.env['hr.applicant.evaluation.line'].create([
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[0].id,
                'is_passed': True,
            },
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[1].id,
                'is_passed': True,
            },
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[2].id,
                'is_passed': True,
            },
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[3].id,
                'is_passed': True,
            },
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[4].id,
                'is_passed': True,
            },
        ])

        self.assertEqual(applicant.evaluation_score, 20.0)
        self.assertEqual(applicant.evaluation_max_score, 20.0)
        self.assertEqual(applicant.evaluation_score_20, 20.0)
        self.assertEqual(applicant.evaluation_recommendation, 'passed')

    def test_partial_score_and_rejected_recommendation(self):
        applicant = self._create_applicant()

        self.env['hr.applicant.evaluation.line'].create([
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[0].id,
                'is_passed': True,
            },
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[1].id,
                'is_passed': False,
            },
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[2].id,
                'is_passed': False,
            },
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[3].id,
                'is_passed': False,
            },
            {
                'applicant_id': applicant.id,
                'criteria_id': self.criteria[4].id,
                'is_passed': False,
            },
        ])

        self.assertEqual(applicant.evaluation_score, 4.0)
        self.assertEqual(applicant.evaluation_max_score, 20.0)
        self.assertEqual(applicant.evaluation_score_20, 4.0)
        self.assertEqual(applicant.evaluation_recommendation, 'rejected')

    def test_empty_evaluation_is_pending(self):
        applicant = self._create_applicant()

        self.assertEqual(applicant.evaluation_score, 0.0)
        self.assertEqual(applicant.evaluation_score_20, 0.0)
        self.assertEqual(applicant.evaluation_recommendation, 'pending')