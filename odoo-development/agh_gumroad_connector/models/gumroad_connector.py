from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class AghGumroadConnector(models.Model):
    _name = 'agh.gumroad.connector'
    _description = 'AGH Gumroad Connector'
    _order = 'name'

    name = fields.Char('Nom', required=True)
    access_token = fields.Char('Access Token', required=True)
    last_sync = fields.Datetime('Dernière Synchronisation', readonly=True)
    status = fields.Selection([
        ('connected', 'Connecté'),
        ('disconnected', 'Déconnecté'),
        ('error', 'Erreur'),
    ], string='Statut', default='disconnected', readonly=True)

    gumroad_user_email = fields.Char('Email Gumroad', readonly=True)
    gumroad_user_name = fields.Char('Nom Gumroad', readonly=True)

    def action_test_connection(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError(_("Veuillez saisir un Access Token avant de tester la connexion."))

        headers = {'Authorization': f'Bearer {self.access_token}'}
        try:
            r = requests.get('https://api.gumroad.com/v2/user', headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                user_data = data.get('user', {})
                self.write({
                    'status': 'connected',
                    'last_sync': fields.Datetime.now(),
                    'gumroad_user_email': user_data.get('email', ''),
                    'gumroad_user_name': user_data.get('name', ''),
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connexion réussie'),
                        'message': _("Connecté en tant que : %s") % user_data.get('email', 'Inconnu'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                self.write({'status': 'error'})
                raise UserError(_("Erreur de connexion Gumroad (HTTP %s). Vérifiez votre Access Token.") % r.status_code)
        except requests.exceptions.Timeout:
            self.write({'status': 'error'})
            raise UserError(_("Délai d'attente dépassé."))
        except requests.exceptions.ConnectionError:
            self.write({'status': 'error'})
            raise UserError(_("Impossible de contacter l'API Gumroad."))
        except UserError:
            raise
        except Exception as e:
            _logger.exception("Gumroad connection error: %s", e)
            self.write({'status': 'error'})
            raise UserError(_("Erreur inattendue : %s") % str(e))

    def action_disconnect(self):
        self.ensure_one()
        self.write({
            'status': 'disconnected',
            'gumroad_user_email': False,
            'gumroad_user_name': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Déconnexion'),
                'message': _('Le connecteur a été déconnecté.'),
                'type': 'warning',
                'sticky': False,
            }
        }
