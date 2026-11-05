from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class ReportBalanceAgee(models.AbstractModel):
    _name = 'report.agh_reporting.report_balance_agee'
    _description = 'Rapport Balance Âgée'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.balance.aged'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.balance.aged',
            'docs': docs,
            'parse_data': self._parse_data,
        }

    def _parse_data(self, data_str):
        if not data_str:
            return []
        try:
            return eval(data_str, {'__builtins__': {}}, {})  # noqa: S307
        except Exception as e:
            _logger.warning("Impossible de parser les données balance âgée: %s", str(e))
            return []
