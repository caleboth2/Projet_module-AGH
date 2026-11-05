from odoo import models, fields, api


class AghGumroadProduct(models.Model):
    _name = 'agh.gumroad.product'
    _description = 'AGH Gumroad Product'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char('Product Name', required=True, tracking=True)
    gumroad_id = fields.Char('Gumroad Product ID', required=True, index=True)
    gumroad_url = fields.Char('Gumroad URL')
    price = fields.Float('Unit Price', digits=(16, 2))
    currency = fields.Char('Currency', default='USD')
    published = fields.Boolean('Published', default=True)

    raw_json = fields.Text('Raw Gumroad Payload',
                           help="Payload JSON brut renvoyé par l'API Gumroad (audit / souveraineté).")

    connector_id = fields.Many2one('agh.gumroad.connector', string='Connector', required=True,
                                   ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Linked Project',
                                 help="Projet Odoo correspondant à cette application Gumroad")

    sale_ids = fields.One2many('agh.gumroad.sale', 'product_id', string='Sales')
    metric_ids = fields.One2many('agh.gumroad.metric', 'product_id', string='Daily Metrics')

    total_sales = fields.Integer('Total Sales', compute='_compute_totals', store=False)
    total_revenue = fields.Float('Total Revenue', compute='_compute_totals', store=False)
    avg_basket = fields.Float('Average Basket', compute='_compute_totals', store=False)

    _sql_constraints = [
        ('gumroad_id_uniq', 'unique(gumroad_id)', 'Gumroad product ID must be unique.'),
    ]

    @api.depends('sale_ids.total_price')
    def _compute_totals(self):
        for rec in self:
            sales = rec.sale_ids.filtered(lambda s: not s.refunded)
            qty = sum(sales.mapped('quantity')) or 0
            revenue = sum(sales.mapped('total_price'))
            rec.total_sales = qty
            rec.total_revenue = revenue
            rec.avg_basket = (revenue / qty) if qty else 0.0
