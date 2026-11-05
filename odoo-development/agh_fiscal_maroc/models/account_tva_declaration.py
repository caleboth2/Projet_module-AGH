# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountTvaDeclaration(models.Model):
    _name = 'account.tva.declaration'
    _description = 'Déclaration TVA Maroc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
    )

    date_from = fields.Date(string="Date début", required=True, tracking=True)
    date_to = fields.Date(string="Date fin", required=True, tracking=True)
    period_type = fields.Selection(
        selection=[
            ('monthly', 'Mensuelle'),
            ('quarterly', 'Trimestrielle'),
        ],
        string="Type de période",
        required=True,
        default='monthly',
        tracking=True,
    )

    fiscal_year = fields.Char(
        string="Exercice fiscal",
        compute='_compute_fiscal_year',
        store=True,
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('calculated', 'Calculée'),
            ('confirmed', 'Confirmée'),
            ('submitted', 'Soumise à la DGI'),
            ('paid', 'Payée'),
            ('cancelled', 'Annulée'),
        ],
        string="Statut",
        default='draft',
        tracking=True,
        copy=False,
    )

    # TVA Collectée (Ventes)
    tva_collecte_20 = fields.Monetary(string="TVA Collectée 20%", currency_field='currency_id')
    tva_collecte_14 = fields.Monetary(string="TVA Collectée 14%", currency_field='currency_id')
    tva_collecte_10 = fields.Monetary(string="TVA Collectée 10%", currency_field='currency_id')
    tva_collecte_7 = fields.Monetary(string="TVA Collectée 7%", currency_field='currency_id')
    total_tva_collecte = fields.Monetary(
        string="Total TVA Collectée",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )

    # TVA Déductible (Achats)
    tva_deductible_20 = fields.Monetary(string="TVA Déductible 20%", currency_field='currency_id')
    tva_deductible_14 = fields.Monetary(string="TVA Déductible 14%", currency_field='currency_id')
    tva_deductible_10 = fields.Monetary(string="TVA Déductible 10%", currency_field='currency_id')
    tva_deductible_7 = fields.Monetary(string="TVA Déductible 7%", currency_field='currency_id')
    total_tva_deductible = fields.Monetary(
        string="Total TVA Déductible",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )

    # Calculs
    tva_brute = fields.Monetary(
        string="TVA Brute",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    credit_anterieur = fields.Monetary(string="Crédit antérieur", currency_field='currency_id')
    tva_nette = fields.Monetary(
        string="TVA Nette à payer",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )
    credit_tva = fields.Monetary(
        string="Crédit de TVA",
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
    )

    # Pénalités
    penalties = fields.Monetary(string="Pénalités", currency_field='currency_id')
    total_a_payer = fields.Monetary(
        string="Total à payer",
        compute='_compute_total_a_payer',
        store=True,
        currency_field='currency_id',
    )

    declaration_lines = fields.One2many(
        'account.tva.declaration.line',
        'declaration_id',
        string="Lignes de déclaration",
    )

    submitted_date = fields.Date(string="Date de soumission", copy=False)
    payment_date = fields.Date(string="Date de paiement", copy=False)
    payment_ref = fields.Char(string="Référence de paiement", copy=False)
    bank_ref = fields.Char(string="Référence bancaire", copy=False)

    export_file = fields.Binary(string="Fichier export DGI", copy=False)
    export_filename = fields.Char(string="Nom du fichier", copy=False)

    invoice_count = fields.Integer(
        string="Nombre de factures",
        compute='_compute_invoice_count',
    )

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'account.tva.declaration'
                ) or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------
    # Display name (Odoo standard hook)
    # ------------------------------------------------------------
    @api.depends('name', 'date_from', 'date_to')
    def _compute_display_name(self):
        for record in self:
            if record.date_from and record.date_to:
                record.display_name = "%s - %s au %s" % (
                    record.name or '',
                    record.date_from.strftime('%d/%m/%Y'),
                    record.date_to.strftime('%d/%m/%Y'),
                )
            else:
                record.display_name = record.name or _('New')

    # ------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------
    @api.depends('date_from')
    def _compute_fiscal_year(self):
        for record in self:
            if record.date_from:
                record.fiscal_year = str(record.date_from.year)
            else:
                record.fiscal_year = False

    @api.depends(
        'tva_collecte_20', 'tva_collecte_14', 'tva_collecte_10', 'tva_collecte_7',
        'tva_deductible_20', 'tva_deductible_14', 'tva_deductible_10', 'tva_deductible_7',
        'credit_anterieur',
    )
    def _compute_totals(self):
        for record in self:
            collecte = (
                record.tva_collecte_20 + record.tva_collecte_14
                + record.tva_collecte_10 + record.tva_collecte_7
            )
            deductible = (
                record.tva_deductible_20 + record.tva_deductible_14
                + record.tva_deductible_10 + record.tva_deductible_7
            )
            brute = collecte - deductible
            record.total_tva_collecte = collecte
            record.total_tva_deductible = deductible
            record.tva_brute = brute
            if brute >= 0:
                record.tva_nette = brute
                record.credit_tva = 0.0
            else:
                record.tva_nette = 0.0
                record.credit_tva = -brute + record.credit_anterieur

    @api.depends('tva_nette', 'penalties')
    def _compute_total_a_payer(self):
        for record in self:
            record.total_a_payer = record.tva_nette + record.penalties

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_invoice_count(self):
        AccountMove = self.env['account.move']
        for record in self:
            if record.date_from and record.date_to and record.company_id:
                record.invoice_count = AccountMove.search_count([
                    ('company_id', '=', record.company_id.id),
                    ('state', '=', 'posted'),
                    ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                    ('date', '>=', record.date_from),
                    ('date', '<=', record.date_to),
                ])
            else:
                record.invoice_count = 0

    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------
    def action_calculate_from_invoices(self):
        """Calculer la TVA à partir des factures de la période."""
        AccountMove = self.env['account.move']
        for record in self:
            invoices = AccountMove.search([
                ('company_id', '=', record.company_id.id),
                ('state', '=', 'posted'),
                ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                ('date', '>=', record.date_from),
                ('date', '<=', record.date_to),
            ])

            totals = {
                'tva_collecte_20': 0.0, 'tva_collecte_14': 0.0,
                'tva_collecte_10': 0.0, 'tva_collecte_7': 0.0,
                'tva_deductible_20': 0.0, 'tva_deductible_14': 0.0,
                'tva_deductible_10': 0.0, 'tva_deductible_7': 0.0,
            }
            line_vals_list = []

            for invoice in invoices:
                is_sale = invoice.move_type in ('out_invoice', 'out_refund')
                tax_type = 'collecte' if is_sale else 'deductible'
                for line in invoice.invoice_line_ids:
                    if not line.tax_ids:
                        continue
                    base = line.price_subtotal
                    for tax in line.tax_ids:
                        rate = tax.amount or 0.0
                        tax_amount = base * (rate / 100.0)
                        rate_int = int(rate)
                        key_prefix = 'tva_collecte_' if is_sale else 'tva_deductible_'
                        key = "%s%d" % (key_prefix, rate_int)
                        if key in totals:
                            totals[key] += tax_amount
                        line_vals_list.append((0, 0, {
                            'invoice_id': invoice.id,
                            'partner_id': invoice.partner_id.id,
                            'invoice_date': invoice.invoice_date or invoice.date,
                            'tax_rate': rate,
                            'base_amount': base,
                            'tax_amount': tax_amount,
                            'tax_type': tax_type,
                        }))

            record.declaration_lines.unlink()
            update_vals = dict(totals)
            update_vals['declaration_lines'] = line_vals_list
            update_vals['state'] = 'calculated'
            record.write(update_vals)
        return True

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'
        return True

    def action_submit_dgi(self):
        """Soumettre à la DGI (génère un fichier d'export)."""
        self.ensure_one()
        wizard = self.env['wizard.tva.export'].create({
            'declaration_id': self.id,
            'export_format': 'excel',
        })
        action = wizard.action_export()
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Date.today(),
        })
        return action

    def action_pay(self):
        for record in self:
            record.write({
                'state': 'paid',
                'payment_date': fields.Date.today(),
            })
        return True

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'
        return True

    def action_draft(self):
        for record in self:
            record.state = 'draft'
        return True

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factures'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'posted'),
                ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ],
            'context': {'default_date': self.date_from},
        }

    def action_export_dgi(self):
        self.ensure_one()
        wizard = self.env['wizard.tva.export'].create({
            'declaration_id': self.id,
            'export_format': 'excel',
        })
        return wizard.action_export()

    def action_request_credit_refund(self):
        """Générer une demande de remboursement de crédit TVA."""
        self.ensure_one()
        if self.credit_tva <= 0:
            raise ValidationError(_("Pas de crédit TVA à rembourser."))
        request = self.env['tva.credit.request'].create({
            'declaration_id': self.id,
            'amount': self.credit_tva,
            'date_request': fields.Date.today(),
            'company_id': self.company_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tva.credit.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }


class AccountTvaDeclarationLine(models.Model):
    _name = 'account.tva.declaration.line'
    _description = 'Ligne de déclaration TVA'

    declaration_id = fields.Many2one(
        'account.tva.declaration',
        string="Déclaration",
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        related='declaration_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='declaration_id.currency_id',
        store=True,
    )
    invoice_id = fields.Many2one('account.move', string="Facture")
    partner_id = fields.Many2one('res.partner', string="Partenaire")
    invoice_date = fields.Date(string="Date facture")
    tax_rate = fields.Float(string="Taux TVA")
    base_amount = fields.Monetary(string="Base HT", currency_field='currency_id')
    tax_amount = fields.Monetary(string="Montant TVA", currency_field='currency_id')
    tax_type = fields.Selection(
        selection=[
            ('collecte', 'Collectée'),
            ('deductible', 'Déductible'),
        ],
        string="Type",
    )


class TvaCreditRequest(models.Model):
    _name = 'tva.credit.request'
    _description = 'Demande de remboursement crédit TVA'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc'

    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    declaration_id = fields.Many2one(
        'account.tva.declaration',
        string="Déclaration TVA",
        ondelete='set null',
    )
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
    )
    amount = fields.Monetary(string="Montant demandé", currency_field='currency_id')
    date_request = fields.Date(string="Date demande", default=fields.Date.context_today)
    state = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('submitted', 'Soumise'),
            ('approved', 'Approuvée'),
            ('rejected', 'Rejetée'),
            ('reimbursed', 'Remboursée'),
        ],
        string="Statut",
        default='draft',
        tracking=True,
        copy=False,
    )
    rejection_reason = fields.Text(string="Motif du rejet")
    reimbursement_date = fields.Date(string="Date remboursement")
    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'tva.credit.request'
                ) or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for record in self:
            record.state = 'submitted'

    def action_approve(self):
        for record in self:
            record.state = 'approved'

    def action_reject(self):
        for record in self:
            record.state = 'rejected'

    def action_reimburse(self):
        for record in self:
            record.write({
                'state': 'reimbursed',
                'reimbursement_date': fields.Date.today(),
            })
