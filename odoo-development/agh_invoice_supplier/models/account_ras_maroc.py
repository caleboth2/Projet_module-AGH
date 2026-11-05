# -*- coding: utf-8 -*-
import base64
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountRASMaroc(models.Model):
    _name = 'account.ras.maroc'
    _description = 'Retenue a la Source Maroc'
    _rec_name = 'name'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Fournisseur',
        related='invoice_id.partner_id',
        store=True,
    )
    ras_type = fields.Selection(
        selection=[
            ('service', 'Prestation de service'),
            ('travaux', 'Travaux - BTP'),
            ('dividendes', 'Dividendes'),
            ('loyers', 'Loyers'),
            ('honoraires', 'Honoraires'),
            ('commissions', 'Commissions'),
        ],
        string='Type RAS',
        required=True,
        default='service',
    )
    ras_rate = fields.Float(
        string='Taux RAS (%)',
        required=True,
        default=10.0,
        help="Taux applicable selon la nature de la prestation",
    )
    taxable_base = fields.Monetary(
        string='Base taxable',
        currency_field='currency_id',
        required=True,
        default=0.0,
        help="Montant HT soumis a la retenue",
    )
    ras_amount = fields.Monetary(
        string='Montant RAS',
        currency_field='currency_id',
        compute='_compute_ras_amount',
        store=True,
    )
    ras_account_id = fields.Many2one(
        'account.account',
        string='Compte comptable RAS',
        domain="[('account_type', '=', 'liability_current')]",
        help="Compte 4456 - Retenues a la source",
    )
    declaration_id = fields.Many2one(
        'account.ras.declaration',
        string='Declaration mensuelle',
        readonly=True,
    )
    date = fields.Date(
        string='Date facture',
        related='invoice_id.invoice_date',
        store=True,
    )
    period = fields.Char(
        string='Periode',
        compute='_compute_period',
        store=True,
    )
    certificate_issued = fields.Boolean(string='Attestation emise', default=False)
    certificate_number = fields.Char(string='N. Attestation', copy=False)
    currency_id = fields.Many2one(
        'res.currency',
        related='invoice_id.currency_id',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='invoice_id.company_id',
        store=True,
    )

    @api.depends('taxable_base', 'ras_rate')
    def _compute_ras_amount(self):
        for ras in self:
            base = ras.taxable_base or 0.0
            rate = ras.ras_rate or 0.0
            ras.ras_amount = base * (rate / 100.0)

    @api.depends('invoice_id', 'invoice_id.name', 'ras_type', 'ras_rate')
    def _compute_name(self):
        for ras in self:
            invoice_name = ras.invoice_id.name or '/'
            ras_type = ras.ras_type or ''
            rate = ras.ras_rate or 0.0
            ras.name = "RAS %s - %s%% - %s" % (ras_type, rate, invoice_name)

    @api.depends('date')
    def _compute_period(self):
        for ras in self:
            if ras.date:
                ras.period = ras.date.strftime('%Y-%m')
            else:
                ras.period = False

    @api.constrains('ras_rate')
    def _check_ras_rate(self):
        valid_rates = [10.0, 15.0, 20.0, 30.0]
        for ras in self:
            if ras.ras_rate not in valid_rates:
                raise ValidationError(_(
                    "Le taux RAS doit etre l'un des suivants: %s%%"
                ) % ', '.join(str(r) for r in valid_rates))

    def action_generate_certificate(self):
        self.ensure_one()
        sequence = self.env['ir.sequence'].next_by_code('ras.certificate')
        if sequence:
            cert_number = sequence
        else:
            cert_number = "CERT-%s-%s" % (self.id, datetime.now().strftime('%Y%m%d'))
        self.write({
            'certificate_issued': True,
            'certificate_number': cert_number,
        })
        report_ref = self.env.ref('agh_invoice_supplier.action_report_ras_certificate')
        return report_ref.report_action(self)


class AccountRASDeclaration(models.Model):
    _name = 'account.ras.declaration'
    _description = 'Declaration Mensuelle RAS'
    _rec_name = 'name'
    _order = 'year desc, month desc'

    name = fields.Char(
        string='Nom declaration',
        required=True,
        copy=False,
        default=lambda self: "RAS-%s" % datetime.now().strftime('%Y-%m'),
    )
    month = fields.Selection(
        selection=[
            ('01', 'Janvier'), ('02', 'Fevrier'), ('03', 'Mars'),
            ('04', 'Avril'), ('05', 'Mai'), ('06', 'Juin'),
            ('07', 'Juillet'), ('08', 'Aout'), ('09', 'Septembre'),
            ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Decembre'),
        ],
        string='Mois',
        required=True,
        default=lambda self: datetime.now().strftime('%m'),
    )
    year = fields.Integer(
        string='Annee',
        required=True,
        default=lambda self: datetime.now().year,
    )
    declaration_date = fields.Date(string='Date declaration', default=fields.Date.today)
    ras_ids = fields.Many2many('account.ras.maroc', string='Retenues incluses')
    total_taxable_base = fields.Monetary(
        string='Total base taxable',
        compute='_compute_totals',
        currency_field='company_currency_id',
        store=True,
    )
    total_ras_amount = fields.Monetary(
        string='Total RAS',
        compute='_compute_totals',
        currency_field='company_currency_id',
        store=True,
    )
    status = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('submitted', 'Soumise'),
            ('paid', 'Payee'),
        ],
        string='Statut',
        default='draft',
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        default=lambda self: self.env.company,
        required=True,
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
    )

    @api.depends('ras_ids.ras_amount', 'ras_ids.taxable_base')
    def _compute_totals(self):
        for declaration in self:
            declaration.total_taxable_base = sum(declaration.ras_ids.mapped('taxable_base'))
            declaration.total_ras_amount = sum(declaration.ras_ids.mapped('ras_amount'))

    def action_submit(self):
        for decl in self:
            decl.status = 'submitted'
            for ras in decl.ras_ids:
                ras.declaration_id = decl.id

    def action_set_paid(self):
        for decl in self:
            decl.status = 'paid'

    def action_reset_draft(self):
        for decl in self:
            decl.status = 'draft'

    def action_generate_file(self):
        self.ensure_one()
        xml_content = self._generate_dgi_xml()
        attachment = self.env['ir.attachment'].create({
            'name': "declaration_ras_%s.xml" % self.name,
            'datas': base64.b64encode(xml_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/xml',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def _generate_dgi_xml(self):
        import xml.etree.ElementTree as ET
        from xml.dom import minidom

        root = ET.Element("DeclarationRAS")
        ET.SubElement(root, "Mois").text = self.month or ''
        ET.SubElement(root, "Annee").text = str(self.year or '')
        if self.declaration_date:
            decl_date_str = self.declaration_date.strftime('%Y-%m-%d')
        else:
            decl_date_str = ''
        ET.SubElement(root, "DateDeclaration").text = decl_date_str
        ET.SubElement(root, "TotalBaseTaxable").text = str(self.total_taxable_base or 0.0)
        ET.SubElement(root, "TotalRAS").text = str(self.total_ras_amount or 0.0)

        ras_element = ET.SubElement(root, "Retenues")
        for ras in self.ras_ids:
            ras_elem = ET.SubElement(ras_element, "Retenue")
            ET.SubElement(ras_elem, "Fournisseur").text = ras.partner_id.name or ''
            ET.SubElement(ras_elem, "ICE").text = ras.partner_id.agh_ice or ''
            ET.SubElement(ras_elem, "TypeRAS").text = ras.ras_type or ''
            ET.SubElement(ras_elem, "Taux").text = str(ras.ras_rate or 0.0)
            ET.SubElement(ras_elem, "BaseTaxable").text = str(ras.taxable_base or 0.0)
            ET.SubElement(ras_elem, "MontantRAS").text = str(ras.ras_amount or 0.0)
            ET.SubElement(ras_elem, "Facture").text = ras.invoice_id.name or ''

        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        return xml_str.encode('utf-8')
