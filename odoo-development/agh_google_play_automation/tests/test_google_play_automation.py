# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAghGooglePlayAutomation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.App = self.env['agh.google.play.app']
        self.Track = self.env['agh.google.play.track']

    def test_app_and_track_creation(self):
        app = self.App.create({
            'name': 'AGH Mobile App Test',
            'package_name': 'com.agh.agency.mobile',
        })
        self.assertEqual(app.track_count, 0)

        track = self.Track.create({
            'app_id': app.id,
            'version_code': 104,
            'version_name': '1.0.4',
            'track_name': 'beta',
            'status': 'in_review',
        })
        self.assertEqual(app.track_count, 1)
        self.assertEqual(track.track_name, 'beta')
        self.assertEqual(track.status, 'in_review')

        # Synchroniser
        res = app.action_sync_google_play()
        self.assertTrue(res)
