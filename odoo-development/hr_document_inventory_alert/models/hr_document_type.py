from odoo import fields, models


class HrDocumentType(models.Model):
    _name = 'hr.document.type'
    _description = 'Type de document RH'

    name = fields.Char(
        string='Nom du document',
        required=True,
    )

    code = fields.Char(
        string='Code',
        required=True,
    )

    description = fields.Text(
        string='Description',
    )

    active = fields.Boolean(
        string='Actif',
        default=True,
    )