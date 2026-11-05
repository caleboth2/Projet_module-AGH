# -*- coding: utf-8 -*-
from odoo import api, models


class RASCertificateReport(models.AbstractModel):
    _name = 'report.agh_invoice_supplier.ras_certificate'
    _description = 'Rapport attestation RAS'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.ras.maroc'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.ras.maroc',
            'docs': docs,
        }
