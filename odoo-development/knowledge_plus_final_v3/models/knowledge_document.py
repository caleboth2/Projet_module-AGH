from odoo import models, fields, api

class KnowledgeArticleDocument(models.Model):
    _name = 'agh.knowledge.article.document'
    _description = 'Document attaché à un article'
    _order = 'create_date desc'

    name = fields.Char(string='Nom du fichier', required=True)
    article_id = fields.Many2one('agh.knowledge.article', string='Article', required=True, ondelete='cascade')
    document_type = fields.Selection([
        ('image', 'Image'),
        ('pdf', 'PDF'),
        ('document', 'Document Office'),
        ('other', 'Autre')
    ], string='Type', compute='_compute_document_type', store=True)
    
    attachment_id = fields.Many2one('ir.attachment', string='Fichier')
    file_data = fields.Binary(string='Fichier', related='attachment_id.datas')
    file_size = fields.Integer(string='Taille', compute='_compute_file_size')
    file_extension = fields.Char(string='Extension', compute='_compute_file_extension')
    
    version = fields.Integer(string='Version', default=1)
    description = fields.Text(string='Description')
    uploaded_by = fields.Many2one('res.users', string='Ajouté par', default=lambda self: self.env.user)
    upload_date = fields.Datetime(string="Date d'ajout", default=fields.Datetime.now)
    
    @api.depends('attachment_id', 'attachment_id.mimetype')
    def _compute_document_type(self):
        for doc in self:
            if doc.attachment_id and doc.attachment_id.mimetype:
                mime = doc.attachment_id.mimetype
                if mime.startswith('image/'):
                    doc.document_type = 'image'
                elif mime == 'application/pdf':
                    doc.document_type = 'pdf'
                elif mime in [
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                ]:
                    doc.document_type = 'document'
                else:
                    doc.document_type = 'other'
            else:
                doc.document_type = 'other'

    @api.depends('attachment_id', 'attachment_id.file_size')
    def _compute_file_size(self):
        for doc in self:
            if doc.attachment_id and doc.attachment_id.file_size:
                doc.file_size = doc.attachment_id.file_size
            else:
                doc.file_size = 0

    @api.depends('attachment_id', 'attachment_id.name')
    def _compute_file_extension(self):
        for doc in self:
            if doc.attachment_id and doc.attachment_id.name:
                parts = doc.attachment_id.name.split('.')
                doc.file_extension = parts[-1].upper() if len(parts) > 1 else ''
            else:
                doc.file_extension = ''
    
    def action_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }
    
    def action_delete(self):
        self.attachment_id.unlink()
        self.unlink()