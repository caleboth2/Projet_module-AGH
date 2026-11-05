# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAghHealthScoreDashboard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Dashboard = self.env['agh.health.score.dashboard']

    def test_health_score_calculation_and_ai_agents(self):
        dashboard = self.Dashboard.create({
            'name': 'Audit Mensuel Santé',
            'dev_cost': 150000.0,
        })
        self.assertTrue(dashboard.health_score > 0)
        self.assertIn(dashboard.health_status, ['excellent', 'good', 'warning', 'critical'])

        # Lancer l'orchestration IA (QA, PM, SecOps)
        res = dashboard.action_run_ai_agents_orchestration()
        self.assertTrue(res)
        self.assertTrue(dashboard.qa_agent_feedback)
        self.assertTrue(dashboard.pm_agent_feedback)
        self.assertTrue(dashboard.secops_agent_feedback)
