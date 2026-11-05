import requests

from odoo import models, fields
from odoo.exceptions import UserError


class FigmaTeam(models.Model):
    _name = "agh.figma.team"
    _description = "Figma Team"

    name = fields.Char(required=True)

    team_id = fields.Char(
        string="Figma Team ID",
        required=True
    )

    project_ids = fields.One2many(
        "agh.figma.project",
        "team_id",
        string="Projects"
    )

    def action_sync_projects(self):

        self.ensure_one()

        token = self.env["ir.config_parameter"].sudo().get_param(
            "figma_integration.api_token"
        )

        if not token:
            raise UserError("Figma token not configured.")

        headers = {
            "X-Figma-Token": token
        }

        url = f"https://api.figma.com/v1/teams/{self.team_id}/projects"

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise UserError(response.text)

        data = response.json()

        for project in data.get("projects", []):

            existing = self.env["agh.figma.project"].search([
                ("project_id", "=", project["id"])
            ], limit=1)

            if not existing:

                self.env["agh.figma.project"].create({
                    "name": project["name"],
                    "project_id": project["id"],
                    "team_id": self.id,
                })

    def action_sync_all(self):

        self.action_sync_projects()
    
        for project in self.project_ids:
            project.action_sync_files()
    
        return True

    