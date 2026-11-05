from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_apk = fields.Boolean(
        string="Est un produit APK/Bundle",
        default=False,
    )
    apk_version = fields.Char(
        string="Version de l'APK",
    )
    apk_file = fields.Binary(
        string="Fichier APK",
        attachment=True,
    )
    apk_filename = fields.Char(
        string="Nom du fichier APK",
    )

    @api.constrains("is_apk", "type", "apk_file")
    def _check_apk_product(self):
        for product in self:
            if product.is_apk and product.type != "service":
                raise ValidationError(
                    "Un produit APK doit être configuré comme un service."
                )
            if product.is_apk and not product.apk_file:
                raise ValidationError(
                    "Un produit APK doit avoir un fichier APK."
                )