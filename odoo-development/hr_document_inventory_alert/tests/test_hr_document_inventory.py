from odoo.tests.common import TransactionCase


class TestHrDocumentInventory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.document_type_cin = cls.env['hr.document.type'].create({
            'name': 'Carte d’identité',
            'code': 'CIN',
        })

        cls.document_type_rib = cls.env['hr.document.type'].create({
            'name': 'RIB',
            'code': 'RIB',
        })

        cls.contract_type = cls.env['hr.contract.type'].create({
            'name': 'CDI Test',
            'required_document_type_ids': [
                (6, 0, [
                    cls.document_type_cin.id,
                    cls.document_type_rib.id,
                ]),
            ],
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employé Test',
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': 'Contrat Test',
            'employee_id': cls.employee.id,
            'contract_type_id': cls.contract_type.id,
            'wage': 3000,
        })

    def test_01_no_document(self):
        self.employee._compute_document_completeness()

        self.assertEqual(self.employee.completeness_rate, 0.0)
        self.assertTrue(self.employee.is_dossier_incomplete)

    def test_02_one_document_of_two(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'cin.pdf',
            'datas': 'VGVzdCBmaWNoaWVy',
        })

        self.env['hr.employee.document'].create({
            'employee_id': self.employee.id,
            'document_type_id': self.document_type_cin.id,
            'attachment_id': attachment.id,
        })

        self.employee._compute_document_completeness()

        self.assertEqual(self.employee.completeness_rate, 50.0)
        self.assertTrue(self.employee.is_dossier_incomplete)

    def test_03_all_documents(self):
        attachment_cin = self.env['ir.attachment'].create({
            'name': 'cin.pdf',
            'datas': 'VGVzdCBDSU4=',
        })

        attachment_rib = self.env['ir.attachment'].create({
            'name': 'rib.pdf',
            'datas': 'VGVzdCBSU0I=',
        })

        self.env['hr.employee.document'].create([
            {
                'employee_id': self.employee.id,
                'document_type_id': self.document_type_cin.id,
                'attachment_id': attachment_cin.id,
            },
            {
                'employee_id': self.employee.id,
                'document_type_id': self.document_type_rib.id,
                'attachment_id': attachment_rib.id,
            },
        ])

        self.employee._compute_document_completeness()

        self.assertEqual(self.employee.completeness_rate, 100.0)
        self.assertFalse(self.employee.is_dossier_incomplete)