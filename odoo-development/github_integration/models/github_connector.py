from odoo import models, fields, api, _
import requests

class GithubConnector(models.Model):
    _name = 'agh.github.connector'
    _description = 'GitHub Connector (Sovereign)'

    name = fields.Char('Nom du Connecteur', required=True)
    github_token = fields.Char('Token GitHub', required=True)
    organization_name = fields.Char('Nom de l\'Organisation')
    repository_ids = fields.One2many('agh.github.repository', 'connector_id', string='Dépôts Importés')
    repository_count = fields.Integer(compute='_compute_repo_count')

    def _compute_repo_count(self):
        for rec in self:
            rec.repository_count = len(rec.repository_ids)

    def _get_session(self):
        s = requests.Session()
        tor_proxy = self.env['ir.config_parameter'].sudo().get_param('agh_mobile_signer.tor_proxy_url')
        if tor_proxy:
            s.proxies = {'http': tor_proxy, 'https': tor_proxy}
        return s

    def action_import_repos(self):
        self.ensure_one()
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        s = self._get_session()
        # Tente l'URL Organisation si un nom est fourni, sinon URL User
        url = f'https://api.github.com/orgs/{self.organization_name}/repos' if self.organization_name else 'https://api.github.com/user/repos'
        
        r = s.get(url, headers=headers, timeout=20)
        
        # Si 404 sur une organisation, on tente en mode "User" (cas fréquent)
        if r.status_code == 404 and self.organization_name:
            url = f'https://api.github.com/users/{self.organization_name}/repos'
            r = s.get(url, headers=headers, timeout=20)

        if r.status_code == 200:
            repos_data = r.json()
            if not isinstance(repos_data, list):
                repos_data = [repos_data]
            
            import_count = 0
            for repo in repos_data:
                existing = self.env['agh.github.repository'].search([('github_url', '=', repo['html_url'])])
                vals = {
                    'name': repo['name'],
                    'github_url': repo['html_url'],
                    'connector_id': self.id,
                    'default_branch': repo.get('default_branch', 'main'),
                }
                if not existing:
                    self.env['agh.github.repository'].create(vals)
                    import_count += 1
                else:
                    existing.write({
                        'connector_id': self.id,
                        'default_branch': repo.get('default_branch', 'main'),
                    })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Importation réussie'),
                    'message': _('%s nouveaux dépôts importés.') % import_count,
                    'sticky': False,
                }
            }
        else:
            error_msg = r.json().get('message', r.text) if r.content else "Inconnue"
            raise models.ValidationError(_("Erreur API GitHub (%s) : %s") % (r.status_code, error_msg))

    def action_sync_all(self):
        self.ensure_one()
        s = self._get_session()
        for repo in self.repository_ids:
            repo.action_sync_github(session=s)

    def action_test_connection(self):
        self.ensure_one()
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        s = self._get_session()
        try:
            r = s.get('https://api.github.com/user', headers=headers, timeout=10)
            if r.status_code == 200:
                user_data = r.json()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connexion réussie'),
                        'message': _('Connecté avec succès en tant que %s') % user_data.get('login'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = r.json().get('message', '') if r.content else 'Non autorisé'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Échec de la connexion'),
                        'message': _('Code API : %s. %s') % (r.status_code, error_msg),
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        except Exception as e:
            raise models.ValidationError(_("Erreur de connexion : %s") % str(e))
