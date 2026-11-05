from odoo.tests.common import TransactionCase  # pyright: ignore[reportMissingImports]
from odoo.exceptions import ValidationError

class TestHrJobTrainingPlan(TransactionCase):

    def setUp(self):
        super(TestHrJobTrainingPlan, self).setUp()
        # On prépare un poste de stage de base pour nos tests
        self.job_vals = {
            'name': 'Stage Test Développeur',
            'is_internship': True,
            'internship_duration': '2 mois',
        }

    def test_create_internship_job(self):
        """Vérifie qu'on peut créer un poste de stage avec succès"""
        job = self.env['hr.job'].create(self.job_vals)
        self.assertTrue(job.is_internship)
        self.assertEqual(job.internship_duration, '2 mois')

    def test_training_line_duration_constraint(self):
        """Vérifie que la durée de formation doit être strictement positive."""
        job = self.env['hr.job'].create(self.job_vals)

        for duration in (0, -5):
            with self.assertRaises(ValidationError):
                self.env['hr.job.training.line'].create({
                    'job_id': job.id,
                    'name': 'Formation Test',
                    'duration_hours': duration,
                })

    def test_internship_requires_duration(self):
        with self.assertRaises(ValidationError):
            self.env['hr.job'].create({
                'name': 'Stage sans durée',
                'is_internship': True,
                'internship_duration': False,
            })

    def test_training_line_requires_job(self):
        with self.assertRaises(ValidationError):
            self.env['hr.job.training.line'].create({
                'name': 'Formation sans poste',
                'duration_hours': 2,
            })

    def test_training_line_category(self):
        job = self.env['hr.job'].create(self.job_vals)
        line = self.env['hr.job.training.line'].create({
            'job_id': job.id,
            'name': 'Python',
            'category': 'skill',
            'duration_hours': 2,
        })
        self.assertEqual(line.category, 'skill')