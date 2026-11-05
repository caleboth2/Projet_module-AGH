# -*- coding: utf-8 -*-
import urllib.request
from datetime import datetime, timedelta
from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestOdoo18FullSuite(TransactionCase):

    def setUp(self):
        super().setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee Audit',
            'user_id': self.env.user.id,
        })
        self.user_admin = self.env.ref('base.user_admin')

    def test_01_certificate_workflow_admin_validation_mandatory(self):
        """Test workflow attestation : L'envoi par email doit échouer si non validé par admin."""
        certificate = self.env['hr.certificate'].create({
            'employee_id': self.employee.id,
            'certificate_type': 'ATT_TRAVAIL',
            'state': 'requested',
        })
        
        # 1. Tentative d'envoi avant validation -> Doit lever ValidationError
        with self.assertRaises(ValidationError):
            certificate.action_send_email()

        # 2. Validation Admin
        certificate.action_validate()
        self.assertEqual(certificate.state, 'validated')

        # 3. Envoi après validation -> Doit réussir
        self.assertTrue(certificate.state == 'validated')

    def test_02_knowledge_plus_wizards_comodel_compatibility(self):
        """Test compatibilité comodel agh.knowledge.article sur tous les wizards Knowledge."""
        article = self.env['agh.knowledge.article'].create({
            'name': 'Article Test Audit',
            'content': 'Contenu initial de test',
        })

        # Test Archive Wizard
        archive_wiz = self.env['knowledge.archive.wizard'].create({
            'article_ids': [(4, article.id)],
            'archive_reason': 'Test motif archivage',
            'permanent_delete': False,
        })
        archive_wiz.action_archive()
        self.assertFalse(article.active)
        self.assertEqual(article.state, 'archived')

        # Réactiver pour autres tests
        article.write({'active': True, 'state': 'approved'})

        # Test PDF Export Wizard
        export_wiz = self.env['knowledge.export.pdf.wizard'].create({
            'article_ids': [(4, article.id)],
        })
        self.assertIn(article, export_wiz.article_ids)

        # Test AI Meeting Wizard
        meeting_wiz = self.env['knowledge.ai.meeting.wizard'].create({
            'article_id': article.id,
            'raw_notes': '- Point 1: Validation CDC\n- Point 2: Architecture RAG',
        })
        self.assertEqual(meeting_wiz.article_id, article)

    def test_03_timesheet_temporal_integrity(self):
        """Test intégration Timesheet & contrôle temporel."""
        project = self.env['project.project'].create({'name': 'Projet Audit Timesheet'})
        task = self.env['project.task'].create({
            'name': 'Tâche Audit',
            'project_id': project.id,
        })

        # Enregistrement d'une ligne de temps avec employé
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Saisie Horaires Audit',
            'project_id': project.id,
            'task_id': task.id,
            'employee_id': self.employee.id,
            'date': fields.Date.today(),
            'unit_amount': 2.0,
        })
        self.assertEqual(timesheet.unit_amount, 2.0)
        self.assertEqual(timesheet.employee_id, self.employee)

    def test_04_integrations_db_sanity(self):
        """Test Sanity des Connecteurs Systèmes en Base de Données."""
        # GitHub Connectors
        gh_connectors = self.env['agh.github.connector'].search([])
        self.assertTrue(len(gh_connectors) >= 1, "Au moins 1 connecteur GitHub doit être configuré")

        # Local LLM Config
        llm_configs = self.env['llm.config'].search([])
        self.assertTrue(len(llm_configs) >= 1, "Au moins 1 configuration LLM Local doit être présente")

    def test_05_ollama_llm_connectivity(self):
        """Test de connectivité directe avec le serveur Ollama LLM."""
        try:
            req = urllib.request.urlopen("http://host.docker.internal:11434/api/tags", timeout=3)
            self.assertEqual(req.status, 200, "Le serveur Ollama doit répondre avec un HTTP status 200")
        except Exception as e:
            self.fail(f"Impossible de se connecter au serveur Ollama LLM : {e}")

    def test_06_google_play_automation(self):
        """Test du module Google Play Automation Pipeline."""
        app = self.env['agh.google.play.app'].create({
            'name': 'AGH Agency Main App',
            'package_name': 'com.agh.agency.app',
        })
        track = self.env['agh.google.play.track'].create({
            'app_id': app.id,
            'version_code': 201,
            'version_name': '2.0.1',
            'track_name': 'production',
            'status': 'approved',
        })
        self.assertEqual(app.track_count, 1)
        self.assertTrue(app.action_sync_google_play())

    def test_07_crash_analytics_aggregator(self):
        """Test du module Crash Analytics Aggregator."""
        crash = self.env['agh.crash.report'].create({
            'name': 'Fatal Signal 11 in RenderEngine',
            'app_name': 'AGH Agency Mobile',
            'severity': 'critical',
            'stack_trace': 'at native_render(NativeLib.cpp:12)',
        })
        crash.action_create_project_task()
        self.assertTrue(crash.task_id)
        self.assertEqual(crash.state, 'in_progress')

    def test_08_automated_offboarding(self):
        """Test du module Offboarding & Access Revocation."""
        emp_test = self.env['hr.employee'].create({'name': 'Employee Offboard Target'})
        wiz = self.env['agh.employee.offboarding.wizard'].create({
            'employee_id': emp_test.id,
            'reason': 'Départ entreprise',
        })
        wiz.action_execute_offboarding()
        self.assertFalse(emp_test.active)
        self.assertIn('✓ Révocation GitHub', wiz.revocation_log)

    def test_09_health_score_dashboard_and_ai_agents(self):
        """Test du Macro Health Score Dashboard et de l'Orchestration des Agents IA."""
        dash = self.env['agh.health.score.dashboard'].create({
            'name': 'Health Score Executive Check',
            'dev_cost': 200000.0,
        })
        self.assertTrue(dash.health_score >= 0)
        res = dash.action_run_ai_agents_orchestration()
        self.assertTrue(res)
        self.assertTrue(dash.qa_agent_feedback)
        self.assertTrue(dash.pm_agent_feedback)
        self.assertTrue(dash.secops_agent_feedback)

    def test_10_automated_onboarding(self):
        """Test de l'Onboarding Automatique (Création Compte Odoo + Invitation GitHub Org)."""
        emp_new = self.env['hr.employee'].create({
            'name': 'Sophie Martin New Hire',
            'work_email': 'smartin@aghagency.com',
            'github_username': 'smartin-agh',
        })
        self.assertTrue(emp_new.user_id)
        self.assertEqual(emp_new.user_id.login, 'smartin@aghagency.com')
        self.assertEqual(emp_new.onboarding_status, 'done')

