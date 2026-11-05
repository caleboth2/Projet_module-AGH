import uuid

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ApkLicense(models.Model):
    _name = 'agh.apk.license'
    _description = 'Licence APK et Bundle'

    name = fields.Char(
        string='Clé de licence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
    )
    partner_id = fields.Many2one('res.partner', string='Client', required=True, index=True)
    product_id = fields.Many2one('product.product', string='Produit / APK', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Commande liée', readonly=True, index=True)
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('active', 'Active'),
            ('suspended', 'Suspendue'),
            ('revoked', 'Révoquée'),
            ('expired', 'Expirée'),
        ],
        string='État',
        required=True,
        default='draft',
        index=True,
    )
    valid_until = fields.Date(string='Valable jusqu’au')
    max_activations = fields.Integer(string='Appareils autorisés', default=1, required=True)
    device_ids = fields.Json(string='Appareils activés', default=list, copy=False)

    download_token = fields.Char(
        string="Jeton de téléchargement",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
    )

    @api.constrains('max_activations', 'device_ids')
    def _check_activation_limits(self):
        for license_record in self:
            devices = license_record.device_ids or []
            if license_record.max_activations < 1:
                raise ValidationError('Le nombre maximal d’appareils doit être supérieur à zéro.')
            if not isinstance(devices, list):
                raise ValidationError('Les appareils activés doivent être enregistrés sous forme de liste.')
            if len(devices) > license_record.max_activations:
                raise ValidationError('Le nombre d’appareils activés dépasse le quota autorisé.')