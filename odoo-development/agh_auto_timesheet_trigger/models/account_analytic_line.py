# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    # Champ de marquage pour l'audit
    is_manual_entry = fields.Boolean(string="Saisie Manuelle", default=True, readonly=True)

    @api.constrains('unit_amount', 'date_time', 'date_time_end')
    def _check_time_integrity(self):
        """Vérifie que la durée déclarée est cohérente avec les marqueurs temporels."""
        for line in self:
            # Si les marqueurs Datetime de l'OCA sont présents
            if line.date_time and line.date_time_end:
                # Calcul de la durée réelle en heures
                duration = (line.date_time_end - line.date_time).total_seconds() / 3600.0
                
                # Tolérance de 3 minutes (0.05h) pour les arrondis système
                if abs(line.unit_amount - duration) > 0.05:
                    raise ValidationError(_(
                        "Souveraineté RH : Intégrité violée. "
                        "La durée déclarée (%s) ne correspond pas au temps réel travaillé (%s). "
                        "Toute tentative de modification manuelle est bloquée."
                    ) % (line.unit_amount, round(duration, 2)))

    @api.model_create_multi
    def create(self, vals_list):
        # Sécurité : Seuls les managers peuvent créer des lignes sans chrono
        is_manager = self.env.user.has_group('project.group_project_manager')
        for vals in vals_list:
            if vals.get('date_time') and vals.get('date_time_end'):
                vals['is_manual_entry'] = False
            elif not is_manager:
                raise ValidationError(_("Usage du chronomètre obligatoire pour les stagiaires."))
        return super().create(vals_list)
