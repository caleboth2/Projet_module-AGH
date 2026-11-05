import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class MobileSignRequest(models.Model):
    _name = 'mobile.sign.request'
    _description = 'Demande de Signature Mobile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    app_id = fields.Many2one('mobile.app', string='Application', required=True, ondelete='cascade', tracking=True)
    name = fields.Char(related='app_id.name', string='Nom de l\'App', store=True, readonly=True)
    version = fields.Char(string='Version / Commit SHA', required=True, tracking=True)
    file_hash = fields.Char(string='Hash SHA-256', tracking=True)
    github_artifact_id = fields.Char(string='ID Artefact GitHub', readonly=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En attente d\'approbation'),
        ('signed', 'Signé'),
        ('rejected', 'Refusé')
    ], default='draft', string='État', tracking=True)

    def _get_tor_proxies(self):
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('agh_mobile_signer.tor_proxy_url')
        if not proxy_url:
            return None
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    def fetch_latest_build_from_github(self):
        """ Récupère les builds depuis GitHub Actions via Tor pour TOUTES les applications """
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('agh_mobile_signer.github_token')
        proxies = self._get_tor_proxies()
        count = 0

        if not token:
            _logger.warning("Token GitHub manquant dans la configuration.")
            return

        active_apps = self.env['mobile.app'].search([('active', '=', True)])
        
        for app in active_apps:
            github_url = f"https://api.github.com/repos/{app.github_repo}/actions/artifacts"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }

            try:
                response = requests.get(github_url, headers=headers, proxies=proxies, timeout=30)
                if response.status_code == 200:
                    artifacts = response.json().get('artifacts', [])
                    for art in artifacts:
                        if art['name'].endswith('-build-info'):
                            existing = self.search([
                                ('github_artifact_id', '=', str(art['id'])),
                                ('app_id', '=', app.id)
                            ])
                            if not existing:
                                self.create({
                                    'app_id': app.id,
                                    'version': art['workflow_run']['head_sha'][:7] if 'workflow_run' in art else 'N/A',
                                    'github_artifact_id': str(art['id']),
                                    'state': 'pending',
                                    'file_hash': 'HASH_A_EXTRAIRE', 
                                })
                                count += 1
                                _logger.info(f"Nouveau build détecté pour {app.name} : {art['name']}")
                else:
                    _logger.error(f"Erreur GitHub API pour {app.name} ({app.github_repo}): {response.status_code}")
            except Exception as e:
                _logger.error(f"Erreur lors de la récupération GitHub pour {app.name} via Tor : {str(e)}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronisation terminée'),
                'message': _('%s nouveaux builds ont été récupérés.') % count,
                'sticky': False,
                'type': 'success',
            }
        }

    def action_approve_and_sign(self):
        """ Approuve et demande la signature au Vault local via Tor """
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        vault_url = params.get_param('agh_mobile_signer.vault_url')
        vault_token = params.get_param('agh_mobile_signer.vault_token')
        proxies = self._get_tor_proxies()

        if not vault_url or not vault_token:
            raise UserError(_("Configuration du coffre-fort manquante."))

        if not self.file_hash:
            raise UserError(_("Le hash du fichier est requis pour la signature."))

        # Utilisation de la clé spécifique à l'application
        vault_key = self.app_id.vault_key_name
        
        payload = {
            "hash": self.file_hash,
            "key_name": vault_key,
            "version": self.version
        }
        headers = {"X-Vault-Token": vault_token}

        try:
            # Appel au coffre-fort sur l'endpoint de transit (SANS PROXY Tor)
            response = requests.post(
                f"{vault_url}/v1/transit/sign/{vault_key}", 
                json=payload, 
                headers=headers, 
                timeout=30
            )
            
            if response.status_code == 200:
                signature_data = response.json().get('data', {}).get('signature', 'N/A')
                log_message = _(
                    "<b>Signature effectuée avec succès</b><br/>"
                    "• Application : %s<br/>"
                    "• Clé Vault : %s<br/>"
                    "• Utilisateur : %s<br/>"
                    "• Signature : %s"
                ) % (self.app_id.name, vault_key, self.env.user.name, signature_data[:30] + '...')
                
                self.message_post(body=log_message)
                self.state = 'signed'
            else:
                raise UserError(_("Le coffre-fort a refusé la signature : %s") % response.text)
        except Exception as e:
            raise UserError(_("Erreur de connexion au coffre-fort via Tor : %s") % str(e))

    def action_reject(self):
        self.write({'state': 'rejected'})
        self.message_post(body=_("Demande de signature rejetée."))

    @api.model
    def _cron_fetch_github_builds(self):
        """ Point d'entrée pour la tâche planifiée """
        self.fetch_latest_build_from_github()
