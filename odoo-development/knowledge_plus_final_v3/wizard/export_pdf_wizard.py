from odoo import models, fields

class ExportPDFWizard(models.TransientModel):
    _name = 'knowledge.export.pdf.wizard'
    _description = 'Assistant d\'export PDF'

    article_ids = fields.Many2many('agh.knowledge.article', string='Articles à exporter')
    include_header = fields.Boolean(string='Inclure l\'en-tête', default=True)
    include_footer = fields.Boolean(string='Inclure le pied de page', default=True)
    include_toc = fields.Boolean(string='Inclure la table des matières', default=True)
    page_format = fields.Selection([
        ('a4', 'A4'),
        ('letter', 'Letter')
    ], string='Format de page', default='a4')

    def action_export(self):
        return self.env.ref('knowledge_plus.action_export_pdf').report_action(self.article_ids)