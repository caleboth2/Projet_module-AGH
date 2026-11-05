from odoo import fields, models


class HrEmployeeDocument(models.Model):
    _inherit = 'hr.employee.document'

    kyc_status = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('processing', 'En cours d’analyse'),
            ('validated', 'Validé'),
            ('rejected', 'Rejeté'),
        ],
        string='Statut KYC',
        default='draft',
        required=True,
        copy=False,
    )

    extracted_first_name = fields.Char(
        string='Prénom extrait',
        copy=False,
    )

    extracted_last_name = fields.Char(
        string='Nom extrait',
        copy=False,
    )

    extracted_document_number = fields.Char(
        string='Numéro de document extrait',
        copy=False,
    )

    extracted_issue_date = fields.Date(
        string="Date d'émission extraite",
        copy=False,
    )

    extracted_expiry_date = fields.Date(
        string="Date d'expiration extraite",
        copy=False,
    )

    ocr_raw_text = fields.Text(
        string='Texte OCR brut',
        readonly=True,
        copy=False,
    )

    ocr_confidence = fields.Float(
        string='Confiance OCR (%)',
        readonly=True,
        copy=False,
    )

    ocr_analyzed_at = fields.Datetime(
        string="Date d'analyse OCR",
        readonly=True,
        copy=False,
    )

    ocr_analyzed_by = fields.Many2one(
        comodel_name='res.users',
        string='Analysé par',
        readonly=True,
        copy=False,
    )

    rejection_reason = fields.Text(
        string='Motif du rejet',
        copy=False,
    )

    validated_at = fields.Datetime(
        string='Date de validation',
        readonly=True,
        copy=False,
    )

    validated_by = fields.Many2one(
        comodel_name='res.users',
        string='Validé par',
        readonly=True,
        copy=False,
    )