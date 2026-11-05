# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardSendInvoice(models.TransientModel):
    _name = 'wizard.send.invoice'
    _description = "Wizard d'envoi de facture par email"

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string="Facture",
        required=True,
        domain=[('move_type', '=', 'out_invoice')],
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Destinataire",
        required=True,
    )
    email_to = fields.Char(
        string="Email destinataire",
        required=True,
    )
    email_cc = fields.Char(string="Copie (CC)")
    subject = fields.Char(
        string="Objet",
        required=True,
        default="Facture",
    )
    body = fields.Html(
        string="Message",
        sanitize=False,
        help="Contenu de l'email.",
    )
    attach_pdf = fields.Boolean(
        string="Joindre le PDF",
        default=True,
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.email_to = self.partner_id.email or ''
            if self.invoice_id:
                self.subject = (
                    f"Facture {self.invoice_id.agh_sequence_maroc or self.invoice_id.name or ''}"
                )

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id and not self.body:
            invoice = self.invoice_id
            ref = invoice.agh_sequence_maroc or invoice.name or ''
            symbol = invoice.currency_id.symbol or ''
            self.body = (
                '<div style="font-family: Arial, sans-serif;">'
                '<p>Bonjour,</p>'
                f'<p>Veuillez trouver ci-joint la facture <strong>{ref}</strong> '
                f"d'un montant de <strong>{invoice.amount_total} {symbol}</strong>.</p>"
                f"<p>Date d'echeance: {invoice.invoice_date_due or ''}</p>"
                '<p>Cordialement,</p>'
                f'<p><strong>{self.env.company.name}</strong></p>'
                '</div>'
            )

    def action_send(self):
        """Envoie l'email avec le PDF en piece jointe."""
        self.ensure_one()
        if not self.email_to:
            raise UserError(_("Veuillez specifier un email destinataire."))

        attachment_ids = []
        if self.attach_pdf:
            report = self.env.ref(
                'agh_invoice_customer.action_report_invoice_maroc', raise_if_not_found=False
            )
            if report:
                pdf_content, _content_type = report._render_qweb_pdf(
                    'agh_invoice_customer.action_report_invoice_maroc',
                    res_ids=[self.invoice_id.id],
                )
                attachment = self.env['ir.attachment'].create({
                    'name': f"Facture_{self.invoice_id.agh_sequence_maroc or self.invoice_id.name or 'facture'}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'account.move',
                    'res_id': self.invoice_id.id,
                    'mimetype': 'application/pdf',
                })
                attachment_ids.append((4, attachment.id))

        mail_values = {
            'subject': self.subject,
            'body_html': self.body or '',
            'email_to': self.email_to,
            'email_cc': self.email_cc or False,
            'attachment_ids': attachment_ids,
            'res_id': self.invoice_id.id,
            'model': 'account.move',
            'auto_delete': False,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()

        self.invoice_id.agh_email_sent = True
        self.invoice_id.message_post(
            body=_("Facture envoyee par email a %s.") % self.email_to,
            subject=self.subject,
        )

        return {'type': 'ir.actions.act_window_close'}
