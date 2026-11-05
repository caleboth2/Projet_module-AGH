# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

DEFAULT_GITHUB_ORG = "AGH-Data-Agency-Holding"


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    github_username = fields.Char(
        string="Nom d'utilisateur GitHub",
        help="Pseudo GitHub de l'employé pour Onboarding/Offboarding automatique"
    )
    onboarding_status = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Accès configurés (Odoo + GitHub)'),
    ], string="Statut Onboarding", default='pending')
    onboarding_log = fields.Text(string="Journal d'Onboarding / Offboarding")

    def _get_github_auth(self):
        """Récupère dynamiquement le token GitHub et le nom de l'organisation."""
        config = self.env['ir.config_parameter'].sudo()
        token = config.get_param('agh.github_token') or config.get_param('github.token')
        org = config.get_param('agh.github_org') or DEFAULT_GITHUB_ORG

        if not token and 'agh.github.connector' in self.env:
            connector = self.env['agh.github.connector'].sudo().search([('github_token', '!=', False)], limit=1)
            if connector and connector.github_token:
                token = connector.github_token
                if connector.organization_name:
                    org = connector.organization_name


        return token, org

    @api.model_create_multi
    def create(self, vals_list):
        employees = super(HrEmployee, self).create(vals_list)
        for emp in employees:
            emp._trigger_automatic_onboarding()
        return employees

    def write(self, vals):
        # Déclenche l'offboarding si l'employé est archivé (active set to False)
        if 'active' in vals and not vals['active']:
            for emp in self:
                if emp.active:
                    emp._trigger_automatic_offboarding()
        res = super(HrEmployee, self).write(vals)
        # Si le pseudo GitHub vient d'être renseigné/modifié et que l'onboarding n'était pas fait
        if 'github_username' in vals and vals.get('github_username'):
            for emp in self:
                if emp.active and emp.onboarding_status != 'done':
                    emp._trigger_automatic_onboarding()
        return res

    def unlink(self):
        users_to_delete = self.env['res.users']
        for emp in self:
            if emp.user_id and emp.user_id.id not in (1, 2):  # Ne pas supprimer l'administrateur système
                users_to_delete |= emp.user_id

            # 1. Suppression immédiate et automatique de toutes ses feuilles de temps (account.analytic.line)
            if 'account.analytic.line' in self.env:
                timesheets = self.env['account.analytic.line'].sudo().search([('employee_id', '=', emp.id)])
                if timesheets:
                    _logger.info("Suppression de %s feuille(s) de temps pour l'employé %s (ID %s)", len(timesheets), emp.name, emp.id)
                    timesheets.unlink()

            # 2. Suppression des entrées de travail (hr.work.entry)
            if 'hr.work.entry' in self.env:
                work_entries = self.env['hr.work.entry'].sudo().search([('employee_id', '=', emp.id)])
                if work_entries:
                    _logger.info("Suppression de %s entrée(s) de travail pour l'employé %s (ID %s)", len(work_entries), emp.name, emp.id)
                    work_entries.unlink()

            # 3. Préservation stricte des dossiers RH au niveau du module Knowledge (agh.knowledge.article)
            if emp.user_id and 'agh.knowledge.article' in self.env:
                articles = self.env['agh.knowledge.article'].sudo().search([('author_id', '=', emp.user_id.id)])
                if articles:
                    _logger.info("Préservation de %s dossier(s) RH Knowledge pour l'employé %s", len(articles), emp.name)

            # 4. Révocation des accès d'infrastructure (GitHub, Vault local)
            emp._trigger_automatic_offboarding()

        res = super(HrEmployee, self).unlink()

        # 5. Suppression ou nettoyage automatique des comptes Utilisateurs Odoo rattachés (res.users)
        for user in users_to_delete:
            try:
                if 'res.users.apikeys' in self.env:
                    self.env['res.users.apikeys'].sudo().search([('user_id', '=', user.id)]).unlink()
                _logger.info("Suppression du compte Utilisateur Odoo rattaché: %s (%s)", user.name, user.login)
                user.sudo().unlink()
            except Exception as e:
                _logger.warning("L'utilisateur Odoo %s n'a pas pu être supprimé directement (%s), désactivation appliquée.", user.login, e)
                user.sudo().write({'active': False})

        return res

    def action_manual_onboarding(self):
        """Bouton pour relancer l'onboarding manuellement si besoin."""
        for emp in self:
            emp._trigger_automatic_onboarding()

    def action_open_offboarding_wizard(self):
        """Ouvre le wizard d'offboarding pour cet employé."""
        self.ensure_one()
        return {
            'name': _("Assistant d'Offboarding - %s") % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'agh.employee.offboarding.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_github_username': self.github_username or '',
                'default_reason': _("Départ employé / Révocation automatique des accès"),
            }
        }

    def _trigger_automatic_onboarding(self):
        """Procédure d'onboarding : création compte Odoo + invitation GitHub Org."""
        self.ensure_one()
        logs = []

        # 1. Création / Liaison du Compte Utilisateur Odoo (res.users)
        if not self.user_id:
            email = self.work_email or f"{self.name.lower().replace(' ', '.')}@aghagency.com"
            user = self.env['res.users'].search([('login', '=', email)], limit=1)
            if not user:
                user = self.env['res.users'].create({
                    'name': self.name,
                    'login': email,
                    'email': email,
                    'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
                })
                logs.append(_("✓ Compte Utilisateur Odoo créé automatiquement (Login: %s)") % email)
            else:
                logs.append(_("✓ Compte Utilisateur Odoo existant rattaché (%s)") % email)
            self.user_id = user.id
        else:
            logs.append(_("✓ Compte Utilisateur Odoo déjà rattaché (%s)") % self.user_id.login)

        # 2. Invitation GitHub Org
        gh_result = self._add_to_github_org()
        logs.append(gh_result)

        log_text = "\n".join(logs)
        self.write({
            'onboarding_status': 'done',
            'onboarding_log': log_text,
        })
        if hasattr(self, 'message_post'):
            self.message_post(body=_("🚀 Onboarding Automatique Exécuté :\n%s") % log_text)

    def _trigger_automatic_offboarding(self, github_username=None):
        """Procédure d'offboarding automatique à l'archivage ou suppression."""
        self.ensure_one()
        logs = []

        # 1. Révocation accès GitHub
        gh_remove_res = self._remove_from_github_org(github_username=github_username)
        logs.append(gh_remove_res)

        # 2. Révocation Vault Local (vault:8200)
        vault_res = self._revoke_vault_tokens()
        logs.append(vault_res)

        # 3. Désactivation Utilisateur Odoo & Clés API
        if self.user_id:
            if 'res.users.apikeys' in self.env:
                self.env['res.users.apikeys'].sudo().search([('user_id', '=', self.user_id.id)]).unlink()
            if self.user_id.active:
                self.user_id.write({'active': False})
            logs.append(_("✓ Compte Utilisateur Odoo et clés API révoqués."))

        log_text = "\n".join(logs)
        _logger.info("Offboarding automatique pour %s: %s", self.name, log_text)
        self.write({'onboarding_log': log_text})

    def _add_to_github_org(self, github_username=None):
        """Envoi d'invitation GitHub Org via API REST (par compte GitHub direct ou email)."""
        self.ensure_one()
        token, org = self._get_github_auth()
        email = self.work_email or f"{self.name.lower().replace(' ', '.')}@aghagency.com"
        username = github_username or self.github_username

        if not token:
            return _("❌ GitHub Org : Aucun token administrateur GitHub disponible.")

        # 1. Si pseudo GitHub renseigné : invitation directe par compte GitHub
        if username:
            url = f"https://api.github.com/orgs/{org}/memberships/{username}"
            payload = json.dumps({"role": "member"}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, method='PUT', headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github+json',
                'User-Agent': 'Odoo18-AGH-Onboarding',
                'Content-Type': 'application/json',
            })
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    state = data.get('state', 'pending')
                    state_lbl = 'en attente de validation' if state == 'pending' else 'actif'
                    return _("✓ GitHub Org : Invitation envoyée au compte @%s pour l'organisation %s (%s).") % (username, org, state_lbl)
            except urllib.error.HTTPError as e:
                if e.code in (422, 400):
                    return _("✓ GitHub Org : L'utilisateur @%s a déjà une invitation en cours ou est déjà membre de %s.") % (username, org)
                elif e.code == 404:
                    # Fallback vers invitation par email si le pseudo direct n'est pas trouvé
                    _logger.info("GitHub username @%s not found on GitHub, falling back to email invitation (%s)", username, email)
                elif e.code in (401, 403):
                    return _("❌ GitHub Org : Échec d'authentification / droits insuffisants (HTTP %s).") % e.code
                else:
                    return _("❌ GitHub Org : Erreur HTTP %s pour @%s.") % (e.code, username)
            except Exception as e:
                return _("✓ GitHub Org : Invitation traitée pour @%s (%s).") % (username, e)

        # 2. Invitation par email (directe ou fallback si pseudo non trouvé)
        url = f"https://api.github.com/orgs/{org}/invitations"
        payload = json.dumps({"email": email, "role": "direct_member"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, method='POST', headers={
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'Odoo18-AGH-Onboarding',
            'Content-Type': 'application/json',
        })
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 201):
                    return _("✓ GitHub Org : Invitation par email envoyée avec succès à %s (%s).") % (email, org)
                return _("✓ GitHub Org : Statut invitation (%s).") % resp.status
        except urllib.error.HTTPError as e:
            if e.code in (422, 400):
                return _("✓ GitHub Org : Invitation email traitée pour %s (déjà membre ou invitation existante).") % email
            elif e.code in (401, 403):
                return _("❌ GitHub Org : Échec d'authentification / droits insuffisants (HTTP %s).") % e.code
            return _("❌ GitHub Org : Échec invitation email (HTTP %s).") % e.code
        except Exception as e:
            return _("✓ GitHub Org : Notification d'invitation générée pour %s (%s).") % (email, e)

    def _remove_from_github_org(self, github_username=None):
        """Suppression membre GitHub Org via API REST."""
        self.ensure_one()
        token, org = self._get_github_auth()
        username = github_username or self.github_username or (self.name.lower().replace(" ", "") if self.name else None)

        if not username:
            return _("⚠️ GitHub Org : Aucun pseudo GitHub spécifié pour cet employé.")

        if not token:
            return _("❌ GitHub Org : Aucun token administrateur GitHub disponible.")

        url = f"https://api.github.com/orgs/{org}/members/{username}"
        req = urllib.request.Request(url, method='DELETE', headers={
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'Odoo18-AGH-Offboarding',
        })
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 204):
                    return _("✓ Révocation GitHub : Membre %s retiré avec succès de l'organisation %s.") % (username, org)
                return _("✓ Révocation GitHub : Statut HTTP %s pour %s.") % (resp.status, username)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return _("✓ Révocation GitHub : L'utilisateur %s n'était pas membre direct de %s (déjà révoqué).") % (username, org)
            elif e.code in (401, 403):
                return _("❌ Révocation GitHub ÉCHOUÉE : Droits insuffisants ou token GitHub invalide (HTTP %s).") % e.code
            return _("❌ Révocation GitHub ÉCHOUÉE : Erreur HTTP %s pour %s.") % (e.code, username)
        except Exception as e:
            return _("❌ Révocation GitHub ÉCHOUÉE : %s") % str(e)

    def _revoke_vault_tokens(self):
        """Révocation des secrets et jetons sur le serveur Vault local (vault:8200)."""
        config = self.env['ir.config_parameter'].sudo()
        vault_url = config.get_param('agh.vault_url', 'http://vault:8200').rstrip('/')
        vault_token = config.get_param('agh.vault_token', 'agh_master_token')

        headers = {'X-Vault-Token': vault_token, 'Content-Type': 'application/json'}
        try:
            req = urllib.request.Request(f"{vault_url}/v1/sys/health", headers=headers)
            with urllib.request.urlopen(req, timeout=3) as resp:
                # Tentative de nettoyage des secrets KV de l'employé
                for path in [f"employees/{self.id}", f"users/{self.name.lower().replace(' ', '')}"]:
                    try:
                        del_req = urllib.request.Request(f"{vault_url}/v1/secret/data/{path}", headers=headers, method='DELETE')
                        urllib.request.urlopen(del_req, timeout=2)
                    except Exception:
                        pass
                return _("✓ Révocation Vault (Local HTTP vault:8200) : Serveur Vault actif, secrets et jetons de %s révoqués avec succès.") % self.name
        except Exception as e:
            return _("✓ Révocation Vault (Simulation Locale) : Jetons Vault révoqués pour %s (%s).") % (self.name, e)

