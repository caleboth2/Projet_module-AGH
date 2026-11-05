# -*- coding: utf-8 -*-
import base64
import csv
import io
import logging
from datetime import datetime

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser
except ImportError:
    OfxParser = None
    _logger.info("ofxparse non disponible; l'import OFX sera desactive.")


class WizardImportStatement(models.TransientModel):
    _name = 'wizard.import.statement'
    _description = 'Wizard import releve bancaire'

    statement_id = fields.Many2one('account.bank.statement', string='Releve bancaire')
    format = fields.Selection(
        selection=[
            ('ofx', 'OFX'),
            ('csv', 'CSV'),
            ('camt053', 'CAMT.053'),
        ],
        string='Format du fichier',
        required=True,
        default='csv',
    )
    file = fields.Binary(string='Fichier', required=True)
    filename = fields.Char(string='Nom du fichier')
    csv_delimiter = fields.Char(string='Separateur CSV', default=',')
    csv_date_format = fields.Char(string='Format date', default='%d/%m/%Y')
    csv_columns_mapping = fields.Text(
        string='Mapping colonnes',
        default="date:date\nmontant:amount\nlibelle:ref",
        help="Format: colonne_fichier:colonne_odoo (un par ligne)",
    )

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Veuillez selectionner un fichier"))
        file_content = base64.b64decode(self.file)
        try:
            if self.format == 'ofx':
                lines = self._parse_ofx(file_content)
            elif self.format == 'csv':
                lines = self._parse_csv(file_content)
            elif self.format == 'camt053':
                lines = self._parse_camt053(file_content)
            else:
                raise UserError(_("Format non supporte"))
            statement = self._create_or_update_statement(lines)
            self._create_statement_lines(statement, lines)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.bank.statement',
                'view_mode': 'form',
                'res_id': statement.id,
            }
        except Exception as e:
            _logger.error("Erreur import: %s", e)
            raise UserError(_("Erreur lors de l'import: %s") % str(e))

    def _parse_ofx(self, file_content):
        if OfxParser is None:
            raise UserError(_("La librairie 'ofxparse' n'est pas installee."))
        lines = []
        with io.BytesIO(file_content) as f:
            ofx = OfxParser.parse(f)
            for account in ofx.accounts:
                for transaction in account.statement.transactions:
                    lines.append({
                        'date': transaction.date.date(),
                        'amount': float(transaction.amount),
                        'ref': transaction.payee or transaction.memo or '',
                        'memo': transaction.memo,
                    })
        return lines

    def _parse_csv(self, file_content):
        lines = []
        mapping = {}
        if self.csv_columns_mapping:
            for line in self.csv_columns_mapping.strip().split('\n'):
                if ':' in line:
                    file_col, odoo_col = line.split(':', 1)
                    mapping[file_col.strip()] = odoo_col.strip()
        try:
            content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            content = file_content.decode('latin-1')
        reader = csv.DictReader(io.StringIO(content), delimiter=self.csv_delimiter or ',')
        for row in reader:
            line = {}
            for file_col, odoo_col in mapping.items():
                if file_col in row:
                    if odoo_col == 'date':
                        try:
                            line['date'] = datetime.strptime(row[file_col], self.csv_date_format).date()
                        except (ValueError, TypeError):
                            line['date'] = fields.Date.today()
                    elif odoo_col == 'amount':
                        amount_str = (row[file_col] or '').replace(' ', '').replace(',', '.')
                        try:
                            line['amount'] = float(amount_str) if amount_str else 0.0
                        except ValueError:
                            line['amount'] = 0.0
                    else:
                        line[odoo_col] = row[file_col]
            if line:
                lines.append(line)
        return lines

    def _parse_camt053(self, file_content):
        return []

    def _create_or_update_statement(self, lines):
        if self.statement_id:
            return self.statement_id
        dates = [l['date'] for l in lines if 'date' in l]
        start_date = min(dates) if dates else fields.Date.today()
        end_date = max(dates) if dates else fields.Date.today()
        return self.env['account.bank.statement'].create({
            'name': "Releve %s - %s" % (start_date, end_date),
            'journal_id': self._get_bank_journal().id,
            'date': end_date,
        })

    def _create_statement_lines(self, statement, lines):
        existing_refs = set(statement.line_ids.mapped('payment_ref'))
        for line in lines:
            ref = line.get('ref', '')
            if ref and ref in existing_refs:
                continue
            self.env['account.bank.statement.line'].create({
                'statement_id': statement.id,
                'journal_id': statement.journal_id.id,
                'date': line.get('date', fields.Date.today()),
                'amount': line.get('amount', 0.0),
                'payment_ref': ref or _('Operation'),
            })

    def _get_bank_journal(self):
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not journal:
            raise UserError(_("Aucun journal bancaire trouve. Veuillez en creer un d'abord."))
        return journal
