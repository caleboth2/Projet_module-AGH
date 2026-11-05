# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ----- OCR / Import -----
    agh_supplier_invoice_ref = fields.Char(
        string='Ref. Facture Fournisseur',
        copy=False,
        help='Numero de facture fournisseur original',
    )
    agh_ocr_imported = fields.Boolean(
        string='Importe par OCR',
        default=False,
        copy=False,
    )
    agh_ocr_confidence = fields.Float(
        string='Confiance OCR (%)',
        default=0.0,
        help='Niveau de confiance de la reconnaissance OCR',
    )
    agh_ocr_raw_data = fields.Text(string='Donnees OCR brutes', copy=False)
    agh_import_queue_status = fields.Selection(
        selection=[
            ('pending', 'En attente'),
            ('processing', 'En traitement'),
            ('completed', 'Termine'),
            ('error', 'Erreur'),
        ],
        string='Statut import',
        default='pending',
        copy=False,
    )
    agh_import_error = fields.Text(string='Erreur import', copy=False)

    # ----- Validation multi-niveaux -----
    agh_validation_level = fields.Selection(
        selection=[
            ('level1', 'Niveau 1 - Comptable'),
            ('level2', 'Niveau 2 - Responsable Achats'),
            ('level3', 'Niveau 3 - Directeur Financier'),
        ],
        string='Niveau validation requis',
        compute='_compute_validation_level',
        store=True,
    )
    agh_validation_status = fields.Selection(
        selection=[
            ('draft', 'Brouillon'),
            ('level1_approved', 'Valide Niveau 1'),
            ('level2_approved', 'Valide Niveau 2'),
            ('level3_approved', 'Valide Niveau 3'),
            ('rejected', 'Rejete'),
            ('posted', 'Comptabilise'),
        ],
        string='Statut validation',
        default='draft',
        copy=False,
        tracking=True,
    )
    agh_level1_approved_by = fields.Many2one('res.users', string='Valide N1 par', copy=False)
    agh_level1_approved_date = fields.Datetime(string='Date validation N1', copy=False)
    agh_level2_approved_by = fields.Many2one('res.users', string='Valide N2 par', copy=False)
    agh_level2_approved_date = fields.Datetime(string='Date validation N2', copy=False)
    agh_level3_approved_by = fields.Many2one('res.users', string='Valide N3 par', copy=False)
    agh_level3_approved_date = fields.Datetime(string='Date validation N3', copy=False)
    agh_rejection_reason = fields.Text(string='Motif rejet', copy=False)

    # ----- 3-way match -----
    agh_3way_match_status = fields.Selection(
        selection=[
            ('not_started', 'Non demarre'),
            ('in_progress', 'En cours'),
            ('matched', 'Rapproche'),
            ('mismatch', 'Ecart detecte'),
            ('approved', 'Approuve'),
        ],
        string='Statut 3-Way Match',
        default='not_started',
        compute='_compute_3way_status',
        store=True,
        readonly=False,
    )
    agh_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Bon de commande',
        help='Bon de commande lie',
    )
    agh_stock_picking_ids = fields.Many2many(
        'stock.picking',
        relation='agh_invoice_picking_rel',
        column1='invoice_id',
        column2='picking_id',
        string='Bons de reception',
        help='Bons de reception lies',
    )
    agh_price_tolerance = fields.Float(string='Tolerance prix (%)', default=5.0)
    agh_qty_tolerance = fields.Float(string='Tolerance quantite (%)', default=10.0)
    agh_price_deviation = fields.Float(
        string='Ecart prix (%)',
        compute='_compute_deviations',
        store=True,
    )
    agh_qty_deviation = fields.Float(
        string='Ecart quantite (%)',
        compute='_compute_deviations',
        store=True,
    )
    agh_match_details = fields.Text(
        string='Details rapprochement',
        compute='_compute_deviations',
        store=True,
    )

    # ----- RAS -----
    agh_ras_ids = fields.One2many(
        'account.ras.maroc',
        'invoice_id',
        string='Retenues a la source',
    )
    agh_ras_total = fields.Monetary(
        string='Total RAS',
        compute='_compute_ras_total',
        store=True,
        currency_field='currency_id',
    )
    agh_net_to_pay = fields.Monetary(
        string='Net a payer',
        compute='_compute_net_to_pay',
        store=True,
        currency_field='currency_id',
    )

    # ============ COMPUTES ============

    @api.depends('amount_total', 'agh_ras_total')
    def _compute_net_to_pay(self):
        for move in self:
            amount_total = move.amount_total or 0.0
            ras_total = move.agh_ras_total or 0.0
            move.agh_net_to_pay = amount_total - ras_total

    @api.depends('agh_ras_ids.ras_amount')
    def _compute_ras_total(self):
        for move in self:
            move.agh_ras_total = sum(move.agh_ras_ids.mapped('ras_amount'))

    @api.depends('amount_total', 'move_type')
    def _compute_validation_level(self):
        for move in self:
            if move.move_type != 'in_invoice':
                move.agh_validation_level = False
                continue
            amount = move.amount_total or 0.0
            if amount > 50000:
                move.agh_validation_level = 'level3'
            elif amount > 10000:
                move.agh_validation_level = 'level2'
            else:
                move.agh_validation_level = 'level1'

    @api.depends(
        'agh_purchase_order_id',
        'invoice_line_ids',
        'invoice_line_ids.product_id',
        'invoice_line_ids.price_unit',
        'invoice_line_ids.quantity',
    )
    def _compute_deviations(self):
        for move in self:
            if not move.agh_purchase_order_id:
                move.agh_price_deviation = 0.0
                move.agh_qty_deviation = 0.0
                move.agh_match_details = "Aucun bon de commande lie"
                continue

            po = move.agh_purchase_order_id
            details = []
            price_deviations = []
            qty_deviations = []

            for line in move.invoice_line_ids:
                if not line.product_id:
                    continue
                po_lines = po.order_line.filtered(lambda l: l.product_id == line.product_id)
                if not po_lines:
                    continue
                po_line = po_lines[:1]
                po_price = po_line.price_unit or 0.0
                inv_price = line.price_unit or 0.0
                if po_price > 0:
                    price_dev = abs((inv_price - po_price) / po_price * 100.0)
                    price_deviations.append(price_dev)
                    if price_dev > (move.agh_price_tolerance or 0.0):
                        details.append(
                            "Produit %s: ecart prix %.1f%%" % (line.product_id.display_name, price_dev)
                        )
                po_qty = po_line.product_qty or 0.0
                inv_qty = line.quantity or 0.0
                if po_qty > 0:
                    qty_dev = abs((inv_qty - po_qty) / po_qty * 100.0)
                    qty_deviations.append(qty_dev)
                    if qty_dev > (move.agh_qty_tolerance or 0.0):
                        details.append(
                            "Produit %s: ecart quantite %.1f%%" % (line.product_id.display_name, qty_dev)
                        )

            move.agh_price_deviation = max(price_deviations) if price_deviations else 0.0
            move.agh_qty_deviation = max(qty_deviations) if qty_deviations else 0.0
            if details:
                move.agh_match_details = "\n".join(details)
            else:
                move.agh_match_details = "Tous les ecarts sont dans les limites autorisees"

    @api.depends(
        'agh_purchase_order_id',
        'agh_price_deviation',
        'agh_qty_deviation',
        'agh_price_tolerance',
        'agh_qty_tolerance',
        'move_type',
    )
    def _compute_3way_status(self):
        for move in self:
            if move.move_type != 'in_invoice' or not move.agh_purchase_order_id:
                move.agh_3way_match_status = 'not_started'
                continue
            price_dev = move.agh_price_deviation or 0.0
            qty_dev = move.agh_qty_deviation or 0.0
            price_tol = move.agh_price_tolerance or 0.0
            qty_tol = move.agh_qty_tolerance or 0.0
            if price_dev > price_tol or qty_dev > qty_tol:
                move.agh_3way_match_status = 'mismatch'
            else:
                move.agh_3way_match_status = 'matched'

    # ============ ACTIONS ============

    def action_validate_level1(self):
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("Seuls les comptables peuvent valider niveau 1."))
        self.write({
            'agh_validation_status': 'level1_approved',
            'agh_level1_approved_by': self.env.user.id,
            'agh_level1_approved_date': fields.Datetime.now(),
        })
        if self.agh_validation_level == 'level1':
            return self.action_post()
        return True

    def action_validate_level2(self):
        self.ensure_one()
        if not self.env.user.has_group('purchase.group_purchase_manager'):
            raise AccessError(_("Seuls les responsables achats peuvent valider niveau 2."))
        if self.agh_validation_status != 'level1_approved':
            raise UserError(_("La validation niveau 1 est requise d'abord."))
        self.write({
            'agh_validation_status': 'level2_approved',
            'agh_level2_approved_by': self.env.user.id,
            'agh_level2_approved_date': fields.Datetime.now(),
        })
        if self.agh_validation_level == 'level2':
            return self.action_post()
        return True

    def action_validate_level3(self):
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError(_("Seuls les directeurs financiers peuvent valider niveau 3."))
        if self.agh_validation_status != 'level2_approved':
            raise UserError(_("La validation niveau 2 est requise d'abord."))
        self.write({
            'agh_validation_status': 'level3_approved',
            'agh_level3_approved_by': self.env.user.id,
            'agh_level3_approved_date': fields.Datetime.now(),
        })
        return self.action_post()

    def action_reject_invoice(self):
        self.ensure_one()
        self.write({'agh_validation_status': 'rejected'})
        return True

    def action_3way_match(self):
        self.ensure_one()
        return {
            'name': _('Rapprochement 3 voies'),
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.3way.match',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_invoice_id': self.id},
        }

    def action_post(self):
        for move in self:
            if move.move_type != 'in_invoice':
                continue
            required_level = move.agh_validation_level
            current_status = move.agh_validation_status
            allowed = {
                'level1': ('level1_approved', 'level2_approved', 'level3_approved'),
                'level2': ('level2_approved', 'level3_approved'),
                'level3': ('level3_approved',),
            }
            if required_level and current_status not in allowed.get(required_level, ()):
                level_label = dict(self._fields['agh_validation_level'].selection).get(
                    required_level, required_level,
                )
                raise UserError(_(
                    "Cette facture necessite une validation %s avant comptabilisation."
                ) % level_label)
            if move.agh_purchase_order_id and move.agh_3way_match_status == 'mismatch':
                raise UserError(_(
                    "Des ecarts ont ete detectes dans le rapprochement 3 voies. "
                    "Veuillez les resoudre avant validation."
                ))
        result = super().action_post()
        for move in self:
            if move.move_type == 'in_invoice':
                move.agh_validation_status = 'posted'
        return result
