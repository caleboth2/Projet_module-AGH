# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ===========================================================
    # Champs originaux (gestion des attestations existantes)
    # ===========================================================
    certificate_ids = fields.One2many(
        'hr.certificate', 'employee_id', string='Attestations')
    certificate_count = fields.Integer(
        compute='_compute_certificate_count',
        string='Nb Attestations',
    )

    # ===========================================================
    # Nouveaux champs intégrés (module Attestation)
    # ===========================================================
    is_intern = fields.Boolean(string="Stagiaire")
    attestation_sent = fields.Boolean(
        string="Attestation envoyée", default=False, copy=False)
    attestation_number = fields.Char(
        string="Numéro Attestation", copy=False)

    # ===========================================================
    # Knowledge Integration (Souveraineté RH)
    # ===========================================================
    knowledge_article_ids = fields.One2many(
        'agh.knowledge.article', 'employee_id', string='Dossier RH (Documents)')
    knowledge_article_count = fields.Integer(
        compute='_compute_knowledge_article_count',
        string='Nb Documents RH',
    )

    @api.depends('knowledge_article_ids')
    def _compute_knowledge_article_count(self):
        for emp in self:
            emp.knowledge_article_count = len(emp.knowledge_article_ids)

    def action_open_knowledge_articles(self):
        self.ensure_one()
        return {
            'name': 'Dossier RH (Documentation)',
            'type': 'ir.actions.act_window',
            'res_model': 'agh.knowledge.article',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    @api.depends('certificate_ids')
    def _compute_certificate_count(self):
        for emp in self:
            emp.certificate_count = len(emp.certificate_ids)

    # ===========================================================
    # Actions originales
    # ===========================================================
    def action_open_certificates(self):
        return {
            'name': 'Attestations',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.certificate',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_generate_certificate(self):
        return {
            'name': 'Générer une Attestation',
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.generate.certificate',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }

    # ===========================================================
    # Action intégrée : Téléchargement direct attestation
    # ===========================================================
    def action_download_attestation(self):
        self.ensure_one()
        report = self.env.ref(
            'agh_employee_certificate.action_report_employee_attestation',
            raise_if_not_found=False,
        )
        if not report:
            raise UserError("Le rapport d'attestation est introuvable.")
        return report.report_action(self)
