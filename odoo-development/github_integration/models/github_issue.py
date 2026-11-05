from odoo import models, fields
import requests

class GithubIssue(models.Model):
    _name = 'agh.github.issue'
    _description = 'GitHub Issue (Sovereign)'

    name = fields.Char('Titre', required=True)
    number = fields.Integer('Numéro')
    state = fields.Selection([('open', 'Ouverte'), ('closed', 'Fermée')], default='open')
    body = fields.Text('Description')
    repository_id = fields.Many2one('agh.github.repository', string='Repository')
    task_id = fields.Many2one('project.task', string='Tâche liée')
    comment_ids = fields.One2many('agh.github.comment', 'issue_id', string='Commentaires')

    def sync_comments(self, headers, repo_name, session=None):
        self.ensure_one()
        page = 1
        s = session or requests.Session()
        while True:
            url = f'https://api.github.com/repos/{repo_name}/issues/{self.number}/comments?page={page}&per_page=100'
            r = s.get(url, headers=headers, timeout=10)
            if r.status_code != 200 or not r.json():
                break
            for c in r.json():
                github_id_str = str(c['id'])
                existing = self.env['agh.github.comment'].search([('github_id', '=', github_id_str)])
                if not existing:
                    self.env['agh.github.comment'].create({
                        'github_id': github_id_str,
                        'author': c['user']['login'],
                        'body': c['body'],
                        'date': c['created_at'],
                        'issue_id': self.id,
                    })
            page += 1
