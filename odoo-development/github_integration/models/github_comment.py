from odoo import models, fields

class GithubComment(models.Model):
    _name = 'agh.github.comment'
    _description = 'GitHub Issue/PR Comment'
    _order = 'date asc'

    github_id = fields.Char('GitHub ID')
    author = fields.Char('Auteur')
    body = fields.Text('Commentaire')
    date = fields.Char('Date')
    issue_id = fields.Many2one('agh.github.issue', string='Issue', ondelete='cascade')
    pr_id = fields.Many2one('agh.github.pull_request', string='Pull Request', ondelete='cascade')
