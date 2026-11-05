from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestRecruitmentStructure(TransactionCase):

    def setUp(self):
        super(TestRecruitmentStructure, self).setUp()
        self.template = self.env['agh.job.template'].create({
            'name': 'Test Template',
            'description': '<p>Job Description</p>',
            'requirements': '<p>Requirements</p>',
        })
        self.job = self.env['hr.job'].create({
            'name': 'Test Job',
        })
        self.stage = self.env['hr.recruitment.stage'].create({
            'name': 'Test Stage',
            'agh_stage_structure': '<p>Stage Structure</p>',
        })
        # Odoo 18 requires a candidate for each applicant
        self.candidate = self.env['hr.candidate'].create({
            'partner_name': 'Test Candidate',
        })

    def test_job_template_onchange(self):
        """Test if selecting a template on a job updates its description."""
        self.job.agh_job_template_id = self.template
        self.job._onchange_agh_job_template_id()
        self.assertIn('Job Description', self.job.description)
        self.assertIn('Requirements', self.job.description)

    def test_applicant_stage_structure(self):
        """Test if applicant shows the structure of its current stage."""
        applicant = self.env['hr.applicant'].create({
            'candidate_id': self.candidate.id,
            'job_id': self.job.id,
            'stage_id': self.stage.id,
        })
        self.assertEqual(applicant.agh_stage_structure, self.stage.agh_stage_structure)
