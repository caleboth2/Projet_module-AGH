from odoo import models, api


class ReportFluxTresorerie(models.AbstractModel):
    _name = 'report.agh_reporting.report_flux_tresorerie'
    _description = 'Rapport Flux de Trésorerie'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.financial.report.print'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.financial.report.print',
            'docs': docs,
        }
