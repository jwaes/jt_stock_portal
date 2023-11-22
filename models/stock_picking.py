from odoo import api, fields, models

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'portal.mixin']

    def _compute_access_url(self):
        super(StockPicking, self)._compute_access_url()
        for transfer in self:
            transfer.access_url = '/my/transfers/%s' % (transfer.id)    

    def _get_report_base_filename(self):
        self.ensure_one()
        return f'{self.name}'