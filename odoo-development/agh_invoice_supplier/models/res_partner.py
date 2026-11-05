# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    agh_ras_subject = fields.Boolean(
        string='Soumis a RAS',
        default=False,
        help="Ce fournisseur est-il soumis a la retenue a la source ?",
    )
    agh_ras_default_type = fields.Selection(
        selection=[
            ('service', 'Prestation de service'),
            ('travaux', 'Travaux - BTP'),
            ('dividendes', 'Dividendes'),
            ('loyers', 'Loyers'),
            ('honoraires', 'Honoraires'),
            ('commissions', 'Commissions'),
        ],
        string='Type RAS par defaut',
    )
    agh_ras_default_rate = fields.Float(string='Taux RAS par defaut (%)', default=0.0)
    agh_ice = fields.Char(string='ICE', size=15, help="Identifiant Commun de l'Entreprise")
    agh_cnss = fields.Char(string='CNSS', size=10)
    agh_patente = fields.Char(string='Patente')
    agh_rc = fields.Char(string='RC', help="Registre de Commerce")
    agh_tax_id = fields.Char(string='IF', help="Identifiant Fiscal")
    agh_strategic_supplier = fields.Boolean(
        string='Fournisseur strategique',
        default=False,
        help="Necessite validation DAF",
    )
