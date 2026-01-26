# -*- coding: utf-8 -*-
import logging

from odoo import http, _
from odoo.http import request
from odoo import models, api, exceptions, fields
from odoo.exceptions import UserError


import requests

_logger = logging.getLogger(__name__)


class LinnController(http.Controller):

    @http.route(['/linnworks/get_stock_level_batch'], type='json')
    def get_stock_level_batch(self, **kwargs):
        """
        Fetches stock levels from Linnworks API
        Returns:
            dict: API response data or raises error
        """
        linnworks_id=kwargs['linnworks_item_id']
        ir_config = request.env["ir.config_parameter"].sudo()
        lw_token = ir_config.get_param("lw_token")
        lw_customer_id = ir_config.get_param("lw_customer_id")
        rishvi_base_api_url = ir_config.get_param("rishvi_base_api_url")
        rishvi_app = ir_config.get_param("rishvi_app")

        url = f'{rishvi_base_api_url}/Inventory/inventory-item/{linnworks_id}'

        params = { 
            "appName": rishvi_app,
            "appToken": lw_token,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, params=params,timeout=10)
            response.raise_for_status()
            if response and response.json():
                response = response.json()      
                return response.get('stockLevels')[0].get('quantity')

        except requests.exceptions.RequestException as req_error:
            _logger.error("Linnworks API Request Failed: %s", req_error)
            raise exceptions.UserError(
                f"API Request Error: {str(req_error)}"
            ) from req_error


    @http.route('/fetch_postal_services', type='json', auth='public', csrf=False)
    def get_postal_services(self, **kwargs):
        """Get available postal services from pos shipping service object"""
        services = [
            {
                "id": service["id"],
                "service_id": service["service_id"],
                "name": service["postal_service_name"],
                "amount": service["amount"],
                "vendor_id": service["vendor_id"],
            }
            for service in request.env['pos.shipping.services'].search([('active', '=', True)])
        ]

        print("\n\n\nServices >>>>>>.", services)
        return services

    @http.route('/pos/shipping/services', type='json', auth='user')
    def get_shipping_services(self):
        services = request.env['pos.shipping.services'].sudo().search([])
        return [
            {'id': s.id, 'name': s.postal_service_name, 'amount': s.amount}
            for s in services
        ]

    @http.route('/my/api/get_product_category_details', type='json', auth='user')
    def product_categories_details(self):
        _logger.debug("You are inside Product categories")

        ir_config = request.env["ir.config_parameter"].sudo()
        lw_token = ir_config.get_param("lw_token")
        rishvi_base_api_url = ir_config.get_param("rishvi_base_api_url")
        rishvi_app = ir_config.get_param("rishvi_app")

        url = f"{rishvi_base_api_url}/Inventory/categories"
        params = {"appName": rishvi_app, "appToken": lw_token}

        try:

            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                pos_category_model = request.env['pos.category']
                imported = 0

                for category in data:
                    category_id = category.get('categoryId')
                    category_name = category.get('categoryName')

                    if not category_id or not category_name:
                        continue

                    existing = pos_category_model.search([
                        ('linnworks_category_id', '=', category_id)
                    ], limit=1)

                    if not existing:
                        pos_category_model.create({
                            'name': category_name,
                            'linnworks_category_id': category_id,
                            'sequence': 10,  # helps display order
                        })
                        imported += 1
                        _logger.info(f"Imported POS category: {category_name}")

                request.env.cr.commit()  # VERY IMPORTANT
                return {'status': 'ok', 'imported': imported}

            return {'status': 'error', 'message': 'Linnworks API returned non-200'}

        except Exception as e:
            raise UserError(_("Failed to import POS categories: %s") % e)
