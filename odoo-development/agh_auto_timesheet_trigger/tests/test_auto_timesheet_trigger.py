# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

@tagged('post_install', '-at_install')
class TestAghAutoTimesheetTrigger(TransactionCase):

    def setUp(self):
        super(TestAghAutoTimesheetTrigger, self).setUp()
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee Auto Timesheet',
            'user_id': self.env.user.id,
        })
        self.Project = self.env['project.project']
        self.Task = self.env['project.task']
        self.project = self.Project.create({'name': 'Test Auto Timesheet Project'})

    def test_timer_start_stop(self):
        task = self.Task.create({
            'name': 'Test Task Timer',
            'project_id': self.project.id,
        })
        task._start_timesheet_timer()
        self.assertTrue(task.timer_start, "Timer should be started")
        
        # Simulate timer start 1 hour ago
        task.timer_start = datetime.now() - timedelta(hours=1)
        task._stop_timesheet_timer()
        self.assertFalse(task.timer_start, "Timer should be reset to False")
        
        line = self.env['account.analytic.line'].search([('task_id', '=', task.id)], limit=1)
        self.assertTrue(line, "Timesheet line should be created automatically")
        self.assertAlmostEqual(line.unit_amount, 1.0, delta=0.05)
