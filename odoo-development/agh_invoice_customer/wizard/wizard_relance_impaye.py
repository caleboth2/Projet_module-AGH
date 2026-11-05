# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardRelanceImpaye(models.TransientModel):
    _name = 'wizard.relance.impaye'
    _description = "Wizard de relance pour impayes"

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string="Facture",
        required=True,
        domain=[
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('not_paid', 'partial', 'in_payment')),
        ],
    )
    relance_level = fields.Selection(
        selection=[
            ('1', "Premiere relance (J+15)"),
            ('2', "Deuxieme relance (J+30)"),
            ('3', "Derniere relance (J+60)"),
        ],
        string="Niveau de relance",
        required=True,
        default='1',
    )
    email_to = fields.Char(
        string="Email destinataire",
        required=True,
    )
    subject = fields.Char(string="Objet")
    body = fields.Html(
        string="Message",
        sanitize=False,
        help="Contenu de l'email de relance.",
    )

    @api.onchange('invoice_id', 'relance_level')
    def _onchange_relance_level(self):
        if not self.invoice_id:
            return
        invoice = self.invoice_id
        partner = invoice.partner_id
        self.email_to = partner.email or ''

        days_late = invoice.agh_late_days or 0
        ref = invoice.agh_sequence_maroc or invoice.name or ''
        symbol = invoice.currency_id.symbol or ''
        company_name = self.env.company.name

        if self.relance_level == '1':
            self.subject = f"Relance 1 - Facture {ref} - Echeance depassee"
            self.body = (
                '<div style="font-family: Arial, sans-serif;">'
                "<p><strong>Objet: Premiere relance - Facture echue</strong></p>"
                "<p>Bonjour,</p>"
                f"<p>Nous vous rappelons que la facture <strong>{ref}</strong> "
                f"d'un montant de <strong>{invoice.amount_residual} {symbol}</strong> "
                f"est echue depuis <strong>{days_late} jours</strong>.</p>"
                "<p>Nous vous remercions de bien vouloir proceder a son reglement "
                "dans les plus brefs delais.</p>"
                "<p>Cordialement,</p>"
                f"<p><strong>{company_name}</strong></p>"
                '</div>'
            )
        elif self.relance_level == '2':
            self.subject = f"Deuxieme relance - Facture {ref} - URGENT"
            self.body = (
                '<div style="font-family: Arial, sans-serif;">'
                "<p><strong>Objet: Deuxieme relance - Situation impayee</strong></p>"
                "<p>Bonjour,</p>"
                f"<p>Malgre notre premiere relance, la facture <strong>{ref}</strong> "
                f"d'un montant de <strong>{invoice.amount_residual} {symbol}</strong> "
                f"reste impayee depuis <strong>{days_late} jours</strong>.</p>"
                "<p>Nous vous saurions gre de regulariser cette situation sous 48 heures.</p>"
                "<p>Cordialement,</p>"
                f"<p><strong>{company_name}</strong></p>"
                '</div>'
            )
        else:
            self.subject = f"DERNIERE RELANCE - Facture {ref} - Mise en demeure"
            self.body = (
                '<div style="font-family: Arial, sans-serif;">'
                "<p><strong>Objet: DERNIERE RELANCE AVANT PROCEDURE</strong></p>"
                "<p>Bonjour,</p>"
                f"<p>Nous vous mettons en demeure de regler la facture <strong>{ref}</strong> "
                f"d'un montant de <strong>{invoice.amount_residual} {symbol}</strong> "
                f"en souffrance depuis <strong>{days_late} jours</strong>.</p>"
                "<p><strong>A defaut de reglement sous 8 jours, nous nous verrons "
                "dans l'obligation de:</strong></p>"
                "<ul>"
                "<li>Suspendre les livraisons</li>"
                "<li>Transmettre le dossier a notre service contentieux</li>"
                "<li>Appliquer les penalites de retard prevues par la loi</li>"
                "</ul>"
                "<p>Cordialement,</p>"
                f"<p><strong>{company_name}</strong></p>"
                '</div>'
            )

    def action_send_relance(self):
        """Envoie la relance et incremente le compteur."""
        self.ensure_one()
        if not self.email_to:
            raise UserError(_("Veuillez specifier un email destinataire."))

        mail_values = {
            'subject': self.subject or _("Relance"),
            'body_html': self.body or '',
            'email_to': self.email_to,
            'res_id': self.invoice_id.id,
            'model': 'account.move',
            'auto_delete': False,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()

        self.invoice_id.action_increment_relance()
        self.invoice_id.message_post(
            body=_("Relance niveau %(level)s envoyee a %(email)s") % {
                'level': self.relance_level,
                'email': self.email_to,
            },
            subject=self.subject or '',
        )

        return {'type': 'ir.actions.act_window_close'}
