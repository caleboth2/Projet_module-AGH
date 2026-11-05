# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    """
    Étend res.company pour la date de verrouillage comptable globale
    (équivalent du « Lock Date » Odoo standard mais piloté par AGH).
    """
    _inherit = 'res.company'

    agh_fiscalyear_lock_date = fields.Date(
        string="Date de verrouillage (tous utilisateurs)",
        help="Aucune écriture comptable ne peut être créée ou modifiée "
             "à cette date ou avant, pour aucun utilisateur."
    )
    agh_period_lock_date = fields.Date(
        string="Date de verrouillage (non-conseiller)",
        help="Aucune écriture comptable ne peut être créée ou modifiée "
             "à cette date ou avant pour les utilisateurs non comptables."
    )
