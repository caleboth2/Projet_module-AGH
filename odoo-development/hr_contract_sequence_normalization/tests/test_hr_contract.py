from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestHrContractSequence(TransactionCase):

    def setUp(self):
        super(TestHrContractSequence, self).setUp()

        # Création d'un département de test avec un code
        self.department = self.env['hr.department'].create({
            'name': 'Ressources Humaines',
            'code': 'RECRUT',
        })

        # Création d'un employé de test lié à ce département
        self.employee = self.env['hr.employee'].create({
            'name': 'Jean Dupont',
            'department_id': self.department.id,
        })

    def test_01_contract_sequence_generation(self):
        """Vérifie que la séquence se génère au bon format lors de la validation"""
        contract = self.env['hr.contract'].create({
            'name': 'Nouveau',
            'employee_id': self.employee.id,
            'wage': 3000,
        })

        contract.action_validate_contract()
        
        # Vérifie que la référence commence bien par REF-RECRUT-2026-
        self.assertTrue(contract.name.startswith('REF-RECRUT-'))
        self.assertTrue(contract.name.endswith('-001'))

    def test_02_contract_sequence_incrementation(self):
        """Vérifie l'incrémentation (+1) pour un second contrat du même département"""
        # Premier contrat
        c1 = self.env['hr.contract'].create({
            'name': 'Nouveau',
            'employee_id': self.employee.id,
            'wage': 3000,
        })
        c1.action_validate_contract()

        # Second contrat
        c2 = self.env['hr.contract'].create({
            'name': 'Nouveau',
            'employee_id': self.employee.id,
            'wage': 3500,
        })
        c2.action_validate_contract()

        self.assertTrue(c2.name.endswith('-002'))

    def test_03_missing_department_validation(self):
        """Vérifie qu'une erreur est levée si aucun département n'est renseigné"""
        employee_no_dept = self.env['hr.employee'].create({'name': 'Sans Département'})
        
        contract = self.env['hr.contract'].create({
            'name': 'Nouveau',
            'employee_id': employee_no_dept.id,
            'wage': 2000,
        })

        with self.assertRaises(ValidationError):
            contract.action_validate_contract()