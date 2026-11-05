# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    agh_po_line_id = fields.Many2one('purchase.order.line', string='Ligne bon de commande')
    agh_picking_line_id = fields.Many2one('stock.move', string='Ligne reception')
    agh_match_status = fields.Selection(
        selection=[
            ('pending', 'En attente'),
            ('matched', 'Rapproche'),
            ('mismatch', 'Ecart'),
        ],
        string='Statut rapprochement',
        default='pending',
    )
    agh_qty_received = fields.Float(
        string='Quantite recue',
        compute='_compute_qty_received',
    )

    @api.depends('agh_po_line_id', 'agh_po_line_id.qty_received', 'agh_po_line_id.product_qty')
    def _compute_qty_received(self):
        for line in self:
            if line.agh_po_line_id:
                line.agh_qty_received = line.agh_po_line_id.qty_received or line.agh_po_line_id.product_qty or 0.0
            else:
                line.agh_qty_received = 0.0
