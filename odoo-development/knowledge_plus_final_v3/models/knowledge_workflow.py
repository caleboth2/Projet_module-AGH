from odoo import models, fields

class KnowledgeWorkflowConfig(models.Model):
    _name = 'agh.knowledge.workflow.config'
    _description = 'Configuration du workflow'

    name = fields.Char(string='Nom', required=True)
    category_id = fields.Many2one('agh.knowledge.category', string='Catégorie concernée')
    approver_ids = fields.Many2many('res.users', string='Approbateurs par défaut')
    requires_validation = fields.Boolean(string='Nécessite une validation', default=True)
    auto_approve = fields.Boolean(string='Approbation automatique', default=False)