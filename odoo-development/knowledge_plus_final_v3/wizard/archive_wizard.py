from odoo import models, fields, api
from datetime import datetime

class KnowledgeArchiveWizard(models.TransientModel):
    _name = 'knowledge.archive.wizard'
    _description = 'Assistant d\'archivage'

    article_ids = fields.Many2many('agh.knowledge.article', string='Articles à archiver')
    article_count = fields.Integer(string='Nombre d\'articles')
    archive_reason = fields.Text(string='Motif d\'archivage', required=True)
    permanent_delete = fields.Boolean(string='Suppression définitive', default=False)
    
    def action_archive(self):
        if self.permanent_delete:
            self.article_ids.unlink()
        else:
            self.article_ids.write({
                'active': False,
                'state': 'archived',
                'archive_reason': self.archive_reason,
                'archived_by': self.env.user.id,
                'archive_date': datetime.now()
            })
        return {'type': 'ir.actions.act_window_close'}


class KnowledgeDeleteWizard(models.TransientModel):
    _name = 'knowledge.delete.wizard'
    _description = 'Assistant de suppression définitive'

    article_ids = fields.Many2many('agh.knowledge.article', string='Articles à supprimer')
    article_count = fields.Integer(string='Nombre d\'articles')
    confirm_text = fields.Char(string='Tapez "SUPPRIMER" pour confirmer', required=True)
    
    @api.constrains('confirm_text')
    def _check_confirm_text(self):
        for record in self:
            if record.confirm_text and record.confirm_text.upper() != 'SUPPRIMER':
                raise models.ValidationError('Veuillez taper "SUPPRIMER" pour confirmer la suppression définitive')
    
    def action_delete_permanent(self):
        if self.confirm_text.upper() == 'SUPPRIMER':
            self.article_ids.unlink()
        return {'type': 'ir.actions.act_window_close'}