import requests
import logging
from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class MobileApp(models.Model):
    _name = 'mobile.app'
    _description = 'Configuration Application Mobile'

    name = fields.Char(string='Nom de l\'App', required=True)
    github_repo = fields.Char(string='Dépôt GitHub (orga/repo)', required=True)
    vault_key_name = fields.Char(string='Nom de la clé Vault', required=True, help="Nom de la clé de transit dans Vault pour cette application.")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('github_repo_unique', 'unique(github_repo)', 'Ce dépôt GitHub est déjà configuré !')
    ]

    def action_sync_from_github(self):
        """ Synchronise les dépôts de l'organisation GitHub AGH """
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('agh_mobile_signer.github_token')
        proxy_url = params.get_param('agh_mobile_signer.tor_proxy_url')
        
        # On force l'URL Tor interne si on est dans Docker
        if not proxy_url or '127.0.0.1' in proxy_url:
            proxy_url = 'socks5h://tor:9050'

        proxies = {'http': proxy_url, 'https': proxy_url}
        org_name = "AGH-Data-Agency-Holding"
        github_url = f"https://api.github.com/orgs/{org_name}/repos"
        
        headers = {
            "Accept": "application/vnd.github+json"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = requests.get(github_url, headers=headers, proxies=proxies, timeout=30)
            if response.status_code == 200:
                repos = response.json()
                count = 0
                for repo in repos:
                    # Ne pas importer le repo d'infra lui-même
                    if repo['name'] == 'odoo-development':
                        continue
                        
                    full_name = repo['full_name']
                    existing = self.search([('github_repo', '=', full_name)])
                    if not existing:
                        self.create({
                            'name': repo['name'].replace('-', ' ').title(),
                            'github_repo': full_name,
                            'vault_key_name': repo['name'].replace('-', '_'),
                        })
                        count += 1
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Synchronisation réussie'),
                        'message': _('%s nouvelles applications importées.') % count,
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_("Erreur GitHub API (%s) : %s") % (response.status_code, response.text))
        except Exception as e:
            raise UserError(_("Erreur lors de la synchronisation via Tor : %s") % str(e))

    def action_view_sign_requests(self):
        self.ensure_one()
        return {
            'name': _('Demandes de signature'),
            'type': 'ir.actions.act_window',
            'res_model': 'mobile.sign.request',
            'view_mode': 'list,form',
            'domain': [('app_id', '=', self.id)],
            'context': {'default_app_id': self.id},
        }

    def fetch_sync_from_app(self):
        self.ensure_one()
        self.env['mobile.sign.request'].fetch_latest_build_from_github()
        return self.action_view_sign_requests()
