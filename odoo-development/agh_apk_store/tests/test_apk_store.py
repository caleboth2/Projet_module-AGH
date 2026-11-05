import base64
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestApkStore(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'APK Store Test Customer',
            'email': 'apk-test@example.com',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test APK',
            'type': 'service',
            'list_price': 10.0,
            'is_apk': True,
            'apk_version': '1.0.0',
            'apk_file': base64.b64encode(b'test-apk-content'),
            'apk_filename': 'test.apk',
        })

    def _create_order(self, quantity=1):
        pricelist = self.env['product.pricelist'].search([
            ('company_id', 'in', (self.company.id, False)),
        ], limit=1)
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company.id,
            'pricelist_id': pricelist.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': quantity,
                'price_unit': self.product.list_price,
            })],
        })

    def test_apk_product_requires_service_and_file(self):
        with self.assertRaises(ValidationError):
            self.env['product.product'].create({
                'name': 'Physical APK Test',
                'type': 'consu',
                'is_apk': True,
                'apk_file': base64.b64encode(b'test'),
            })

        with self.assertRaises(ValidationError):
            self.env['product.product'].create({
                'name': 'Missing APK File Test',
                'type': 'service',
                'is_apk': True,
            })

    def test_license_state_and_activation_quota(self):
        license_record = self.env['agh.apk.license'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'company_id': self.company.id,
            'state': 'active',
            'max_activations': 2,
            'device_ids': ['device-a'],
        })
        self.assertEqual(license_record.state, 'active')
        self.assertEqual(license_record.company_id, self.company)

        with self.assertRaises(ValidationError):
            license_record.write({'device_ids': ['device-a', 'device-b', 'device-c']})

    def test_paid_order_creates_one_license_per_unit_and_is_idempotent(self):
        order = self._create_order(quantity=3)
        template = self.env.ref(
            'agh_apk_store.email_template_apk_license',
        )

        with patch.object(type(template), 'send_mail') as send_mail:
            order._create_apk_licenses_after_payment()

        licenses = self.env['agh.apk.license'].search([
            ('sale_order_id', '=', order.id),
        ])
        self.assertEqual(len(licenses), 3)
        self.assertTrue(all(license_record.state == 'active' for license_record in licenses))
        self.assertEqual(send_mail.call_count, 3)

        with patch.object(type(template), 'send_mail') as send_mail:
            order._create_apk_licenses_after_payment()

        self.assertEqual(self.env['agh.apk.license'].search_count([
            ('sale_order_id', '=', order.id),
        ]), 3)
        send_mail.assert_not_called()