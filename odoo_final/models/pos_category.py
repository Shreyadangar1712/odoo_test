from odoo import models, fields, api, exceptions ,_
import logging


_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = 'pos.category'

    linnworks_category_id = fields.Char(
        string='Linnworks Category ID',
        help='External Linnworks unique category identifier (UUID).'
    )