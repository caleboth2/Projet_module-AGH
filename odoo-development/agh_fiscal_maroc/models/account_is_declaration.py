# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountIsDeclaration(models.Model):
    _name = 'account.is.declaration'
    _description = 'Déclaration IS Maroc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fiscal_year desc'

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

    fiscal_year = fields.Char(string="Exercice fiscal", required=True, tracking=True)
    date_from = fields.Date(string="Date début")
    date_to = fields.Date(string="Date fin")

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

    # Résultat fiscal
    accounting_result = fields.Monetary(
        string="Résultat comptable", currency_field='currency_id'
    )
    fiscal_reintegration = fields.Monetary(
        string="Réintégrations fiscales", currency_field='currency_id'
    )
    fiscal_deduction = fields.Monetary(
        string="Déductions fiscales", currency_field='currency_id'
    )
    fiscal_result = fields.Monetary(
        string="Résultat fiscal",
        compute='_compute_fiscal_result',
        store=True,
        currency_field='currency_id',
    )

    # Type société et taux IS
    company_type = fields.Selection(
        selection=[
            ('pme', 'PME (CA < 3M MAD)'),
            ('normal', 'Normal'),
        ],
        string="Type société",
        default='normal',
    )
    is_rate = fields.Float(
        string="Taux IS (%)",
        compute='_compute_is_rate',
        store=True,
    )
    is_amount = fields.Monetary(
        string="Montant IS",
        compute='_compute_is_amount',
        store=True,
        currency_field='currency_id',
    )

    # Cotisation Minimale
    cm_amount = fields.Monetary(string="Cotisation Minimale", currency_field='currency_id')
    cm_base = fields.Monetary(string="Base CM (CA TTC)", currency_field='currency_id')
    cm_rate = fields.Float(string="Taux CM (%)", default=0.5)
    is_higher_than_cm = fields.Boolean(
        string="IS > CM",
        compute='_compute_comparison',
    )
    amount_to_pay = fields.Monetary(
        string="IS retenu (max IS/CM)",
        compute='_compute_amount_to_pay',
        store=True,
        currency_field='currency_id',
    )

    # Acomptes provisionnels
    acompte_t1 = fields.Monetary(string="Acompte T1 (Mars)", currency_field='currency_id')
    acompte_t2 = fields.Monetary(string="Acompte T2 (Juin)", currency_field='currency_id')
    acompte_t3 = fields.Monetary(string="Acompte T3 (Septembre)", currency_field='currency_id')
    acompte_t4 = fields.Monetary(string="Acompte T4 (Décembre)", currency_field='currency_id')
    total_acomptes = fields.Monetary(
        string="Total acomptes versés",
        compute='_compute_total_acomptes',
        store=True,
        currency_field='currency_id',
    )

    # Solde
    solde_is = fields.Monetary(
        string="Solde IS à payer",
        compute='_compute_solde',
        store=True,
        currency_field='currency_id',
    )
    credit_is = fields.Monetary(
        string="Crédit IS",
        compute='_compute_solde',
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

    # Documents
    liasse_fiscale = fields.Binary(string="Liasse fiscale", copy=False)
    liasse_filename = fields.Char(string="Nom fichier liasse", copy=False)

    submitted_date = fields.Date(string="Date de soumission", copy=False)
    payment_date = fields.Date(string="Date de paiement", copy=False)

    acompte_lines = fields.One2many(
        'is.acompte.line', 'declaration_id', string="Lignes acomptes"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'account.is.declaration'
                ) or _('New')
        return super().create(vals_list)

    @api.depends('name', 'fiscal_year')
    def _compute_display_name(self):
        for record in self:
            if record.fiscal_year:
                record.display_name = "IS %s - %s" % (record.fiscal_year, record.name or '')
            else:
                record.display_name = record.name or _('New')

    @api.depends('accounting_result', 'fiscal_reintegration', 'fiscal_deduction')
    def _compute_fiscal_result(self):
        for record in self:
            record.fiscal_result = (
                record.accounting_result + record.fiscal_reintegration - record.fiscal_deduction
            )

    @api.depends('company_type')
    def _compute_is_rate(self):
        for record in self:
            # Loi de finances Maroc : 20% pour PME et taux normal sur la période courante
            record.is_rate = 20.0

    @api.depends('fiscal_result', 'is_rate')
    def _compute_is_amount(self):
        for record in self:
            if record.fiscal_result > 0:
                record.is_amount = record.fiscal_result * (record.is_rate / 100.0)
            else:
                record.is_amount = 0.0

    @api.depends('is_amount', 'cm_amount')
    def _compute_comparison(self):
        for record in self:
            record.is_higher_than_cm = record.is_amount > record.cm_amount

    @api.depends('is_amount', 'cm_amount')
    def _compute_amount_to_pay(self):
        for record in self:
            record.amount_to_pay = max(record.is_amount, record.cm_amount)

    @api.depends('acompte_t1', 'acompte_t2', 'acompte_t3', 'acompte_t4')
    def _compute_total_acomptes(self):
        for record in self:
            record.total_acomptes = (
                record.acompte_t1 + record.acompte_t2
                + record.acompte_t3 + record.acompte_t4
            )

    @api.depends('amount_to_pay', 'total_acomptes')
    def _compute_solde(self):
        for record in self:
            diff = record.amount_to_pay - record.total_acomptes
            if diff > 0:
                record.solde_is = diff
                record.credit_is = 0.0
            else:
                record.solde_is = 0.0
                record.credit_is = -diff

    @api.depends('solde_is', 'penalties')
    def _compute_total_a_payer(self):
        for record in self:
            record.total_a_payer = record.solde_is + record.penalties

    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------
    def action_calculate_from_accounts(self):
        """Calculer l'IS à partir des comptes comptables (point d'extension)."""
        for record in self:
            record.state = 'calculated'
        return True

    def action_calculate_cm(self):
        for record in self:
            if record.cm_base:
                record.cm_amount = record.cm_base * (record.cm_rate / 100.0)
        return True

    def action_generate_liasse(self):
        """Générer la liasse fiscale (rapport PDF)."""
        self.ensure_one()
        self.state = 'confirmed'
        return self.env.ref('agh_fiscal_maroc.report_liasse_fiscale').report_action(self)

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_submit_dgi(self):
        for record in self:
            record.write({
                'state': 'submitted',
                'submitted_date': fields.Date.today(),
            })

    def action_pay(self):
        for record in self:
            record.write({
                'state': 'paid',
                'payment_date': fields.Date.today(),
            })

    def action_open_acompte_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Acompte IS'),
            'res_model': 'wizard.is.acompte',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_declaration_id': self.id},
        }


class IsAcompteLine(models.Model):
    _name = 'is.acompte.line'
    _description = 'Ligne acompte IS'
    _order = 'trimester'

    declaration_id = fields.Many2one(
        'account.is.declaration',
        string="Déclaration IS",
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
    trimester = fields.Selection(
        selection=[
            ('t1', 'T1 - Mars'),
            ('t2', 'T2 - Juin'),
            ('t3', 'T3 - Septembre'),
            ('t4', 'T4 - Décembre'),
        ],
        string="Trimestre",
        required=True,
    )
    amount = fields.Monetary(string="Montant", currency_field='currency_id')
    payment_date = fields.Date(string="Date paiement")
    payment_ref = fields.Char(string="Référence paiement")
    is_paid = fields.Boolean(string="Payé")
