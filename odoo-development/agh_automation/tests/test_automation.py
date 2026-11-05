# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestAghAutomation(TransactionCase):

    def setUp(self):
        super(TestAghAutomation, self).setUp()
        self.AutomationConfig = self.env['agh.automation.config']

    def test_dashboard_stats(self):
        config = self.AutomationConfig.create({})
        self.assertIsNotNone(config.success_count_today)
        self.assertIsNotNone(config.error_count_today)
        self.assertIsNotNone(config.active_alerts_count)
        self.assertIsNotNone(config.scheduled_jobs_count)
