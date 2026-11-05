# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date

class TestAccountFiscalYear(TransactionCase):

    def setUp(self):
        super(TestAccountFiscalYear, self).setUp()
        self.FiscalYear = self.env['account.fiscal.year']
        self.company = self.env.company

    def test_create_fiscal_year(self):
        fy = self.FiscalYear.create({
            'name': 'FY 2026',
            'date_from': date(2026, 1, 1),
            'date_to': date(2026, 12, 31),
            'company_id': self.company.id,
        })
        self.assertEqual(fy.name, 'FY 2026')

    def test_invalid_dates(self):
        with self.assertRaises(ValidationError):
            self.FiscalYear.create({
                'name': 'FY Invalid',
                'date_from': date(2026, 12, 31),
                'date_to': date(2026, 1, 1),
                'company_id': self.company.id,
            })
