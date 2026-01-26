from odoo import models, fields


class PosSession(models.Model):
    _inherit = 'product.template'

    default_code = fields.Char(
        String='SKU', compute='_compute_default_code',
        inverse='_set_default_code', store=True)

    linnworks_item_id = fields.Char()
    linnworks_location_id = fields.Char()
    
# mapsb
