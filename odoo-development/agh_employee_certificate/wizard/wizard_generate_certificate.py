# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class WizardGenerateCertificate(models.TransientModel):
    _name = 'wizard.generate.certificate'
    _description = 'Assistant de génération d\'attestation'

    employee_id = fields.Many2one('hr.employee', string='Employé', required=True)
    certificate_type = fields.Selection([
        ('ATT_TRAVAIL', 'Attestation de Travail'),
        ('ATT_SALAIRE', 'Attestation de Salaire'),
        ('ATT_STAGE', 'Attestation de Stage'),
        ('ATT_CONGE', 'Attestation de Congé'),
        ('PEC', 'Prise en Charge'),
        ('ATT_FIN', 'Attestation de Fin de Contrat'),
    ], string='Type', required=True)
    template_id = fields.Many2one(
        'hr.certificate.template', string='Modèle',
        domain="[('certificate_type', '=', certificate_type), ('active', '=', True)]",
    )
    language = fields.Selection([
        ('fr_FR', 'Français'),
        ('ar_001', 'Arabe'),
    ], string='Langue', default='fr_FR')
    signature_image = fields.Binary(string='Signature (optionnel)', attachment=True)
    send_email = fields.Boolean(string='Envoyer par email', default=False)
    # Leave dates (visible only for ATT_CONGE)
    leave_date_start = fields.Date(string='Début de congé')
    leave_date_end = fields.Date(string='Fin de congé')

    def action_generate(self):
        self.ensure_one()
        cert_vals = {
            'employee_id': self.employee_id.id,
            'certificate_type': self.certificate_type,
            'signature_image': self.signature_image,
            'signature_name': self.env.user.name,
            'state': 'requested',
            'requested_by_id': self.env.user.id,
            'leave_date_start': self.leave_date_start,
            'leave_date_end': self.leave_date_end,
        }
        certificate = self.env['hr.certificate'].create(cert_vals)
        certificate.generate_pdf()
        # Removal of automatic validate and email send to force admin approval
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.certificate',
            'res_id': certificate.id,
            'view_mode': 'form',
            'target': 'current',
        }
