from odoo import models, fields

class GithubCommit(models.Model):
    _name = 'agh.github.commit'
    _description = 'GitHub Commit (Sovereign)'

    name = fields.Char('Message', required=True)
    sha = fields.Char('SHA')
    author = fields.Char('Auteur')
    date = fields.Char('Date')
    repository_id = fields.Many2one('agh.github.repository', string='Repository')
    task_id = fields.Many2one('project.task', string='Tâche liée')
