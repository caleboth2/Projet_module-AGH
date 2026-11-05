from odoo import models, fields
import requests

class GithubPullRequest(models.Model):
    _name = 'agh.github.pull_request'
    _description = 'GitHub Pull Request (Sovereign)'

    name = fields.Char('Titre', required=True)
    number = fields.Integer('Numéro')
    state = fields.Selection([
        ('open', 'Ouverte'),
        ('closed', 'Fermée'),
        ('merged', 'Fusionnée'),
    ], default='open')
    body = fields.Text('Description')
    repository_id = fields.Many2one('agh.github.repository', string='Repository')
    task_id = fields.Many2one('project.task', string='Tâche liée')
    html_url = fields.Char('URL')
    comment_ids = fields.One2many('agh.github.comment', 'pr_id', string='Commentaires')

    def sync_comments(self, headers, repo_name, session=None):
        self.ensure_one()
        # GitHub traite les commentaires de PR comme des issues
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
                        'pr_id': self.id,
                    })
            page += 1
