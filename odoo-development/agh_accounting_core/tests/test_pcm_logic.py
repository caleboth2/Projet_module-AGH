# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestAghAccountingCore(TransactionCase):

    def setUp(self):
        super(TestAghAccountingCore, self).setUp()
        self.Journal = self.env['account.journal']
        self.Account = self.env['account.account']

    def test_pcm_journals_exist(self):
        """Vérifie que les journaux PCM de base ont été créés lors de l'installation."""
        sale_journal = self.Journal.search([('code', '=', 'VTE')], limit=1)
        self.assertTrue(sale_journal, "Le journal des ventes (VTE) devrait exister.")
        
        purchase_journal = self.Journal.search([('code', '=', 'ACH')], limit=1)
        self.assertTrue(purchase_journal, "Le journal des achats (ACH) devrait exister.")

    def test_account_pcm_logic(self):
        """Vérifie que la logique de classification PCM fonctionne sur les comptes."""
        # Création d'un compte d'immobilisation (Classe 2)
        immob_account = self.Account.create({
            'code': '2111',
            'name': 'Terrains',
            'account_type': 'asset_fixed',
        })
        self.assertEqual(immob_account.pcm_class, '2', "Le compte 2111 devrait être en classe 2.")
        self.assertTrue(immob_account.is_immobilisation, "Le compte 2111 devrait être marqué comme immobilisation.")
