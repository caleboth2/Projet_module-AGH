import subprocess
import logging
from datetime import datetime, timedelta, date
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AghScheduledAction(models.AbstractModel):
    _name = 'agh.scheduled.action'
    _description = 'Actions planifiées pour l’automatisation'

    @api.model
    def _log_execution(self, action_name, status, details=''):
        """Enregistre l’exécution dans le journal dédié."""
        log_model = self.env['agh.workflow.log']
        log_model.create({
            'action_name': action_name,
            'status': status,
            'details': details,
            'execution_date': fields.Datetime.now(),
        })

    # -------------------------------------------------------------------------
    # 1. Relances impayés clients (J+15, J+30, J+60)
    # -------------------------------------------------------------------------
    @api.model
    def cron_send_customer_reminders(self):
        """Envoi d’email de relance selon les échéances J+15, J+30, J+60."""
        action_name = 'Relances impayés clients'
        _logger.info('Début de %s', action_name)
        today = date.today()
        templates = {
            15: self.env.ref('agh_automation.email_template_reminder_15d', False),
            30: self.env.ref('agh_automation.email_template_reminder_30d', False),
            60: self.env.ref('agh_automation.email_template_reminder_60d', False),
        }
        # Factures clients non soldées
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('state', '=', 'posted'),
            ('invoice_date_due', '!=', False)
        ])
        sent_count = 0
        for inv in invoices:
            due_date = inv.invoice_date_due
            if not due_date:
                continue
            days_overdue = (today - due_date).days
            if days_overdue in templates and templates[days_overdue]:
                try:
                    # Envoi du template d’email avec la facture en contexte
                    template = templates[days_overdue]
                    template.with_context(active_id=inv.id).send_mail(inv.id)
                    sent_count += 1
                    _logger.info('Relance envoyée pour facture %s (%s jours)', inv.name, days_overdue)
                except Exception as e:
                    _logger.exception('Erreur envoi relance facture %s', inv.name)
        self._log_execution(action_name, 'success', f'{sent_count} relances envoyées')
        return True

    # -------------------------------------------------------------------------
    # 2. Alertes échéances fournisseurs (J-3 et J-1)
    # -------------------------------------------------------------------------
    @api.model
    def cron_supplier_payment_alerts(self):
        """Notification des échéances fournisseurs à J-3 et J-1."""
        action_name = 'Alertes échéances fournisseurs'
        _logger.info('Début de %s', action_name)
        today = date.today()
        target_days = [3, 1]
        for delta in target_days:
            target_date = today + timedelta(days=delta)
            bills = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('state', '=', 'posted'),
                ('invoice_date_due', '=', target_date)
            ])
            for bill in bills:
                message = f"Échéance fournisseur {bill.partner_id.name} - Facture {bill.name} due le {bill.invoice_date_due}"
                # Notification Odoo interne
                bill.message_post(body=message, subject="Alerte échéance fournisseur")
                # Envoi email aux utilisateurs responsables (ex: acheteur)
                if bill.user_id and bill.user_id.email:
                    mail_vals = {
                        'subject': f'Paiement fournisseur imminent : {bill.name}',
                        'body_html': f'<p>{message}</p>',
                        'email_to': bill.user_id.email,
                    }
                    self.env['mail.mail'].create(mail_vals).send()
        self._log_execution(action_name, 'success', 'Alertes fournisseurs traitées')
        return True

    # -------------------------------------------------------------------------
    # 3. Clôture mensuelle automatique (verrouillage période N-1)
    # -------------------------------------------------------------------------
    @api.model
    def cron_monthly_closing(self):
        """Verrouillage de la période comptable du mois précédent."""
        action_name = 'Clôture mensuelle automatique'
        _logger.info('Début de %s', action_name)
        today = fields.Date.today()
        first_day_current = today.replace(day=1)
        last_month_end = first_day_current - timedelta(days=1)
        if last_month_end.month == 12:
            fiscal_year_end = date(last_month_end.year, 12, 31)
        else:
            fiscal_year_end = date(last_month_end.year, last_month_end.month, 1) - timedelta(days=1)

        # Mise à jour de la date de verrouillage des écritures comptables (company)
        companies = self.env['res.company'].search([])
        for company in companies:
            company.write({'lock_date': last_month_end})
            company.write({'fiscalyear_lock_date': fiscal_year_end})
        self._log_execution(action_name, 'success', f'Période verrouillée jusqu’au {last_month_end}')
        return True

    # -------------------------------------------------------------------------
    # 4. Export TVA DGI (mensuel/trimestriel)
    # -------------------------------------------------------------------------
    @api.model
    def cron_export_tva_dgi(self):
        """Génération du fichier TVA DGI et envoi au destinataire configuré."""
        action_name = 'Export TVA DGI'
        _logger.info('Début de %s', action_name)
        # Période par défaut : mois précédent
        today = date.today()
        first_day_prev = today.replace(day=1) - timedelta(days=1)
        period_start = first_day_prev.replace(day=1)
        period_end = first_day_prev

        # Appel au module agh_fiscal_maroc pour générer le fichier
        try:
            tva_export = self.env['dgi.tva.export'].create({
                'date_from': period_start,
                'date_to': period_end,
            })
            attachment = tva_export.generate_export_file()  # méthode fictive, adapter selon module réel
            # Envoi par email à la DGI (ou direction fiscale)
            email_values = {
                'subject': f'Déclaration TVA {period_start.strftime("%m/%Y")}',
                'body_html': '<p>Fichier TVA généré automatiquement.</p>',
                'attachment_ids': [(4, attachment.id)],
                'email_to': self.env['ir.config_parameter'].sudo().get_param('dgi_tva_recipient_email', 'dgi@example.com'),
            }
            self.env['mail.mail'].create(email_values).send()
            self._log_execution(action_name, 'success', f'Export TVA {period_start} - {period_end} envoyé')
        except Exception as e:
            self._log_execution(action_name, 'failed', str(e))
            _logger.exception('Erreur export TVA')
        return True

    # -------------------------------------------------------------------------
    # 5. Rappel calendrier fiscal (alerte avant échéances DGI)
    # -------------------------------------------------------------------------
    @api.model
    def cron_fiscal_calendar_reminder(self):
        """Alerte configurable sur les échéances fiscales (ex: TVA, IS)."""
        action_name = 'Rappel calendrier fiscal'
        _logger.info('Début de %s', action_name)
        # Utilisation des événements du calendrier fiscal depuis agh_fiscal_maroc
        FiscalEvent = self.env['fiscal.calendar.event'] if 'fiscal.calendar.event' in self.env else None
        if FiscalEvent:
            today = date.today()
            upcoming = FiscalEvent.search([
                ('date_due', '>=', today),
                ('date_due', '<=', today + timedelta(days=7)),
                ('reminder_sent', '=', False)
            ])
            for event in upcoming:
                # Notification aux responsables
                partner_ids = event.responsible_ids.ids if event.responsible_ids else []
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': f'Échéance fiscale : {event.name}',
                    'note': f'Date : {event.date_due}',
                    'res_model_id': self.env['ir.model']._get_id('fiscal.calendar.event'),
                    'res_id': event.id,
                    'user_ids': [(4, self.env.ref('base.user_admin').id)],  # À adapter
                })
                event.write({'reminder_sent': True})
        self._log_execution(action_name, 'success', 'Rappels fiscaux traités')
        return True

    # -------------------------------------------------------------------------
    # 6. Sauvegarde base de données (dump PostgreSQL compressé)
    # -------------------------------------------------------------------------
    @api.model
    def cron_db_backup(self):
        """Dump PostgreSQL quotidien et nettoyage des anciennes sauvegardes."""
        action_name = 'Sauvegarde base de données'
        _logger.info('Début de %s', action_name)
        db_name = self._cr.dbname
        backup_dir = '/var/odoo/backups'  # À adapter selon infrastructure
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'{backup_dir}/{db_name}_{timestamp}.sql.gz'
        try:
            subprocess.run(
                f'pg_dump {db_name} | gzip > {backup_file}',
                shell=True, check=True, executable='/bin/bash'
            )
            # Nettoyage des backups de plus de 30 jours
            subprocess.run(f'find {backup_dir} -name "*.sql.gz" -mtime +30 -delete', shell=True)
            self._log_execution(action_name, 'success', f'Sauvegarde créée : {backup_file}')
        except subprocess.CalledProcessError as e:
            self._log_execution(action_name, 'failed', str(e))
            _logger.exception('Erreur lors du dump PostgreSQL')
        return True

    # -------------------------------------------------------------------------
    # 7. Rapport trésorerie quotidien
    # -------------------------------------------------------------------------
    @api.model
    def cron_cash_flow_report(self):
        """Envoi des soldes bancaires à la direction."""
        action_name = 'Rapport trésorerie'
        _logger.info('Début de %s', action_name)
        bank_journals = self.env['account.journal'].search([('type', '=', 'bank')])
        lines = []
        total = 0.0
        for journal in bank_journals:
            balance = journal.balance
            total += balance
            lines.append(f'<tr><td>{journal.name}</td><td align="right">{balance:,.2f} MAD</td></tr>')
        html = f"""
        <h3>Situation de trésorerie au {fields.Date.today()}</h3>
        <table border="1" cellpadding="5">
        <thead><tr><th>Compte bancaire</th><th>Solde</th></tr></thead>
        <tbody>{''.join(lines)}</tbody>
        <tfoot><tr><th>Total</th><th align="right">{total:,.2f} MAD</th></tr></tfoot>
        </table>
        """
        # Destinataire : paramètre système ou responsable financier
        recipient = self.env['ir.config_parameter'].sudo().get_param('cash_flow_recipient_email', 'direction@example.com')
        self.env['mail.mail'].create({
            'subject': f'Rapport trésorerie quotidien {fields.Date.today()}',
            'body_html': html,
            'email_to': recipient,
        }).send()
        self._log_execution(action_name, 'success', 'Email envoyé')
        return True

    # -------------------------------------------------------------------------
    # 8. Calcul des KPIs quotidiens
    # -------------------------------------------------------------------------
    @api.model
    def cron_update_kpis(self):
        """Mise à jour des indicateurs dans un modèle dédié (ou envoi par mail)."""
        action_name = 'Calcul KPIs'
        _logger.info('Début de %s', action_name)
        today = date.today()
        # Exemples de KPIs
        total_unpaid = sum(self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('state', '=', 'posted')
        ]).mapped('amount_residual'))
        overdue_count = self.env['account.move'].search_count([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('invoice_date_due', '<', today)
        ])
        # Stockage dans un modèle dédié (optionnel)
        KpiModel = self.env['agh.kpi'] if 'agh.kpi' in self.env else None
        if KpiModel:
            KpiModel.create({
                'date': today,
                'total_receivables': total_unpaid,
                'overdue_invoices_count': overdue_count,
            })
        # Envoi récapitulatif à la direction
        body = f"""
        <p>KPIs du {today}:</p>
        <ul>
        <li>Créances clients totales : {total_unpaid:,.2f} MAD</li>
        <li>Factures impayées en retard : {overdue_count}</li>
        </ul>
        """
        self.env['mail.mail'].create({
            'subject': f'KPIs quotidiens {today}',
            'body_html': body,
            'email_to': self.env['ir.config_parameter'].sudo().get_param('kpi_recipient_email', 'direction@example.com'),
        }).send()
        self._log_execution(action_name, 'success', 'KPIs mis à jour')
        return True