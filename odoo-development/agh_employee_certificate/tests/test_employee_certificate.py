# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestAghEmployeeCertificate(TransactionCase):

    def setUp(self):
        super(TestAghEmployeeCertificate, self).setUp()
        self.Employee = self.env['hr.employee']
        self.Certificate = self.env['hr.certificate']
        self.employee = self.Employee.create({'name': 'Test Employee Certificate'})

    def test_certificate_creation(self):
        cert = self.Certificate.create({
            'employee_id': self.employee.id,
            'certificate_type': 'ATT_TRAVAIL',
        })
        self.assertEqual(cert.state, 'requested')
        cert.action_validate()
        self.assertEqual(cert.state, 'validated')
