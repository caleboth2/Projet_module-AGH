# -*- coding: utf-8 -*-

from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestFiscalMaroc(common.TransactionCase):
    """Tests de base pour le module agh_fiscal_maroc"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Société Test Maroc',
        })

    def test_01_tva_declaration_creation(self):
        declaration = self.env['account.tva.declaration'].create({
            'company_id': self.company.id,
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
            'period_type': 'monthly',
            'tva_collecte_20': 10000.0,
            'tva_deductible_20': 8000.0,
        })
        self.assertEqual(declaration.state, 'draft')
        self.assertTrue(declaration.name)

    def test_02_is_declaration_creation(self):
        declaration = self.env['account.is.declaration'].create({
            'company_id': self.company.id,
            'fiscal_year': '2025',
            'accounting_result': 100000.0,
            'fiscal_reintegration': 5000.0,
            'fiscal_deduction': 3000.0,
        })
        self.assertEqual(declaration.state, 'draft')
        self.assertEqual(declaration.fiscal_result, 102000.0)

    def test_03_cotisation_minimale_creation(self):
        cm = self.env['account.cotisation.minimale'].create({
            'company_id': self.company.id,
            'fiscal_year': '2025',
            'total_revenue_ttc': 1000000.0,
            'other_products': 50000.0,
            'cm_rate': 0.5,
        })
        self.assertEqual(cm.state, 'draft')
        self.assertEqual(cm.total_base, 1050000.0)
        self.assertEqual(cm.cm_amount, 5250.0)

    def test_04_taxe_professionnelle_creation(self):
        tp = self.env['account.taxe.professionnelle'].create({
            'company_id': self.company.id,
            'fiscal_year': '2025',
            'category': 'a',
            'rental_value': 100000.0,
            'municipal_rate': 10.0,
            'regional_rate': 5.0,
        })
        self.assertEqual(tp.state, 'draft')
        self.assertEqual(tp.municipal_tp, 10000.0)
        self.assertEqual(tp.regional_tp, 5000.0)
        self.assertEqual(tp.total_tp, 15000.0)

    def test_05_fiscal_calendar_creation(self):
        calendar = self.env['account.fiscal.calendar'].create({
            'name': 'TVA Mensuelle - Janvier 2025',
            'declaration_type': 'tva_monthly',
            'fiscal_year': '2025',
            'due_date': '2025-02-28',
            'deadline': '2025-02-28',
            'period_from': '2025-01-01',
            'period_to': '2025-01-31',
            'company_id': self.company.id,
        })
        self.assertFalse(calendar.is_done)
        self.assertEqual(calendar.declaration_type, 'tva_monthly')

    def test_06_tva_calculation(self):
        declaration = self.env['account.tva.declaration'].create({
            'company_id': self.company.id,
            'date_from': '2025-01-01',
            'date_to': '2025-01-31',
            'period_type': 'monthly',
            'tva_collecte_20': 20000.0,
            'tva_collecte_14': 1400.0,
            'tva_collecte_10': 1000.0,
            'tva_collecte_7': 700.0,
            'tva_deductible_20': 15000.0,
            'tva_deductible_14': 700.0,
            'tva_deductible_10': 500.0,
            'tva_deductible_7': 350.0,
            'credit_anterieur': 0.0,
        })
        self.assertEqual(declaration.total_tva_collecte, 23100.0)
        self.assertEqual(declaration.total_tva_deductible, 16550.0)
        self.assertEqual(declaration.tva_brute, 6550.0)
        self.assertEqual(declaration.tva_nette, 6550.0)

    def test_07_is_rate(self):
        declaration = self.env['account.is.declaration'].create({
            'company_id': self.company.id,
            'fiscal_year': '2025',
            'company_type': 'normal',
            'accounting_result': 100000.0,
        })
        self.assertEqual(declaration.is_rate, 20.0)
