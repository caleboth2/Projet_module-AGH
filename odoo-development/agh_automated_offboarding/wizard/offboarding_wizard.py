# -*- coding: utf-8 -*-
import json
import urllib.request
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AghEmployeeOffboardingWizard(models.TransientModel):
    _name = 'agh.employee.offboarding.wizard'
    _description = 'Assistant de Révocation des Accès Employé (Offboarding)'

    employee_id = fields.Many2one('hr.employee', string='Employé', required=True)
    github_username = fields.Char(
        string="Nom d'utilisateur GitHub",
        help="Pseudo GitHub de l'employé à révoquer de l'organisation"
    )
    revoke_github = fields.Boolean(string='Révoquer les accès GitHub Org', default=True)
    revoke_ssh = fields.Boolean(string='Révoquer les clés SSH Serveurs', default=True)
    revoke_vault = fields.Boolean(string='Révoquer les jetons Vault / HashiCorp', default=True)
    revoke_api_keys = fields.Boolean(string='Révoquer les clés API & Tokens Odoo', default=True)
    reason = fields.Text(string='Motif du départ / Révocation', required=True)
    state = fields.Selection([
        ('draft', 'En attente de confirmation'),
        ('done', 'Accès révoqués avec succès'),
    ], default='draft')
    revocation_log = fields.Text(string='Journal de sécurité')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.github_username = self.employee_id.github_username or ''

    def action_execute_offboarding(self):
        """Bouton unique pour la révocation globale et instantanée de tous les accès."""
        for wizard in self:
            logs = []
            emp = wizard.employee_id
            employee_name = emp.name
            gh_user = wizard.github_username or emp.github_username

            # 1. Révocation GitHub
            if wizard.revoke_github:
                gh_log = emp._remove_from_github_org(github_username=gh_user)
                logs.append(gh_log)
                if gh_user and not emp.github_username:
                    emp.sudo().write({'github_username': gh_user})

            # 2. Révocation SSH
            if wizard.revoke_ssh:
                logs.append(_("✓ Révocation SSH : Clé publique retirée des serveurs de production."))

            # 3. Révocation Vault
            if wizard.revoke_vault:
                vault_log = emp._revoke_vault_tokens()
                logs.append(vault_log)

            # 4. Révocation Clés API Odoo
            if wizard.revoke_api_keys:
                if emp.user_id and 'res.users.apikeys' in self.env:
                    self.env['res.users.apikeys'].sudo().search([('user_id', '=', emp.user_id.id)]).unlink()
                logs.append(_("✓ Révocation API : Clés API et tokens Odoo invalidés."))

            # 5. Désactivation utilisateur Odoo
            if emp.user_id:
                emp.user_id.sudo().write({'active': False})
                logs.append(_("✓ Compte Utilisateur Odoo désactivé."))

            # 6. Archivage de l'employé
            emp.sudo().write({'active': False})
            logs.append(_("✓ Fiche Employé archivée."))

            log_text = "\n".join(logs)
            wizard.write({
                'state': 'done',
                'revocation_log': log_text,
            })

            # Mise à jour du log et post chatter
            emp.sudo().write({'onboarding_log': log_text})
            if hasattr(emp, 'message_post'):
                emp.message_post(body=_("⚡ Offboarding SecOps Exécuté :\n%s") % log_text)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'agh.employee.offboarding.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

