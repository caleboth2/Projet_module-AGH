from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestHrDocumentKyc(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employé KYC Test',
        })

        cls.document_type = cls.env['hr.document.type'].create({
            'name': 'Carte nationale',
            'code': 'CNI',
        })

        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'cni_test.pdf',
            'datas': 'VGVzdCBkb2N1bWVudA==',
            'res_model': 'hr.employee.document',
        })

    def test_document_kyc_starts_in_draft(self):
        document = self.env['hr.employee.document'].create({
            'employee_id': self.employee.id,
            'document_type_id': self.document_type.id,
            'attachment_id': self.attachment.id,
        })

        self.assertEqual(document.kyc_status, 'draft')
        self.assertFalse(document.extracted_first_name)
        self.assertFalse(document.extracted_last_name)
        self.assertFalse(document.extracted_document_number)
        self.assertEqual(document.ocr_confidence, 0.0)

    def test_document_kyc_can_be_rejected(self):
        document = self.env['hr.employee.document'].create({
            'employee_id': self.employee.id,
            'document_type_id': self.document_type.id,
            'attachment_id': self.attachment.id,
        })

        document.write({
            'kyc_status': 'rejected',
            'rejection_reason': 'Document illisible',
        })

        self.assertEqual(document.kyc_status, 'rejected')
        self.assertEqual(
            document.rejection_reason,
            'Document illisible',
        )