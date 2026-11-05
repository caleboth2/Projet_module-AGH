from odoo import models, fields, api
from odoo.exceptions import ValidationError  # type: ignore[reportMissingImports]
from datetime import datetime

class HrContract(models.Model):
    _inherit = 'hr.contract'

    # Séquence générée automatiquement
    name = fields.Char(
        string='Référence du Contrat',
        required=True,
        default='Nouveau',
        copy=False
    )

    def action_validate_contract(self):
        """Méthode de validation pour attribuer la séquence dynamique"""
        for contract in self:
            if contract.name == 'Nouveau' or not contract.name:
                contract._generate_contract_sequence()
        # Si une méthode parente existe dans Odoo pour l'ouverture du contrat
        if hasattr(super(HrContract, self), 'action_state_open'):
            return super(HrContract, self).action_state_open()
        return True

    def _generate_contract_sequence(self):
        self.ensure_one()
        dept = self.department_id or (self.employee_id.department_id if self.employee_id else False)

        if not dept:
            raise ValidationError("Impossible de générer la référence : l'employé ou le contrat doit être rattaché à un département.")

        # Récupération du code département ou génération par défaut
        dept_code = (dept.code or dept.name[:6]).upper().replace(" ", "")
        current_year = datetime.now().year

        # Préfixe de recherche pour l'historique du département
        prefix = f"REF-{dept_code}-{current_year}-"

        # Compter le nombre de contrats déjà existants pour ce département cette année
        count = self.search_count([
            ('department_id', '=', dept.id),
            ('name', '=like', f"{prefix}%")
        ]) + 1

        # Formatage avec 3 chiffres (ex: 004)
        sequence_number = str(count).zfill(3)
        self.name = f"{prefix}{sequence_number}"