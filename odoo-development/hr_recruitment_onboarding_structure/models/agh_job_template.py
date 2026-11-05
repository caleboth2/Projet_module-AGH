from odoo import models, fields

class AghJobTemplate(models.Model):
    _name = 'agh.job.template'
    _description = "Modèle d'annonce d'emploi"

    name = fields.Char(string="Nom du modèle", required=True)
    description = fields.Html(string="Description du poste")
    requirements = fields.Html(string="Prérequis")
