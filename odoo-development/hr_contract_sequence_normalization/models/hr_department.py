from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    code = fields.Char(
        string="Code du Département",
        size=10,
        help="Aide à générer la référence des contrats (ex: RECRUT, IT, FIN).",
    )

    @api.constrains('code')
    def _check_code_format(self):
        for dept in self:
            if dept.code and not dept.code.isalnum():
                raise ValidationError("Le code du département ne doit contenir que des lettres et chiffres (sans espaces ni caractères spéciaux).")