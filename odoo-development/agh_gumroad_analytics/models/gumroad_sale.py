from odoo import models, fields, api


class AghGumroadSale(models.Model):
    _name = 'agh.gumroad.sale'
    _description = 'AGH Gumroad Sale'
    _order = 'sale_date desc'

    name = fields.Char('Sale ID', required=True, index=True)
    product_id = fields.Many2one('agh.gumroad.product', string='Product',
                                 required=True, ondelete='cascade')
    project_id = fields.Many2one(related='product_id.project_id', store=True)

    # ----- Souveraineté client -----
    partner_id = fields.Many2one('res.partner', string='Client (res.partner)',
                                 ondelete='set null',
                                 help="Client local créé/mis à jour automatiquement. "
                                      "L'agence conserve la souveraineté de la base clients.")

    sale_date = fields.Datetime('Sale Date')

    # ----- Pricing (bug fix) -----
    # Gumroad renvoie `price` en CENTS et c'est le TOTAL payé (taxes incluses) pour la vente,
    # PAS le prix unitaire. On stocke donc :
    #   - total_price : montant total payé (price_cents / 100)
    #   - price       : prix unitaire = total_price / quantity
    # Ainsi le prix affiché correspond au prix du produit dans Gumroad.
    price = fields.Float('Unit Price', digits=(16, 2),
                         help="Prix unitaire dérivé du total payé / quantité.")
    total_price = fields.Float('Total Paid', digits=(16, 2),
                               help="Montant total payé (taxes incluses), tel que renvoyé par Gumroad.")
    quantity = fields.Integer('Quantity', default=1)
    currency = fields.Char('Currency', default='USD')

    email = fields.Char('Buyer Email')
    country = fields.Char('Country')
    referrer = fields.Char('Traffic Source / Referrer')
    refunded = fields.Boolean('Refunded', default=False)

    # ----- Souveraineté audit -----
    raw_json = fields.Text('Raw Gumroad Payload',
                           help="JSON brut de la transaction Gumroad. Permet l'audit même "
                                "si l'API Gumroad change ou est arrêtée.")

    _sql_constraints = [
        ('sale_uniq', 'unique(name)', 'Sale ID must be unique.'),
    ]
