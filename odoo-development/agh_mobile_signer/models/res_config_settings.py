from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    agh_tor_proxy_url = fields.Char(
        string='URL Proxy Tor',
        config_parameter='agh_mobile_signer.tor_proxy_url',
        default='socks5h://127.0.0.1:9050'
    )
    agh_vault_url = fields.Char(
        string='URL Coffre-fort (Vault)',
        config_parameter='agh_mobile_signer.vault_url'
    )
    agh_vault_token = fields.Char(
        string='Token Vault',
        config_parameter='agh_mobile_signer.vault_token'
    )
    agh_github_token = fields.Char(
        string='Token GitHub',
        config_parameter='agh_mobile_signer.github_token'
    )
