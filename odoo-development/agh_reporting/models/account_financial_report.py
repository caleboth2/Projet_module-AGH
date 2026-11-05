from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AccountFinancialReport(models.TransientModel):
    _name = 'account.financial.report'
    _description = 'Rapport financier PCM Maroc'

    name = fields.Char(string='Nom rapport', default='Bilan PCM')
    date_from = fields.Date(string='Date début', required=True)
    date_to = fields.Date(string='Date fin', required=True)
    compare_previous = fields.Boolean(string='Comparer avec N-1', default=True)
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )
    report_type = fields.Selection([
        ('bilan', 'Bilan comptable'),
        ('cpc', 'Compte de Produits et Charges'),
        ('flux', 'Tableau de flux de trésorerie'),
    ], string='Type rapport', required=True)
    analytic_only = fields.Boolean(string='Analytique uniquement')
    include_draft = fields.Boolean(string='Inclure brouillons', default=False)
    bilan_data = fields.Text(string='Données bilan')
    cpc_data = fields.Text(string='Données CPC')
    flux_data = fields.Text(string='Données flux')

    def action_generate_report(self):
        self.ensure_one()
        if self.report_type == 'bilan':
            return self._generate_bilan()
        elif self.report_type == 'cpc':
            return self._generate_cpc()
        elif self.report_type == 'flux':
            return self._generate_flux()
        raise UserError(_("Type de rapport non reconnu"))

    def _generate_bilan(self):
        bilan = {
            'actif': {
                'actif_immobilise': {
                    'immobilisations_incorporelles': self._get_balance_by_prefix(['21']),
                    'immobilisations_corporelles': self._get_balance_by_prefix(['22', '23']),
                    'immobilisations_financieres': self._get_balance_by_prefix(['25', '26']),
                },
                'actif_circulant': {
                    'stocks': self._get_balance_by_prefix(['31', '32', '33', '34', '35']),
                    'creances_clients': self._get_balance_by_prefix(['342']),
                    'autres_creances': self._get_balance_by_prefix(['34', '35', '36', '37']),
                    'tresorerie_actif': self._get_balance_by_prefix(['51', '52', '53', '55']),
                },
            },
            'passif': {
                'capitaux_propres': {
                    'capital': self._get_balance_by_prefix(['111']),
                    'reserves': self._get_balance_by_prefix(['112', '113', '114', '115']),
                    'report_a_nouveau': self._get_balance_by_prefix(['119']),
                    'resultat_exercice': self._get_resultat_exercice(),
                },
                'dettes': {
                    'dettes_financieres': self._get_balance_by_prefix(['16']),
                    'dettes_fournisseurs': self._get_balance_by_prefix(['441']),
                    'dettes_fiscales': self._get_balance_by_prefix(['444', '445']),
                    'dettes_sociales': self._get_balance_by_prefix(['443']),
                    'autres_dettes': self._get_balance_by_prefix(['44']),
                },
            },
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'company_id': self.company_id.id,
        }
        if self.compare_previous:
            bilan['previous'] = {}
        return self._create_print_record(bilan, 'bilan')

    def _generate_cpc(self):
        date_from = str(self.date_from)
        date_to = str(self.date_to)
        produits = {
            'ventes_biens': self._get_lines_credit(['71'], date_from, date_to),
            'ventes_services': self._get_lines_credit(['72'], date_from, date_to),
            'subventions': self._get_lines_credit(['74'], date_from, date_to),
            'autres_produits': self._get_lines_credit(['75', '76', '78'], date_from, date_to),
        }
        charges = {
            'achats_vendus': self._get_lines_debit(['61'], date_from, date_to),
            'autres_achats': self._get_lines_debit(['62'], date_from, date_to),
            'charges_personnel': self._get_lines_debit(['63'], date_from, date_to),
            'impots_taxes': self._get_lines_debit(['64'], date_from, date_to),
            'charges_financieres': self._get_lines_debit(['65'], date_from, date_to),
            'dotations_amortissements': self._get_lines_debit(['68'], date_from, date_to),
            'autres_charges': self._get_lines_debit(['69'], date_from, date_to),
        }
        total_produits = sum(produits.values())
        total_charges = sum(charges.values())
        cpc_data = {
            'produits': produits,
            'charges': charges,
            'total_produits': total_produits,
            'total_charges': total_charges,
            'resultat': total_produits - total_charges,
            'date_from': date_from,
            'date_to': date_to,
            'company_id': self.company_id.id,
        }
        if self.compare_previous:
            cpc_data['previous'] = {}
        return self._create_print_record(cpc_data, 'cpc')

    def _generate_flux(self):
        flux_exploitation = self._get_cash_flow_from_operations()
        flux_investissement = self._get_cash_flow_from_investments()
        flux_financement = self._get_cash_flow_from_financing()
        flux_data = {
            'flux_exploitation': flux_exploitation,
            'flux_investissement': flux_investissement,
            'flux_financement': flux_financement,
            'variation_tresorerie': flux_exploitation + flux_investissement + flux_financement,
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
            'company_id': self.company_id.id,
        }
        return self._create_print_record(flux_data, 'flux')

    def _build_move_line_domain(self, prefixes):
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if not self.include_draft:
            domain.append(('parent_state', '=', 'posted'))
        if len(prefixes) == 1:
            domain.append(('account_id.code', '=like', prefixes[0] + '%'))
        else:
            domain.append(('account_id.code', 'in', [p + '%' for p in prefixes]))
        return domain

    def _get_balance_by_prefix(self, prefixes):
        total = 0.0
        for prefix in prefixes:
            domain = [
                ('company_id', '=', self.company_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('account_id.code', '=like', prefix + '%'),
            ]
            if not self.include_draft:
                domain.append(('parent_state', '=', 'posted'))
            lines = self.env['account.move.line'].search(domain)
            total += sum(lines.mapped('debit')) - sum(lines.mapped('credit'))
        return total

    def _get_lines_credit(self, prefixes, date_from, date_to):
        total = 0.0
        for prefix in prefixes:
            domain = [
                ('account_id.code', '=like', prefix + '%'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
            ]
            lines = self.env['account.move.line'].search(domain)
            total += sum(lines.mapped('credit'))
        return total

    def _get_lines_debit(self, prefixes, date_from, date_to):
        total = 0.0
        for prefix in prefixes:
            domain = [
                ('account_id.code', '=like', prefix + '%'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
            ]
            lines = self.env['account.move.line'].search(domain)
            total += sum(lines.mapped('debit'))
        return total

    def _get_resultat_exercice(self):
        date_from = str(self.date_from)
        date_to = str(self.date_to)
        produits = self._get_lines_credit(['71', '72', '74', '75', '76', '78'], date_from, date_to)
        charges = self._get_lines_debit(['61', '62', '63', '64', '65', '68', '69'], date_from, date_to)
        return produits - charges

    def _get_cash_flow_from_operations(self):
        resultat = self._get_resultat_exercice()
        dotations = self._get_lines_debit(['68'], str(self.date_from), str(self.date_to))
        return resultat + dotations

    def _get_cash_flow_from_investments(self):
        acquisitions = self._get_lines_debit(['21', '22', '23', '24'], str(self.date_from), str(self.date_to))
        cessions = self._get_lines_credit(['751'], str(self.date_from), str(self.date_to))
        return -acquisitions + cessions

    def _get_cash_flow_from_financing(self):
        capital = self._get_lines_credit(['111'], str(self.date_from), str(self.date_to))
        emprunts = self._get_lines_credit(['16'], str(self.date_from), str(self.date_to))
        dividendes = self._get_lines_debit(['116'], str(self.date_from), str(self.date_to))
        return capital + emprunts - dividendes

    def _create_print_record(self, data, report_type):
        print_rec = self.env['account.financial.report.print'].create({
            'report_type': report_type,
            'report_data': str(data),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
        })
        report_xmlid = {
            'bilan': 'agh_reporting.report_bilan_pcm',
            'cpc': 'agh_reporting.report_cpc_pcm',
            'flux': 'agh_reporting.report_flux_tresorerie',
        }.get(report_type)
        if report_xmlid:
            return self.env.ref(report_xmlid).report_action(print_rec)
        return {'type': 'ir.actions.act_window_close'}


class AccountFinancialReportPrint(models.TransientModel):
    _name = 'account.financial.report.print'
    _description = 'Impression rapport financier'

    report_type = fields.Selection([
        ('bilan', 'Bilan'),
        ('cpc', 'CPC'),
        ('flux', 'Flux de trésorerie'),
    ], string='Type rapport')
    report_data = fields.Text(string='Données rapport')
    date_from = fields.Date(string='Date début')
    date_to = fields.Date(string='Date fin')
    company_id = fields.Many2one(
        'res.company', string='Société',
        default=lambda self: self.env.company
    )
    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('both', 'PDF et Excel'),
    ], string='Format sortie', default='pdf')

    def action_print(self):
        self.ensure_one()
        if self.output_format in ('pdf', 'both'):
            report_xmlid = {
                'bilan': 'agh_reporting.report_bilan_pcm',
                'cpc': 'agh_reporting.report_cpc_pcm',
                'flux': 'agh_reporting.report_flux_tresorerie',
            }.get(self.report_type)
            if report_xmlid:
                return self.env.ref(report_xmlid).report_action(self)
        return {'type': 'ir.actions.act_window_close'}
