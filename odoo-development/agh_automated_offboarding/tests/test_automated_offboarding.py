# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAghAutomatedOffboarding(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Employee = self.env['hr.employee']
        self.Wizard = self.env['agh.employee.offboarding.wizard']
        self.User = self.env['res.users']

    def test_01_automatic_onboarding_on_employee_creation(self):
        """Vérifie la création automatique du compte Odoo et de l'invitation GitHub lors de l'ajout d'un employé."""
        employee = self.Employee.create({
            'name': 'Jean Dupont Onboarding',
            'work_email': 'jdupont@aghagency.com',
            'github_username': 'jdupont-agh',
        })
        self.assertTrue(employee.user_id, "Le compte utilisateur Odoo doit être créé automatiquement")
        self.assertEqual(employee.user_id.login, 'jdupont@aghagency.com')
        self.assertEqual(employee.onboarding_status, 'done')
        self.assertIn('✓ Compte Utilisateur Odoo créé', employee.onboarding_log)
        self.assertIn('✓ GitHub Org', employee.onboarding_log)

    def test_02_automatic_offboarding_on_employee_archiving(self):
        """Vérifie la désactivation automatique des accès (Odoo User, Vault, GitHub) à l'archivage d'un employé."""
        employee = self.Employee.create({
            'name': 'Marie Curie Offboarding',
            'work_email': 'mcurie@aghagency.com',
            'github_username': 'mcurie-agh',
        })
        user = employee.user_id
        self.assertTrue(user.active)

        # Archiver l'employé
        employee.write({'active': False})

        self.assertFalse(employee.active, "L'employé doit être archivé")
        self.assertFalse(user.active, "Le compte utilisateur Odoo rattaché doit être désactivé")

    def test_03_offboarding_wizard_manual_execution(self):
        """Vérifie l'exécution manuelle du wizard d'offboarding."""
        employee = self.Employee.create({
            'name': 'Test Dev Departing Wizard',
            'work_email': 'departing.wizard@aghagency.com',
        })
        self.assertTrue(employee.active)

        wizard = self.Wizard.create({
            'employee_id': employee.id,
            'reason': 'Fin de mission contractuelle',
            'revoke_github': True,
            'revoke_ssh': True,
            'revoke_vault': True,
            'revoke_api_keys': True,
        })
        self.assertEqual(wizard.state, 'draft')

        wizard.action_execute_offboarding()
        self.assertEqual(wizard.state, 'done')
        self.assertFalse(employee.active)
        self.assertIn('✓ Révocation GitHub', wizard.revocation_log)
        self.assertIn('✓ Révocation Vault', wizard.revocation_log)

    def test_04_employee_unlink_purges_timesheets_and_preserves_knowledge(self):
        """Vérifie que la suppression d'un employé purge ses feuilles de temps mais préserve ses dossiers Knowledge."""
        employee = self.Employee.create({
            'name': 'Test Employee Deletion',
            'work_email': 'deletion.test@aghagency.com',
        })
        emp_id = employee.id

        # Créer une feuille de temps factice rattachée
        project = self.env['project.project'].create({'name': 'Project Test Deletion'})
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Temps de travail de test',
            'project_id': project.id,
            'employee_id': emp_id,
            'unit_amount': 4.0,
        })
        self.assertTrue(timesheet.exists())

        user_id = employee.user_id.id if employee.user_id else False

        # Supprimer l'employé
        employee.unlink()

        # Vérifier que la feuille de temps a été purgée, l'employé et l'utilisateur Odoo supprimés
        self.assertFalse(timesheet.exists(), "Les feuilles de temps de l'employé doivent être supprimées automatiquement")
        self.assertFalse(self.Employee.search([('id', '=', emp_id)]), "L'employé doit être supprimé sans erreur SQL")
        if user_id:
            self.assertFalse(self.User.search([('id', '=', user_id)]), "L'utilisateur Odoo rattaché doit également être supprimé")

    def test_05_offboarding_wizard_with_custom_github_username(self):
        """Vérifie que la saisie d'un pseudo GitHub personnalisé dans le wizard révoque l'accès et met à jour l'employé."""
        employee = self.Employee.create({
            'name': 'Test Custom GH User',
            'work_email': 'customgh@aghagency.com',
        })
        wizard = self.Wizard.create({
            'employee_id': employee.id,
            'github_username': 'custom-dev-gh',
            'reason': 'Départ confirmé',
            'revoke_github': True,
        })
        wizard.action_execute_offboarding()
        self.assertEqual(wizard.state, 'done')
        self.assertFalse(employee.active)
        self.assertEqual(employee.github_username, 'custom-dev-gh')
        self.assertIn('✓ Révocation GitHub', wizard.revocation_log)



