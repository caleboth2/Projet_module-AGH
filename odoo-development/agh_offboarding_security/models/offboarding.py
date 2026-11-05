from odoo import api, fields, models
from odoo.exceptions import ValidationError

class AghOffboarding(models.Model):
    _name = "agh.offboarding"
    _description = "Employee Offboarding"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        default="New",
        tracking=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("executed", "Executed"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    github_revoked = fields.Boolean(
        string="GitHub Access Revoked",
        tracking=True,
    )
    
    server_revoked = fields.Boolean(
        string="Server Access Revoked",
        tracking=True,
    )
    
    api_revoked = fields.Boolean(
        string="API Access Revoked",
        tracking=True,
    )
    
    vpn_revoked = fields.Boolean(
        string="VPN Access Revoked",
        tracking=True,
    )
    
    email_revoked = fields.Boolean(
        string="Email Access Revoked",
        tracking=True,
    )
    
    validated_by_manager = fields.Boolean(
        string="Manager Validation",
        tracking=True,
    )
    
    validated_by_hr = fields.Boolean(
        string="HR Validation",
        tracking=True,
    )

    def action_approve(self):
        for rec in self:
            if not rec.validated_by_manager:
                raise ValidationError(
                    "Manager validation is required."
                )
    
            if not rec.validated_by_hr:
                raise ValidationError(
                    "HR validation is required."
                )
    
            rec.state = "approved"
    
    
    def action_execute(self):
        for rec in self:
            required = [
                rec.github_revoked,
                rec.server_revoked,
                rec.api_revoked,
                rec.vpn_revoked,
                rec.email_revoked,
            ]
    
            if not all(required):
                raise ValidationError(
                    "All checklist items must be completed."
                )
    
            rec.state = "executed"
    
            rec.message_post(
                body="Offboarding executed successfully."
            )

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code(
                "agh.offboarding"
            ) or "New"
    
        return super().create(vals)