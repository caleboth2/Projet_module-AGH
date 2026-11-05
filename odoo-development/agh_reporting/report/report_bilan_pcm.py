from odoo import models, api


class ReportBilanPCM(models.AbstractModel):
    _name = 'report.agh_reporting.report_bilan_pcm'
    _description = 'Rapport Bilan PCM'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.financial.report.print'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.financial.report.print',
            'docs': docs,
        }
