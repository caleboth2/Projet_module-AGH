import requests

from odoo import models, fields
from odoo.exceptions import UserError


class FigmaProject(models.Model):
    _name = "agh.figma.project"
    _description = "Figma Project"

    name = fields.Char(required=True)

    project_id = fields.Char(
        string="Project ID",
        required=True
    )

    team_id = fields.Many2one(
        "agh.figma.team",
        string="Team",
        ondelete="cascade"
    )

    design_ids = fields.One2many(
        "agh.figma.design",
        "figma_project",
        string="Designs"
    )

    def action_sync_files(self):

        token = self.env['ir.config_parameter'].sudo().get_param(
            'figma_integration.api_token'
        )

        headers = {
            "X-Figma-Token": token
        }

        for rec in self:

            url = f"https://api.figma.com/v1/projects/{rec.project_id}/files"

            response = requests.get(
                url,
                headers=headers,
                timeout=20
            )

            data = response.json()

            for file_data in data.get("files", []):

                existing = self.env['agh.figma.design'].search([
                    ('figma_file_key', '=', file_data.get('key'))
                ], limit=1)

                values = {
                    'name': file_data.get('name'),
                    'figma_file_key': file_data.get('key'),
                    'figma_url': file_data.get('url'),
                    'figma_project': rec.id,
                }

                if existing:
                    existing.write(values)
                    existing.action_sync_data()
                else:
                    new_design = self.env['agh.figma.design'].create(values)
                    new_design.action_sync_data()