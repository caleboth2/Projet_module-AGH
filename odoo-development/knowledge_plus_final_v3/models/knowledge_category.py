from odoo import models, fields, api

class KnowledgeCategory(models.Model):
    _name = 'agh.knowledge.category'
    _description = 'Catégorie de connaissances'
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Nom', required=True, translate=True)
    complete_name = fields.Char(
        string='Nom complet',
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )
    description = fields.Html(string='Description')
    parent_id = fields.Many2one(
        'agh.knowledge.category',
        string='Catégorie parente',
        ondelete='restrict',
        index=True
    )
    child_ids = fields.One2many(
        'agh.knowledge.category',
        'parent_id',
        string='Sous-catégories'
    )
    parent_path = fields.Char(index=True, unaccent=False)
    article_count = fields.Integer(
        string='Nombre d\'articles',
        compute='_compute_article_count'
    )
    color = fields.Integer(string='Couleur')
    active = fields.Boolean(default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f'{category.parent_id.complete_name} / {category.name}'
            else:
                category.complete_name = category.name

    def _compute_article_count(self):
        for category in self:
            category.article_count = self.env['agh.knowledge.article',].search_count([
                ('category_id', '=', category.id)
            ])