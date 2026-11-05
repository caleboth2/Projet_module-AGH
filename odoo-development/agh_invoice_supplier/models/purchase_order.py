# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    agh_invoice_ids = fields.One2many(
        'account.move',
        'agh_purchase_order_id',
        string='Factures liees',
    )
    agh_invoice_count = fields.Integer(
        string='Nombre factures',
        compute='_compute_invoice_count',
    )
    agh_total_invoiced = fields.Monetary(
        string='Total facture',
        compute='_compute_invoiced_amounts',
        currency_field='currency_id',
    )
    agh_total_received = fields.Monetary(
        string='Total recu',
        compute='_compute_received_amounts',
        currency_field='currency_id',
    )

    @api.depends('agh_invoice_ids')
    def _compute_invoice_count(self):
        for order in self:
            order.agh_invoice_count = len(order.agh_invoice_ids)

    @api.depends('agh_invoice_ids.amount_total', 'agh_invoice_ids.state')
    def _compute_invoiced_amounts(self):
        for order in self:
            posted_invoices = order.agh_invoice_ids.filtered(lambda i: i.state == 'posted')
            order.agh_total_invoiced = sum(posted_invoices.mapped('amount_total'))

    @api.depends('order_line', 'order_line.qty_received', 'order_line.product_qty', 'order_line.price_unit')
    def _compute_received_amounts(self):
        for order in self:
            received_amount = 0.0
            for line in order.order_line:
                received_qty = line.qty_received or line.product_qty or 0.0
                price_unit = line.price_unit or 0.0
                received_amount += received_qty * price_unit
            order.agh_total_received = received_amount

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Factures'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('agh_purchase_order_id', '=', self.id)],
        }
