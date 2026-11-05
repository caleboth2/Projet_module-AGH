from odoo import models, fields


class AghGumroadMetric(models.Model):
    _name = 'agh.gumroad.metric'
    _description = 'AGH Daily Gumroad Metric per Product'
    _order = 'date desc'

    product_id = fields.Many2one('agh.gumroad.product', required=True, ondelete='cascade')
    project_id = fields.Many2one(related='product_id.project_id', store=True)
    date = fields.Date('Date', required=True)

    sales_count = fields.Integer('Sales Count')
    revenue = fields.Float('Revenue')
    avg_basket = fields.Float('Average Basket')
    views = fields.Integer('Page Views')
    conversion_rate = fields.Float('Conversion Rate (%)')
    top_referrer = fields.Char('Top Traffic Source')

    _sql_constraints = [
        ('product_date_uniq', 'unique(product_id, date)',
         'One metric record per product per day.'),
    ]
