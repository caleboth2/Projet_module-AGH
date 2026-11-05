from odoo import api, fields, models


class AghCrashReport(models.Model):
    _name = "agh.crash.report"
    _description = "Crash Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        default="New",
        tracking=True,
    )

    title = fields.Char(
        string="Title",
        required=True,
        tracking=True,
    )

    signature = fields.Char(
        string="Signature",
        required=True,
        tracking=True,
    )

    description = fields.Text()

    source = fields.Char()

    severity = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("new", "New"),
            ("ticket_created", "Ticket Created"),
            ("closed", "Closed"),
        ],
        default="new",
        tracking=True,
    )

    occurrence_count = fields.Integer(
        default=1,
    )

    task_id = fields.Many2one(
        "project.task",
        string="Technical Ticket",
    )

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "agh.crash.report"
                    )
                    or "New"
                )

            signature = vals.get("signature")

            if signature:

                existing = self.search(
                    [
                        ("signature", "=", signature)
                    ],
                    limit=1,
                )

                if existing:
                    existing.occurrence_count += 1
                    return existing

        return super().create(vals_list)

    def action_create_ticket(self):

        Project = self.env["project.project"]

        project = Project.search(
            [
                ("name", "=", "Crash Management")
            ],
            limit=1,
        )

        if not project:
            project = Project.create(
                {
                    "name": "Crash Management"
                }
            )

        for rec in self:

            if not rec.task_id:

                task = self.env[
                    "project.task"
                ].create(
                    {
                        "name": rec.title,
                        "description": rec.description,
                        "project_id": project.id,
                    }
                )

                rec.task_id = task.id

                rec.state = "ticket_created"

                rec.message_post(
                    body="Technical ticket created automatically."
                )