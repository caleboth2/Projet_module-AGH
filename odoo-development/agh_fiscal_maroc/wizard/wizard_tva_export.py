# -*- coding: utf-8 -*-

import base64
import io
import csv

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardTvaExport(models.TransientModel):
    _name = 'wizard.tva.export'
    _description = "Assistant d'export TVA pour la DGI"

    declaration_id = fields.Many2one(
        'account.tva.declaration',
        string="Déclaration TVA",
        required=True,
    )
    export_format = fields.Selection(
        selection=[
            ('excel', 'Excel (.xlsx)'),
            ('csv', 'CSV'),
            ('xml', 'XML DGI'),
        ],
        string="Format",
        required=True,
        default='excel',
    )
    include_lines = fields.Boolean(string="Inclure le détail des lignes", default=True)

    file_data = fields.Binary(string="Fichier", readonly=True)
    filename = fields.Char(string="Nom du fichier", readonly=True)

    def action_export(self):
        self.ensure_one()
        if self.export_format == 'excel':
            return self._export_excel()
        if self.export_format == 'csv':
            return self._export_csv()
        if self.export_format == 'xml':
            return self._export_xml()
        raise UserError(_("Format d'export non supporté."))

    def _export_excel(self):
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_(
                "Le module Python 'xlsxwriter' est requis pour l'export Excel. "
                "Installez-le avec : pip install xlsxwriter"
            ))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Déclaration TVA')

        bold = workbook.add_format({'bold': True, 'bg_color': '#714B67', 'font_color': 'white'})
        money = workbook.add_format({'num_format': '#,##0.00'})

        d = self.declaration_id
        sheet.write('A1', _("Déclaration TVA"), bold)
        sheet.write('A2', _("Référence"))
        sheet.write('B2', d.name or '')
        sheet.write('A3', _("Société"))
        sheet.write('B3', d.company_id.name or '')
        sheet.write('A4', _("Période"))
        sheet.write('B4', "%s - %s" % (d.date_from or '', d.date_to or ''))

        sheet.write('A6', _("TVA Collectée"), bold)
        sheet.write('A7', "20%")
        sheet.write('B7', d.tva_collecte_20, money)
        sheet.write('A8', "14%")
        sheet.write('B8', d.tva_collecte_14, money)
        sheet.write('A9', "10%")
        sheet.write('B9', d.tva_collecte_10, money)
        sheet.write('A10', "7%")
        sheet.write('B10', d.tva_collecte_7, money)
        sheet.write('A11', _("Total"), bold)
        sheet.write('B11', d.total_tva_collecte, money)

        sheet.write('A13', _("TVA Déductible"), bold)
        sheet.write('A14', "20%")
        sheet.write('B14', d.tva_deductible_20, money)
        sheet.write('A15', "14%")
        sheet.write('B15', d.tva_deductible_14, money)
        sheet.write('A16', "10%")
        sheet.write('B16', d.tva_deductible_10, money)
        sheet.write('A17', "7%")
        sheet.write('B17', d.tva_deductible_7, money)
        sheet.write('A18', _("Total"), bold)
        sheet.write('B18', d.total_tva_deductible, money)

        sheet.write('A20', _("TVA Brute"), bold)
        sheet.write('B20', d.tva_brute, money)
        sheet.write('A21', _("TVA Nette à payer"), bold)
        sheet.write('B21', d.tva_nette, money)

        if self.include_lines and d.declaration_lines:
            row = 23
            headers = [_('Date'), _('Partenaire'), _('Type'), _('Taux'), _('Base HT'), _('TVA')]
            for col, header in enumerate(headers):
                sheet.write(row, col, header, bold)
            row += 1
            for line in d.declaration_lines:
                sheet.write(row, 0, str(line.invoice_date or ''))
                sheet.write(row, 1, line.partner_id.name or '')
                sheet.write(row, 2, dict(line._fields['tax_type'].selection).get(line.tax_type, ''))
                sheet.write(row, 3, line.tax_rate)
                sheet.write(row, 4, line.base_amount, money)
                sheet.write(row, 5, line.tax_amount, money)
                row += 1

        workbook.close()
        file_data = output.getvalue()
        output.close()

        filename = "declaration_tva_%s.xlsx" % (d.name or 'export').replace('/', '_')
        self.write({
            'file_data': base64.b64encode(file_data),
            'filename': filename,
        })
        d.write({
            'export_file': self.file_data,
            'export_filename': filename,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=wizard.tva.export&id=%d&field=file_data&filename=%s&download=true' % (
                self.id, filename,
            ),
            'target': 'self',
        }

    def _export_csv(self):
        d = self.declaration_id
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['Champ', 'Valeur'])
        writer.writerow(['Référence', d.name or ''])
        writer.writerow(['Société', d.company_id.name or ''])
        writer.writerow(['Date début', str(d.date_from or '')])
        writer.writerow(['Date fin', str(d.date_to or '')])
        writer.writerow(['TVA Collectée 20%', d.tva_collecte_20])
        writer.writerow(['TVA Collectée 14%', d.tva_collecte_14])
        writer.writerow(['TVA Collectée 10%', d.tva_collecte_10])
        writer.writerow(['TVA Collectée 7%', d.tva_collecte_7])
        writer.writerow(['Total TVA Collectée', d.total_tva_collecte])
        writer.writerow(['TVA Déductible 20%', d.tva_deductible_20])
        writer.writerow(['TVA Déductible 14%', d.tva_deductible_14])
        writer.writerow(['TVA Déductible 10%', d.tva_deductible_10])
        writer.writerow(['TVA Déductible 7%', d.tva_deductible_7])
        writer.writerow(['Total TVA Déductible', d.total_tva_deductible])
        writer.writerow(['TVA Brute', d.tva_brute])
        writer.writerow(['TVA Nette', d.tva_nette])

        if self.include_lines:
            writer.writerow([])
            writer.writerow(['Date', 'Partenaire', 'Type', 'Taux', 'Base HT', 'TVA'])
            for line in d.declaration_lines:
                writer.writerow([
                    str(line.invoice_date or ''),
                    line.partner_id.name or '',
                    line.tax_type or '',
                    line.tax_rate,
                    line.base_amount,
                    line.tax_amount,
                ])

        file_data = output.getvalue().encode('utf-8-sig')
        output.close()

        filename = "declaration_tva_%s.csv" % (d.name or 'export').replace('/', '_')
        self.write({
            'file_data': base64.b64encode(file_data),
            'filename': filename,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=wizard.tva.export&id=%d&field=file_data&filename=%s&download=true' % (
                self.id, filename,
            ),
            'target': 'self',
        }

    def _export_xml(self):
        d = self.declaration_id
        from xml.sax.saxutils import escape
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_parts.append('<DeclarationTVA>')
        xml_parts.append('  <Reference>%s</Reference>' % escape(d.name or ''))
        xml_parts.append('  <Societe>%s</Societe>' % escape(d.company_id.name or ''))
        xml_parts.append('  <DateDebut>%s</DateDebut>' % (d.date_from or ''))
        xml_parts.append('  <DateFin>%s</DateFin>' % (d.date_to or ''))
        xml_parts.append('  <TVACollectee>')
        xml_parts.append('    <Taux20>%s</Taux20>' % d.tva_collecte_20)
        xml_parts.append('    <Taux14>%s</Taux14>' % d.tva_collecte_14)
        xml_parts.append('    <Taux10>%s</Taux10>' % d.tva_collecte_10)
        xml_parts.append('    <Taux7>%s</Taux7>' % d.tva_collecte_7)
        xml_parts.append('    <Total>%s</Total>' % d.total_tva_collecte)
        xml_parts.append('  </TVACollectee>')
        xml_parts.append('  <TVADeductible>')
        xml_parts.append('    <Taux20>%s</Taux20>' % d.tva_deductible_20)
        xml_parts.append('    <Taux14>%s</Taux14>' % d.tva_deductible_14)
        xml_parts.append('    <Taux10>%s</Taux10>' % d.tva_deductible_10)
        xml_parts.append('    <Taux7>%s</Taux7>' % d.tva_deductible_7)
        xml_parts.append('    <Total>%s</Total>' % d.total_tva_deductible)
        xml_parts.append('  </TVADeductible>')
        xml_parts.append('  <TVABrute>%s</TVABrute>' % d.tva_brute)
        xml_parts.append('  <TVANette>%s</TVANette>' % d.tva_nette)
        xml_parts.append('</DeclarationTVA>')

        file_data = '\n'.join(xml_parts).encode('utf-8')
        filename = "declaration_tva_%s.xml" % (d.name or 'export').replace('/', '_')
        self.write({
            'file_data': base64.b64encode(file_data),
            'filename': filename,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=wizard.tva.export&id=%d&field=file_data&filename=%s&download=true' % (
                self.id, filename,
            ),
            'target': 'self',
        }
