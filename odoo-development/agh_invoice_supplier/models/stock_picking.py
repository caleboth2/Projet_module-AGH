# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    agh_invoice_ids = fields.Many2many(
        'account.move',
        relation='agh_invoice_picking_rel',
        column1='picking_id',
        column2='invoice_id',
        string='Factures liees',
    )
    agh_is_fully_invoiced = fields.Boolean(
        string='Entierement facture',
        compute='_compute_invoice_status',
    )

    @api.depends('agh_invoice_ids', 'agh_invoice_ids.invoice_line_ids', 'move_ids.quantity')
    def _compute_invoice_status(self):
        for picking in self:
            total_received = sum(picking.move_ids.mapped('quantity'))
            picking_products = picking.move_ids.mapped('product_id')
            total_invoiced = 0.0
            for invoice in picking.agh_invoice_ids:
                for line in invoice.invoice_line_ids:
                    if line.product_id and line.product_id in picking_products:
                        total_invoiced += line.quantity or 0.0
            if total_received > 0 and total_invoiced >= total_received:
                picking.agh_is_fully_invoiced = True
            else:
                picking.agh_is_fully_invoiced = False
