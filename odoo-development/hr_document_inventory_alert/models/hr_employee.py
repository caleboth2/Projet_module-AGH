from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_document_ids = fields.One2many(
        comodel_name='hr.employee.document',
        inverse_name='employee_id',
        string='Documents',
    )

    completeness_rate = fields.Float(
        string='Taux de complétude (%)',
        compute='_compute_document_completeness',
        store=True,
    )

    is_dossier_incomplete = fields.Boolean(
        string='Dossier incomplet',
        compute='_compute_document_completeness',
        store=True,
    )

    @api.depends(
        'contract_id.contract_type_id.required_document_type_ids',
        'employee_document_ids.document_type_id',
        'employee_document_ids.attachment_id',
    )
    def _compute_document_completeness(self):
        for employee in self:
            contract = employee.contract_id
            contract_type = contract.contract_type_id if contract else False
            required_types = (
                contract_type.required_document_type_ids
                if contract_type
                else self.env['hr.document.type']
            )

            if not required_types:
                employee.completeness_rate = 100.0
                employee.is_dossier_incomplete = False
                continue

            provided_types = employee.employee_document_ids.filtered(
                lambda document: (
                    document.document_type_id in required_types
                    and document.attachment_id
                )
            ).mapped('document_type_id')

            rate = len(provided_types) / len(required_types) * 100
            employee.completeness_rate = round(rate, 2)
            employee.is_dossier_incomplete = rate < 100