# -*- coding: utf-8 -*-
import base64
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # ==========================================================
    # CRON : envoi automatique d'attestation à la fin du contrat
    # ==========================================================
    def cron_auto_send_attestation(self):
        """Recherche les contrats arrivant à terme aujourd'hui et
        envoie automatiquement une attestation (Stage ou Travail)
        à l'employé concerné. Inspiré du module intern_attestation.
        """
        today = fields.Date.today()
        _logger.info("AGH ATTESTATION CRON EXECUTED - %s", today)

        contracts = self.search([
            ('date_end', '=', today),
            ('employee_id.attestation_sent', '=', False),
        ])

        for contract in contracts:
            employee = contract.employee_id
            job = (employee.job_id.name or '').lower()

            # Détection du type d'attestation selon le poste / flag stagiaire
            if employee.is_intern or any(
                k in job for k in ('trainee', 'stagiaire', 'intern')
            ):
                attestation_type = "Attestation de Stage"
                body = (
                    f"<p>Bonjour {employee.name},</p>"
                    "<p>Nous attestons que vous avez effectué votre stage "
                    "au sein de notre société.</p>"
                    "<p>Cordialement.</p>"
                )
            else:
                attestation_type = "Attestation de Travail"
                body = (
                    f"<p>Bonjour {employee.name},</p>"
                    "<p>Nous attestons que vous avez travaillé "
                    "au sein de notre société.</p>"
                    "<p>Cordialement.</p>"
                )

            if not employee.work_email:
                _logger.info("No email for %s", employee.name)
                continue

            # Numéro unique
            sequence = self.env['ir.sequence'].next_by_code(
                'intern.attestation') or 'ATT/000'
            employee.attestation_number = sequence

            # PDF
            report = self.env.ref(
                'agh_employee_certificate.action_report_employee_attestation',
                raise_if_not_found=False,
            )
            if not report:
                _logger.info("Report not found")
                continue

            pdf_content, _dummy = report._render_qweb_pdf(
                report.report_name, [employee.id])

            attachment = self.env['ir.attachment'].create({
                'name': f'{sequence}_{employee.name}.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'hr.employee',
                'res_id': employee.id,
                'mimetype': 'application/pdf',
            })

            mail = self.env['mail.mail'].create({
                'subject': attestation_type,
                'body_html': body,
                'email_to': employee.work_email,
                'attachment_ids': [(6, 0, [attachment.id])],
            })
            mail.send()

            employee.attestation_sent = True
            employee.message_post(
                body=(
                    f"{attestation_type} envoyée automatiquement.<br/>"
                    f"Référence : {sequence}"
                )
            )

            _logger.info(
                "%s sent to %s (%s)",
                attestation_type, employee.work_email, sequence,
            )
