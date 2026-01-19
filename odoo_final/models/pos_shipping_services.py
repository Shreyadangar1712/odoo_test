# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
from odoo.http import request
from odoo import http, _




class PosShippingServices(models.Model):
    _name = 'pos.shipping.services'
    _description = 'Pos Shipping Services'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    service_id = fields.Char(string='Service ID', required=True)
    postal_service_name = fields.Char(string='Postal Service Name', required=True)
    service_country = fields.Many2one('res.country', string='Service Country', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='vendor_id.currency_id', readonly=True)
    active = fields.Boolean(string='Active', default=True)

