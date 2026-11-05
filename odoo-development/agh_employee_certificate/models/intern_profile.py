# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api
from odoo.exceptions import UserError


class InternProfile(models.Model):
    _name = 'intern.profile'
    _description = 'Stagiaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # =========================
    # Informations stagiaire
    # =========================
    name = fields.Char("Nom stagiaire", required=True, tracking=True)
    cine = fields.Char("CINE", tracking=True)
    email = fields.Char("Email", tracking=True)

    start_date = fields.Date("Date début")
    end_date = fields.Date("Date fin")

    stage_type = fields.Selection([
        ('pfe', 'Stage PFE'),
        ('pre', 'Stage pré embauche'),
        ('stage', 'Stage de 3 mois'),
    ], string="Type de stage")

    city = fields.Char("Ville")

    # =========================
    # Informations entreprise
    # =========================
    company_name = fields.Char(
        string="Entreprise",
        default="AGH DATA AGENCY HOLDING SA",
    )
    supervisor = fields.Char(
        string="Signataire",
        default="Amine El Ghobari",
    )
    supervisor_job = fields.Char(
        string="Fonction signataire",
        default="Chief Executive Officer",
    )

    # =========================
    # Attestation
    # =========================
    attestation_number = fields.Char(
        string="Numéro d'attestation",
        readonly=True, copy=False, default="AUTO",
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé'),
        ('sent', 'Envoyé'),
    ], string="Statut", default='draft', tracking=True)

    # =========================
    # Création automatique numéro
    # =========================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('attestation_number', 'AUTO') == 'AUTO':
                vals['attestation_number'] = self.env['ir.sequence'].next_by_code(
                    'intern.attestation'
                ) or 'ATT/000'
        return super().create(vals_list)

    # =========================
    # Boutons
    # =========================
    def action_validate(self):
        for rec in self:
            rec.state = 'validated'

    def action_print_attestation(self):
        report = self.env.ref(
            'agh_employee_certificate.action_report_attestation',
            raise_if_not_found=False,
        )
        if not report:
            raise UserError("Le rapport PDF est introuvable.")
        return report.report_action(self)

    def action_send_email(self):
        for rec in self:
            rec.send_attestation_email()
            rec.state = 'sent'

    # =========================
    # Génération PDF + Email
    # =========================
    def send_attestation_email(self):
        self.ensure_one()
        if not self.email:
            raise UserError("Veuillez renseigner l'email du stagiaire.")

        report = self.env.ref(
            'agh_employee_certificate.action_report_attestation',
            raise_if_not_found=False,
        )
        if not report:
            raise UserError("Rapport PDF introuvable.")

        pdf_content, _ = report._render_qweb_pdf(
            'agh_employee_certificate.action_report_attestation',
            [self.id],
        )

        attachment = self.env['ir.attachment'].create({
            'name': f'{self.attestation_number}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'intern.profile',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        mail = self.env['mail.mail'].create({
            'subject': 'Votre Attestation de Stage',
            'body_html': (
                f"<p>Bonjour {self.name},</p>"
                "<p>Veuillez trouver ci-joint votre attestation de stage.</p>"
                "<p>Cordialement,</p>"
                "<p>AGH DATA AGENCY HOLDING SA</p>"
            ),
            'email_to': self.email,
            'attachment_ids': [(6, 0, [attachment.id])],
        })
        mail.send()

    # =========================
    # CRON : envoi automatique fin stage
    # =========================
    @api.model
    def cron_send_attestations(self):
        interns = self.search([
            ('end_date', '<=', fields.Date.today()),
            ('state', '=', 'validated'),
            ('email', '!=', False),
        ])
        for rec in interns:
            try:
                rec.send_attestation_email()
                rec.state = 'sent'
            except Exception:
                pass
