from odoo import api, fields, models


class AghWorkflowLog(models.Model):
    _name = 'agh.workflow.log'
    _description = "Journal des executions automatiques"
    _order = 'execution_date desc'
    _rec_name = 'action_name'

    action_name = fields.Char(string='Action', required=True)
    execution_date = fields.Datetime(
        string="Date d'execution",
        default=fields.Datetime.now, required=True,
    )
    status = fields.Selection([
        ('success', 'Succes'),
        ('failed', 'Echec'),
        ('warning', 'Avertissement'),
        ('partial', 'Partiel'),
    ], string="Statut", default='success', required=True)

    duration = fields.Float(
        string="Duree (s)",
        help="Temps d'execution en secondes",
    )
    records_processed = fields.Integer(
        string="Enregistrements traites", default=0,
    )
    errors_count = fields.Integer(string="Nb erreurs", default=0)
    triggered_by = fields.Char(
        string="Declencheur",
        default='cron',
        help="cron, manuel, api, etc.",
    )
    error_message = fields.Text(string="Message d'erreur")
    details = fields.Text(string="Details / Message")
