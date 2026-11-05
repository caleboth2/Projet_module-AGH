# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    agh_client_ref = fields.Char(
        string="Ref. Bon de commande client",
        help="Reference du bon de commande du client.",
    )
    agh_acompte_percentage = fields.Float(
        string="Pourcentage acompte (%)",
        default=0.0,
        help="Pourcentage d'acompte a facturer a la confirmation du devis.",
    )
    agh_acompte_invoice_id = fields.Many2one(
        comodel_name='account.move',
        string="Facture d'acompte",
        readonly=True,
        copy=False,
    )

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.agh_acompte_percentage and order.agh_acompte_percentage > 0:
                order._create_acompte_from_order()
        return res

    def _create_acompte_from_order(self):
        """Cree une facture d'acompte (brouillon) depuis le devis."""
        self.ensure_one()
        if self.agh_acompte_invoice_id:
            return self.agh_acompte_invoice_id

        acompte_amount = (self.amount_total or 0.0) * (self.agh_acompte_percentage / 100.0)
        if acompte_amount <= 0:
            return False

        journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.company_id.id)],
            limit=1,
        )
        if not journal:
            return False

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'journal_id': journal.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'name': f"Acompte {self.agh_acompte_percentage:.2f}% - {self.name}",
                'quantity': 1.0,
                'price_unit': acompte_amount,
            })],
        }

        acompte_invoice = self.env['account.move'].create(invoice_vals)
        self.agh_acompte_invoice_id = acompte_invoice.id
        return acompte_invoice
