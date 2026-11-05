# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Wizard3WayMatch(models.TransientModel):
    _name = 'wizard.3way.match'
    _description = 'Wizard Rapprochement 3 voies'

    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        domain=[('move_type', '=', 'in_invoice')],
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Bon de commande',
        domain="[('partner_id', '=', partner_id), ('state', '=', 'purchase')]",
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Fournisseur',
        related='invoice_id.partner_id',
        readonly=True,
    )
    stock_picking_ids = fields.Many2many(
        'stock.picking',
        string='Bons de reception',
        domain="[('partner_id', '=', partner_id), ('state', '=', 'done')]",
    )
    price_tolerance = fields.Float(string='Tolerance prix (%)', default=5.0)
    qty_tolerance = fields.Float(string='Tolerance quantite (%)', default=10.0)
    match_result = fields.Text(string='Resultat rapprochement', readonly=True)

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order(self):
        if self.purchase_order_id:
            pickings = self.purchase_order_id.picking_ids.filtered(lambda p: p.state == 'done')
            self.stock_picking_ids = [(6, 0, pickings.ids)]
        else:
            self.stock_picking_ids = [(5, 0, 0)]

    def action_match(self):
        self.ensure_one()
        invoice = self.invoice_id
        if not self.purchase_order_id:
            raise UserError(_("Veuillez selectionner un bon de commande."))
        invoice.write({
            'agh_purchase_order_id': self.purchase_order_id.id,
            'agh_stock_picking_ids': [(6, 0, self.stock_picking_ids.ids)],
            'agh_price_tolerance': self.price_tolerance,
            'agh_qty_tolerance': self.qty_tolerance,
        })
        invoice._compute_deviations()
        invoice._compute_3way_status()

        picking_names = self.stock_picking_ids.mapped('name')
        if not picking_names:
            picking_names = ['-']
        result_lines = [
            "=== RAPPROCHEMENT 3 VOIES ===",
            "Bon de commande: %s" % self.purchase_order_id.name,
            "Bons de reception: %s" % ", ".join(picking_names),
            "",
            "Ecart prix detecte: %.2f%%" % (invoice.agh_price_deviation or 0.0),
            "Ecart quantite detecte: %.2f%%" % (invoice.agh_qty_deviation or 0.0),
            "",
        ]
        if invoice.agh_match_details:
            result_lines.append("Details:")
            result_lines.append(invoice.agh_match_details)
        if invoice.agh_3way_match_status == 'matched':
            result_lines.append("")
            result_lines.append("STATUT: Rapproche - Les ecarts sont dans les limites autorisees")
        else:
            result_lines.append("")
            result_lines.append("STATUT: Ecart detecte - Une validation supplementaire est requise")

        self.match_result = "\n".join(result_lines)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.3way.match',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def action_approve(self):
        self.ensure_one()
        self.invoice_id.write({'agh_3way_match_status': 'approved'})
        return {'type': 'ir.actions.act_window_close'}
