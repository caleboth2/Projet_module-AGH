# -*- coding: utf-8 -*-
from odoo import fields, models


class HrCertificateTemplate(models.Model):
    _name = 'hr.certificate.template'
    _description = 'Certificate Template'
    _rec_name = 'name'

    name = fields.Char(string='Nom du modèle', required=True, translate=True)
    certificate_type = fields.Selection([
        ('ATT_TRAVAIL', 'Attestation de Travail'),
        ('ATT_SALAIRE', 'Attestation de Salaire'),
        ('ATT_STAGE', 'Attestation de Stage'),
        ('ATT_CONGE', 'Attestation de Congé'),
        ('PEC', 'Prise en Charge'),
        ('ATT_FIN', 'Attestation de Fin de Contrat'),
    ], string='Type', required=True)
    language = fields.Selection([
        ('fr_FR', 'Français'),
        ('ar_001', 'Arabe'),
    ], string='Langue', default='fr_FR')
    report_template_id = fields.Many2one('ir.actions.report', string='Rapport', required=True)
    email_subject = fields.Char(
        string='Objet email', required=True, translate=True,
        default='Votre attestation est prête',
    )
    email_body = fields.Html(
        string='Corps email', translate=True,
        default='<p>Cher(e) employé(e),</p><p>Veuillez trouver ci-joint votre attestation.</p>',
    )
    active = fields.Boolean(default=True)
