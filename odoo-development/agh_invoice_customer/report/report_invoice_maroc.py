# -*- coding: utf-8 -*-
from odoo import api, models


class ReportInvoiceMaroc(models.AbstractModel):
    _name = 'report.agh_invoice_customer.report_invoice_maroc_template'
    _description = "Rapport facture conforme Maroc"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'company': self.env.company,
            'get_tva_summary': self._get_tva_summary,
        }

    def _get_tva_summary(self, invoice):
        """Resume TVA par taux: { 'Tax Name': montant_tva, ... }."""
        tva_summary = {}
        for line in invoice.invoice_line_ids:
            for tax in line.tax_ids:
                tax_amount = (line.price_subtotal or 0.0) * ((tax.amount or 0.0) / 100.0)
                tva_summary[tax.name] = tva_summary.get(tax.name, 0.0) + tax_amount
        return tva_summary
