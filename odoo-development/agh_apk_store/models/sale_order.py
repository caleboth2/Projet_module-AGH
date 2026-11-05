from collections import defaultdict

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_apk_licenses_after_payment(self):
        licenses_by_order_product = defaultdict(int)
        order_by_id = {}

        for order in self:
            order_by_id[order.id] = order
            for line in order.order_line:
                if line.product_id.is_apk:
                    quantity = int(line.product_uom_qty)
                    if quantity > 0:
                        licenses_by_order_product[
                            (order.id, line.product_id.id)
                        ] += quantity

        if not licenses_by_order_product:
            return

        license_model = self.env['agh.apk.license']
        values_list = []
        for (order_id, product_id), requested_quantity in licenses_by_order_product.items():
            existing_quantity = license_model.search_count([
                ('sale_order_id', '=', order_id),
                ('product_id', '=', product_id),
            ])
            missing_quantity = requested_quantity - existing_quantity
            order = order_by_id[order_id]

            values_list.extend({
                'partner_id': order.partner_id.id,
                'product_id': product_id,
                'sale_order_id': order_id,
                'company_id': order.company_id.id,
                'state': 'active',
            } for _ in range(max(missing_quantity, 0)))

        if not values_list:
            return

        created_licenses = license_model.create(values_list)
        template = self.env.ref(
            'agh_apk_store.email_template_apk_license',
            raise_if_not_found=False,
        )
        if template:
            for license_record in created_licenses:
                template.send_mail(license_record.id)