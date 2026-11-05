from odoo import models, api


class ReportGrandLivre(models.AbstractModel):
    _name = 'report.agh_reporting.report_grand_livre'
    _description = 'Rapport Grand-Livre'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.general.ledger'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.general.ledger',
            'docs': docs,
        }
