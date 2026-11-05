from odoo import models, fields

class KnowledgeTag(models.Model):
    _name = 'agh.knowledge.tag'
    _description = 'Tag intelligent pour articles'

    name = fields.Char(string='Nom', required=True)
    color = fields.Integer(string='Couleur')
    article_count = fields.Integer(
        string='Nombre d\'articles',
        compute='_compute_article_count'
    )
    is_smart_tag = fields.Boolean(string='Tag intelligent', default=False)
    tag_rule = fields.Char(string='Règle du tag intelligent')
    active = fields.Boolean(default=True)

    def _compute_article_count(self):
        for tag in self:
            tag.article_count = self.env['agh.knowledge.article',].search_count([
                ('tag_ids', 'in', tag.id)
            ])