from odoo import models, fields, api, _
import requests
import base64

class GithubRepository(models.Model):
    _name = 'agh.github.repository'
    _description = 'GitHub Repository (Sovereign)'

    name = fields.Char('Nom du repo', required=True)
    github_url = fields.Char('URL GitHub')
    github_token = fields.Char('Token Spécifique')
    project_id = fields.Many2one('project.project', string='Projet Odoo')
    connector_id = fields.Many2one('agh.github.connector', string='Connecteur Global')
    
    commit_ids = fields.One2many('agh.github.commit', 'repository_id', string='Commits')
    issue_ids = fields.One2many('agh.github.issue', 'repository_id', string='Issues')
    pull_request_ids = fields.One2many('agh.github.pull_request', 'repository_id', string='Pull Requests')
    
    commit_count = fields.Integer(compute='_compute_counts')
    issue_count = fields.Integer(compute='_compute_counts')
    pr_count = fields.Integer(compute='_compute_counts')

    # Mirroring ZIP
    zip_backup = fields.Binary('Backup ZIP Mirror', attachment=True)
    zip_filename = fields.Char('Nom du fichier ZIP')
    last_backup_date = fields.Datetime('Dernier Backup')
    default_branch = fields.Char('Branche par défaut', default='main')

    def _compute_counts(self):
        for rec in self:
            rec.commit_count = len(rec.commit_ids)
            rec.issue_count = len(rec.issue_ids)
            rec.pr_count = len(rec.pull_request_ids)

    def _get_session(self):
        if self.connector_id:
            return self.connector_id._get_session()
        s = requests.Session()
        tor_proxy = self.env['ir.config_parameter'].sudo().get_param('agh_mobile_signer.tor_proxy_url')
        if tor_proxy:
            s.proxies = {'http': tor_proxy, 'https': tor_proxy}
        return s

    def _get_token(self):
        return self.github_token or (self.connector_id.github_token if self.connector_id else False)

    def action_mirror_zip(self, session=None):
        """Télécharge le repo en ZIP pour archivage souverain."""
        self.ensure_one()
        token = self._get_token()
        if not token: return
        repo_name = self.github_url.split('github.com/')[-1]
        headers = {'Authorization': f'token {token}'}
        branch = self.default_branch or 'main'
        url = f'https://api.github.com/repos/{repo_name}/zipball/{branch}'
        
        s = session or self._get_session()
        r = s.get(url, headers=headers, timeout=60)
        if r.status_code == 200:
            zip_content = base64.b64encode(r.content)
            filename = f"{self.name}_mirror_{fields.Date.today()}.zip"
            self.write({
                'zip_backup': zip_content,
                'zip_filename': filename,
                'last_backup_date': fields.Datetime.now(),
            })
            if self.project_id:
                # Sauvegarde également en tant que pièce jointe (ir.attachment) du projet
                attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', 'project.project'),
                    ('res_id', '=', self.project_id.id),
                    ('name', '=', filename)
                ], limit=1)
                vals = {
                    'name': filename,
                    'type': 'binary',
                    'datas': zip_content,
                    'res_model': 'project.project',
                    'res_id': self.project_id.id,
                }
                if attachment:
                    attachment.write(vals)
                else:
                    self.env['ir.attachment'].create(vals)

    def action_sync_github(self, session=None):
        self.ensure_one()
        token = self._get_token()
        if not token: return
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        repo_name = self.github_url.split('github.com/')[-1]
        
        s = session or self._get_session()
        
        # 0. Sync default branch from metadata
        r_repo = s.get(f'https://api.github.com/repos/{repo_name}', headers=headers, timeout=15)
        if r_repo.status_code == 200:
            repo_info = r_repo.json()
            if isinstance(repo_info, list) and repo_info:
                repo_info = repo_info[0]
            if isinstance(repo_info, dict) and repo_info.get('default_branch'):
                self.write({'default_branch': repo_info['default_branch']})
        
        # 1. Sync commits
        r_commits = s.get(f'https://api.github.com/repos/{repo_name}/commits', headers=headers, timeout=15)
        if r_commits.status_code == 200:
            for c in r_commits.json()[:20]:
                if not self.env['agh.github.commit'].search([('sha', '=', c['sha'])]):
                    self.env['agh.github.commit'].create({
                        'name': c['commit']['message'][:200],
                        'sha': c['sha'],
                        'author': c['commit']['author']['name'],
                        'date': c['commit']['author']['date'],
                        'repository_id': self.id,
                    })

        # 2. Sync Issues & PRs (inclut commentaires, avec pagination)
        page = 1
        while True:
            r_issues = s.get(f'https://api.github.com/repos/{repo_name}/issues?state=all&page={page}&per_page=100', headers=headers, timeout=20)
            if r_issues.status_code != 200 or not r_issues.json():
                break
            for issue_data in r_issues.json():
                is_pr = 'pull_request' in issue_data
                model_name = 'agh.github.pull_request' if is_pr else 'agh.github.issue'
                
                existing = self.env[model_name].search([('repository_id', '=', self.id), ('number', '=', issue_data['number'])])
                vals = {
                    'name': issue_data['title'],
                    'number': issue_data['number'],
                    'state': issue_data['state'],
                    'repository_id': self.id,
                    'body': issue_data.get('body', '') or '',
                }
                if is_pr:
                    vals['html_url'] = issue_data['html_url']
                    if issue_data.get('pull_request', {}).get('merged_at'): vals['state'] = 'merged'

                rec = existing if existing else self.env[model_name].create(vals)
                if not existing: rec = self.env[model_name].browse(rec.id)
                else: rec.write(vals)

                # Sync Commentaires
                rec.sync_comments(headers, repo_name, session=s)
            page += 1
