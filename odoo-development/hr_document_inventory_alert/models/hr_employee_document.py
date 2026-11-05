from odoo import api, fields, models


class HrEmployeeDocument(models.Model):
    _name = 'hr.employee.document'
    _description = 'Document d’un employé'
    _order = 'document_type_id, id'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employé',
        required=True,
        ondelete='cascade',
    )

    document_type_id = fields.Many2one(
        comodel_name='hr.document.type',
        string='Type de document',
        required=True,
        ondelete='restrict',
    )

    attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='Fichier',
        required=True,
        ondelete='restrict',
    )

    is_provided = fields.Boolean(
        string='Fourni',
        compute='_compute_is_provided',
        store=True,
    )

    @api.depends('attachment_id')
    def _compute_is_provided(self):
        for document in self:
            document.is_provided = bool(document.attachment_id)