from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        result = super()._post_process()

        done_transactions = self.filtered(
            lambda transaction: transaction.state == 'done'
        )
        done_transactions.mapped('sale_order_ids')._create_apk_licenses_after_payment()

        return result