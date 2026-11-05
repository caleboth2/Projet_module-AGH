# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WizardIsAcompte(models.TransientModel):
    _name = 'wizard.is.acompte'
    _description = "Assistant de paiement d'acompte IS"

    declaration_id = fields.Many2one(
        'account.is.declaration',
        string="Déclaration IS",
        required=True,
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
        default='t1',
    )
    amount = fields.Monetary(
        string="Montant",
        currency_field='currency_id',
        required=True,
    )
    payment_date = fields.Date(
        string="Date paiement",
        default=fields.Date.context_today,
        required=True,
    )
    payment_ref = fields.Char(string="Référence")
    currency_id = fields.Many2one(
        'res.currency',
        related='declaration_id.currency_id',
        readonly=True,
    )

    @api.onchange('declaration_id', 'trimester')
    def _onchange_suggest_amount(self):
        if self.declaration_id and self.trimester:
            # Suggérer 25% du montant IS de référence
            self.amount = (self.declaration_id.amount_to_pay or 0.0) * 0.25

    def action_register_acompte(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Le montant de l'acompte doit être positif."))
        # Mettre à jour le champ acompte du trimestre dans la déclaration
        field_map = {
            't1': 'acompte_t1',
            't2': 'acompte_t2',
            't3': 'acompte_t3',
            't4': 'acompte_t4',
        }
        field_name = field_map[self.trimester]
        self.declaration_id.write({field_name: self.amount})
        # Créer la ligne d'acompte associée
        self.env['is.acompte.line'].create({
            'declaration_id': self.declaration_id.id,
            'trimester': self.trimester,
            'amount': self.amount,
            'payment_date': self.payment_date,
            'payment_ref': self.payment_ref or '',
            'is_paid': True,
        })
        return {'type': 'ir.actions.act_window_close'}
