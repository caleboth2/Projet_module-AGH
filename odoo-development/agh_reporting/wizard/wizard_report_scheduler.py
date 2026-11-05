from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import base64
import logging

_logger = logging.getLogger(__name__)


class ReportScheduler(models.Model):
    _name = 'report.scheduler'
    _description = 'Planification envoi rapports'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom planification', required=True, tracking=True)
    report_type = fields.Selection([
        ('bilan', 'Bilan PCM'),
        ('cpc', 'CPC'),
        ('flux', 'Tableau de flux'),
        ('balance_agee_client', 'Balance âgée clients'),
        ('balance_agee_fournisseur', 'Balance âgée fournisseurs'),
        ('grand_livre', 'Grand-livre général'),
        ('kpi_dashboard', 'Tableau de bord KPIs'),
    ], string='Type rapport', required=True, tracking=True)
    frequency = fields.Selection([
        ('daily', 'Quotidien'),
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel'),
        ('quarterly', 'Trimestriel'),
        ('yearly', 'Annuel'),
    ], string='Fréquence', required=True, default='monthly', tracking=True)
    day_of_month = fields.Integer(
        string='Jour du mois',
        help='Pour les rapports mensuels (1-31)',
        default=1,
    )
    day_of_week = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
        ('6', 'Dimanche'),
    ], string='Jour de la semaine', help='Pour les rapports hebdomadaires')
    hour = fields.Integer(string='Heure (0-23)', default=9)
    minute = fields.Integer(string='Minute (0-59)', default=0)
    last_sent = fields.Datetime(string='Dernier envoi', readonly=True)
    next_send = fields.Datetime(
        string='Prochain envoi',
        compute='_compute_next_send',
        store=True,
    )
    active = fields.Boolean(string='Actif', default=True, tracking=True)

    email_to = fields.Text(
        string='Destinataires (Email)',
        required=True,
        help="Un email par ligne ou séparés par des virgules",
    )
    email_cc = fields.Text(string='Copie (CC)')
    email_bcc = fields.Text(string='Copie cachée (BCC)')

    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('both', 'PDF et Excel'),
    ], string='Format sortie', default='pdf')

    period_days = fields.Integer(
        string='Période (jours)',
        default=30,
        help="Nombre de jours à inclure dans le rapport",
    )
    compare_previous = fields.Boolean(string='Comparer avec N-1', default=True)

    history_ids = fields.One2many(
        'report.scheduler.history', 'scheduler_id', string='Historique envois'
    )
    body_preview = fields.Html(string='Aperçu email', compute='_compute_body_preview')

    @api.depends('report_type', 'period_days', 'output_format')
    def _compute_body_preview(self):
        for rec in self:
            import datetime as dt_mod
            today = dt_mod.date.today()
            date_from = today - timedelta(days=rec.period_days or 30)
            rec.body_preview = rec._get_email_body(date_from, today)

    @api.depends('frequency', 'hour', 'minute', 'day_of_month', 'day_of_week', 'last_sent', 'active')
    def _compute_next_send(self):
        for scheduler in self:
            if not scheduler.active:
                scheduler.next_send = False
                continue
            now = datetime.now()
            scheduler.next_send = scheduler._calculate_next_date(now)

    def _calculate_next_date(self, from_date):
        hour = self.hour or 0
        minute = self.minute or 0

        if self.frequency == 'daily':
            next_date = from_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_date <= from_date:
                next_date += timedelta(days=1)

        elif self.frequency == 'weekly':
            target_weekday = int(self.day_of_week) if self.day_of_week else 0
            days_ahead = (target_weekday - from_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_date = (from_date + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

        elif self.frequency == 'monthly':
            target_day = self.day_of_month or 1
            try:
                next_date = from_date.replace(day=target_day, hour=hour, minute=minute, second=0, microsecond=0)
            except ValueError:
                next_date = from_date.replace(day=28, hour=hour, minute=minute, second=0, microsecond=0)
            if next_date <= from_date:
                month = from_date.month + 1
                year = from_date.year
                if month > 12:
                    month = 1
                    year += 1
                try:
                    next_date = next_date.replace(year=year, month=month, day=target_day)
                except ValueError:
                    next_date = next_date.replace(year=year, month=month, day=28)

        elif self.frequency == 'quarterly':
            quarter_start_month = ((from_date.month - 1) // 3) * 3 + 1
            next_quarter_month = quarter_start_month + 3
            year = from_date.year
            if next_quarter_month > 12:
                next_quarter_month = 1
                year += 1
            next_date = from_date.replace(
                year=year, month=next_quarter_month, day=1,
                hour=hour, minute=minute, second=0, microsecond=0
            )

        else:  # yearly
            next_date = from_date.replace(
                month=1, day=1, hour=hour, minute=minute, second=0, microsecond=0
            )
            if next_date <= from_date:
                next_date = next_date.replace(year=from_date.year + 1)

        return next_date

    def action_send_now(self):
        self.ensure_one()
        self._send_report()
        return {'type': 'ir.actions.act_window_close'}

    def _send_report(self):
        self.ensure_one()
        import datetime as dt_mod
        try:
            date_to = dt_mod.date.today()
            date_from = date_to - timedelta(days=self.period_days or 30)
            report_info = self._get_report_info()
            self._send_email(report_info, date_from, date_to)
            self.env['report.scheduler.history'].create({
                'scheduler_id': self.id,
                'sent_date': fields.Datetime.now(),
                'status': 'sent',
                'recipients': self.email_to,
            })
            self.last_sent = fields.Datetime.now()
        except Exception as e:
            _logger.error("Erreur envoi rapport %s: %s", self.name, str(e))
            self.env['report.scheduler.history'].create({
                'scheduler_id': self.id,
                'sent_date': fields.Datetime.now(),
                'status': 'error',
                'error_message': str(e),
            })
            raise

    def _get_report_info(self):
        report_map = {
            'bilan': 'agh_reporting.report_bilan_pcm',
            'cpc': 'agh_reporting.report_cpc_pcm',
            'flux': 'agh_reporting.report_flux_tresorerie',
            'balance_agee_client': 'agh_reporting.report_balance_agee',
            'balance_agee_fournisseur': 'agh_reporting.report_balance_agee',
            'grand_livre': 'agh_reporting.report_grand_livre',
            'kpi_dashboard': False,
        }
        return {
            'report_name': report_map.get(self.report_type),
            'type': self.report_type,
        }

    def _send_email(self, report_info, date_from, date_to):
        attachments = []

        if self.output_format in ('pdf', 'both') and report_info.get('report_name'):
            try:
                report = self.env['ir.actions.report']._get_report_from_name(
                    report_info['report_name']
                )
                if report:
                    pdf_content, _mime = report._render_qweb_pdf(self, data={})
                    attachments.append((
                        "rapport_{}_{}_{}.pdf".format(self.report_type, date_from, date_to),
                        pdf_content,
                    ))
            except Exception as e:
                _logger.warning("Impossible de générer le PDF: %s", str(e))

        mail_values = {
            'subject': "[Rapport périodique] {} - {}".format(
                self._get_report_label(), self.env.company.name
            ),
            'body_html': self._get_email_body(date_from, date_to),
            'email_to': self.email_to,
            'email_cc': self.email_cc or '',
            'email_bcc': self.email_bcc or '',
            'attachment_ids': [],
        }

        for att_name, att_content in attachments:
            if isinstance(att_content, bytes):
                att_data = base64.b64encode(att_content).decode('utf-8')
            else:
                att_data = att_content
            attachment = self.env['ir.attachment'].create({
                'name': att_name,
                'datas': att_data,
                'res_model': 'report.scheduler',
                'res_id': self.id,
            })
            mail_values['attachment_ids'].append((4, attachment.id))

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

    def _get_report_label(self):
        labels = {
            'bilan': 'Bilan PCM',
            'cpc': 'CPC',
            'flux': 'Tableau de flux de trésorerie',
            'balance_agee_client': 'Balance âgée clients',
            'balance_agee_fournisseur': 'Balance âgée fournisseurs',
            'grand_livre': 'Grand-livre général',
            'kpi_dashboard': 'Tableau de bord KPIs',
        }
        return labels.get(self.report_type, 'Rapport')

    def _get_email_body(self, date_from, date_to):
        return """
        <div style="font-family: Arial, sans-serif;">
            <h3>Rapport périodique - {report_name}</h3>
            <p>Bonjour,</p>
            <p>Veuillez trouver ci-joint le rapport <strong>{report_name}</strong>
            pour la période du <strong>{date_from}</strong> au <strong>{date_to}</strong>.</p>
            <ul>
                <li>Type: {report_name}</li>
                <li>Période: {period_days} jours</li>
                <li>Format: {output_format}</li>
            </ul>
            <p>Cordialement,</p>
            <p><strong>{company}</strong></p>
            <hr/>
            <p style="font-size: 10px; color: #666;">Email généré automatiquement.</p>
        </div>
        """.format(
            report_name=self._get_report_label(),
            date_from=date_from,
            date_to=date_to,
            period_days=self.period_days or 30,
            output_format=self.output_format or 'pdf',
            company=self.env.company.name,
        )

    def action_view_history(self):
        self.ensure_one()
        return {
            'name': _('Historique envois'),
            'type': 'ir.actions.act_window',
            'res_model': 'report.scheduler.history',
            'view_mode': 'list,form',
            'domain': [('scheduler_id', '=', self.id)],
        }


class ReportSchedulerHistory(models.Model):
    _name = 'report.scheduler.history'
    _description = 'Historique envois rapports'
    _order = 'sent_date desc'

    scheduler_id = fields.Many2one('report.scheduler', string='Planification', ondelete='cascade')
    sent_date = fields.Datetime(string='Date envoi', required=True)
    status = fields.Selection([
        ('sent', 'Envoyé'),
        ('error', 'Erreur'),
    ], string='Statut', required=True)
    recipients = fields.Text(string='Destinataires')
    error_message = fields.Text(string="Message d'erreur")

    def action_resend(self):
        self.ensure_one()
        return self.scheduler_id.action_send_now()
