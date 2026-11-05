# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrCertificate(models.Model):
    _name = 'hr.certificate'
    _description = 'Employee Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char(
        string='Certificate Number', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    certificate_type = fields.Selection([
        ('ATT_TRAVAIL', 'Attestation de Travail'),
        ('ATT_SALAIRE', 'Attestation de Salaire'),
        ('ATT_STAGE', 'Attestation de Stage'),
        ('ATT_CONGE', 'Attestation de Congé'),
        ('PEC', 'Prise en Charge'),
        ('ATT_FIN', 'Attestation de Fin de Contrat'),
    ], string='Type', required=True, tracking=True)

    employee_id = fields.Many2one('hr.employee', string='Employé', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)

    # Leave certificate dates
    leave_date_start = fields.Date(string='Début de congé')
    leave_date_end = fields.Date(string='Fin de congé')

    state = fields.Selection([
        ('requested', 'Demandé'),
        ('validated', 'Validé'),
        ('sent', 'Envoyé'),
    ], string='Statut', default='requested', tracking=True, copy=False)

    signature_image = fields.Binary(string='Signature numérique', attachment=True)
    signature_name = fields.Char(string='Signé par', default=lambda self: self.env.user.name)
    pdf_attachment_id = fields.Many2one('ir.attachment', string='Pièce jointe PDF', copy=False)
    email_sent = fields.Boolean(string='Email envoyé', copy=False)
    send_date = fields.Datetime(string='Date d\'envoi', copy=False)
    requested_by_id = fields.Many2one('res.users', string='Demandé par', default=lambda self: self.env.user)
    request_date = fields.Datetime(string='Date de demande', default=fields.Datetime.now)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.certificate') or _('New')
        return super().create(vals_list)

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_send_email(self):
        self.ensure_one()
        if self.state != 'validated':
            raise ValidationError(_("L'attestation doit être validée par un administrateur avant d'être envoyée."))
        if not self.pdf_attachment_id:
            self.generate_pdf()
        template = self.env.ref(
            'agh_employee_certificate.email_template_certificate',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id)
        self.write({
            'email_sent': True,
            'send_date': fields.Datetime.now(),
            'state': 'sent',
        })

    def generate_pdf(self):
        self.ensure_one()
        report_xmlid_map = {
            'ATT_TRAVAIL': 'agh_employee_certificate.report_att_travail',
            'ATT_SALAIRE': 'agh_employee_certificate.report_att_salaire',
            'ATT_STAGE': 'agh_employee_certificate.report_att_stage',
            'ATT_CONGE': 'agh_employee_certificate.report_attestation_conge',
            'PEC': 'agh_employee_certificate.report_prise_en_charge',
            'ATT_FIN': 'agh_employee_certificate.report_attestation_fin',
        }
        report_xmlid = report_xmlid_map.get(self.certificate_type)
        if not report_xmlid:
            raise ValidationError(_("Aucun rapport défini pour ce type d'attestation."))
        report = self.env.ref(report_xmlid, raise_if_not_found=False)
        if not report:
            raise ValidationError(_("Rapport introuvable : %s") % report_xmlid)
        pdf_content, _ = report._render_qweb_pdf(self.ids)
        attachment = self.env['ir.attachment'].create({
            'name': '%s_%s.pdf' % (self.name, self.employee_id.name),
            'type': 'binary',
            'datas': pdf_content,
            'res_model': 'hr.certificate',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        self.pdf_attachment_id = attachment

    def action_view_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % self.pdf_attachment_id.id,
            'target': 'new',
        }

    def _get_report_data(self):
        """Returns dynamic data used in QWeb reports."""
        self.ensure_one()
        employee = self.employee_id
        # Get active contract via hr.contract (available in Community)
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['open', 'close']),
        ], limit=1, order='date_start desc')
        return {
            'certificate': self,
            'employee': employee,
            'company': self.company_id,
            'contract': contract,
            'wage': contract.wage if contract else 0.0,
            'signature': self.signature_image,
            'signature_name': self.signature_name,
        }
