from odoo import models, fields


class AghGumroadSyncWizard(models.TransientModel):
    _name = 'agh.gumroad.sync.wizard'
    _description = 'Manual AGH Gumroad Sync'

    connector_id = fields.Many2one('agh.gumroad.connector', required=True)
    days = fields.Integer('Days to sync', default=7)
    sync_products = fields.Boolean('Sync Products', default=True)

    def action_run(self):
        self.ensure_one()
        if self.sync_products:
            self.connector_id.action_sync_products()
        self.connector_id.action_sync_sales(days=self.days)
        return {'type': 'ir.actions.act_window_close'}
