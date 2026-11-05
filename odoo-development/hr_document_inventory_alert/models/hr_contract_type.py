from odoo import fields, models


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    required_document_type_ids = fields.Many2many(
        comodel_name='hr.document.type',
        relation='hr_contract_type_document_type_rel',
        column1='contract_type_id',
        column2='document_type_id',
        string='Documents obligatoires',
    )