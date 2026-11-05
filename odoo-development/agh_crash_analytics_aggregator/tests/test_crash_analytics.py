# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAghCrashAnalytics(TransactionCase):

    def setUp(self):
        super().setUp()
        self.CrashReport = self.env['agh.crash.report']

    def test_crash_report_and_task_creation(self):
        crash = self.CrashReport.create({
            'name': 'NullPointerException in Login',
            'app_name': 'AGH Mobile',
            'package_name': 'com.agh.mobile',
            'exception_type': 'NullPointerException',
            'severity': 'critical',
            'stack_trace': 'at com.agh.mobile.Login.onClick(Login.java:42)',
        })
        self.assertEqual(crash.state, 'new')
        self.assertFalse(crash.task_id)

        # Action creation tâche
        crash.action_create_project_task()
        self.assertTrue(crash.task_id)
        self.assertEqual(crash.state, 'in_progress')
        self.assertIn('CRITICAL', crash.task_id.name)
