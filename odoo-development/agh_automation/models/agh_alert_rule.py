from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AghAlertRule(models.Model):
    _name = 'agh.alert.rule'
    _description = 'Règle d’alerte dynamique'
    _rec_name = 'name'

    name = fields.Char(string='Libellé', required=True)
    model_id = fields.Many2one('ir.model', string='Modèle surveillé', required=True,
                               domain=[('transient', '=', False)], ondelete='cascade')
    condition_domain = fields.Char(string='Domaine Odoo (Python expression)',
                                   help="Exemple: [('state','=','posted'),('amount_residual','>',0)]")
    threshold_value = fields.Float(string='Seuil déclencheur', default=0.0,
                                   help="Nombre minimal d’enregistrements pour déclencher l’alerte")
    alert_type = fields.Selection([
        ('email', 'Email'),
        ('notification', 'Notification Odoo'),
        ('sms', 'SMS (API externe)')
    ], string="Type d’alerte", required=True, default='email')
    recipient_ids = fields.Many2many('res.users', string='Destinataires')
    active = fields.Boolean(string='Actif', default=True)

    @api.constrains('condition_domain')
    def _check_domain(self):
        for rule in self:
            if rule.condition_domain:
                try:
                    eval(rule.condition_domain)
                except Exception as e:
                    raise ValidationError(_("Domaine invalide : %s") % str(e))

    def _evaluate_rule(self):
        """Évalue la règle et déclenche l’alerte si les conditions sont remplies."""
        self.ensure_one()
        if not self.active:
            return False
        model = self.env[self.model_id.model]
        try:
            domain = eval(self.condition_domain) if self.condition_domain else []
        except Exception:
            _logger.exception("Erreur d’évaluation du domaine pour la règle %s", self.name)
            return False
        records = model.search(domain)
        if len(records) >= self.threshold_value:
            self._trigger_alert(records)
            return True
        return False

    def _trigger_alert(self, records):
        """Envoie l’alerte selon le type configuré."""
        if self.alert_type == 'email':
            self._send_email_alert(records)
        elif self.alert_type == 'notification':
            self._send_notification_alert(records)
        elif self.alert_type == 'sms':
            self._send_sms_alert(records)

    def _send_email_alert(self, records):
        """Construction et envoi d’un email aux destinataires."""
        recipients = self.recipient_ids.mapped('email')
        if not recipients:
            return
        body = f"""
        <p><strong>Règle d’alerte : {self.name}</strong></p>
        <p>Modèle : {self.model_id.name}</p>
        <p>Enregistrements concernés ({len(records)}) :</p>
        <ul>
        {"".join(f"<li>{rec.display_name}</li>" for rec in records[:10])}
        {"> 10 résultats ..." if len(records) > 10 else ""}
        </ul>
        """
        mail_vals = {
            'subject': f'Alerte : {self.name}',
            'body_html': body,
            'email_to': ','.join(recipients),
        }
        self.env['mail.mail'].create(mail_vals).send()

    def _send_notification_alert(self, records):
        """Crée des notifications (messages) pour chaque destinataire."""
        for user in self.recipient_ids:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': f'Alerte : {self.name}',
                'note': f"{len(records)} enregistrement(s) correspond(ent) à la règle.",
                'user_id': user.id,
                'res_model_id': self.model_id.id,
                'res_id': records[0].id if records else False,
            })

    def _send_sms_alert(self, records):
        """Placeholder pour l’envoi de SMS (nécessite un module SMS)."""
        _logger.info("SMS non implémenté - règle %s", self.name)