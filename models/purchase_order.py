from odoo import api, fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Need to be stored to be able to filter on it
    is_shipped = fields.Boolean(compute="_compute_is_shipped", store=True) 