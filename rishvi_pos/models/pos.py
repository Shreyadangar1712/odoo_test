from odoo import models, api, exceptions, fields
import requests
from odoo.http import request
import logging
import json

from datetime import datetime, timedelta, timezone

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    linnworks_order_id = fields.Char(string='Linnworks Order ID')
    linn_order_number = fields.Char(string='Linnworks Order Number')
    linnworks_sync = fields.Boolean(string='Linnworks Synced', default=False)
    shippingName = fields.Char(string='Shipping service Name')
    shipping_service_id = fields.Many2one('pos.shipping.services', string="Shipping Service")
    shipping_amount = fields.Monetary(string="Shipping Amount", currency_field="currency_id")

    @api.model
    def create(self, values):
 
        # Create the POS order first (handling multiple records if applicable)
        order_ids = super(PosOrder, self).create(values)
 
        for order in order_ids:
            _data = order.read()[0]
            _logger.info(_data)
            try:
                icp = request.env["ir.config_parameter"].sudo()
                lw_token = icp.get_param("lw_token").strip()
                rishvi_base_api_url = icp.get_param("rishvi_base_api_url").strip()
                rishvi_app = icp.get_param("rishvi_app").strip()
                raw_time = str(order.date_order)
                try:
                    # Try parsing normally first
                    dt = datetime.strptime(raw_time[:19], "%Y-%m-%d %H:%M:%S")
                    _logger.info(f"Parsed datetime: {dt}")
                except ValueError:
                    # Fallback if seconds part is broken
                    parts = raw_time.split()
                    date_part = parts[0]
                    time_part = parts[1].split(":")[:3]
                    fixed_time = ":".join(time_part)
                    dt = datetime.strptime(f"{date_part} {fixed_time}", "%Y-%m-%d %H:%M:%S")
                    _logger.info(f"Fallback parsed datetime: {dt}")

                # Convert to UTC and ISO 8601 with milliseconds
                iso_time_recieved_order = dt.replace(tzinfo=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                _logger.info(f"ISO Time: {iso_time_recieved_order}")
                linn_order_invoiced_status=0
                linn_order_shipping_status=False
                linn_order_parked_status=False
                linn_order_Cancel_OnHold_status=False
                linn_order_invoiced_status=1
                
                _logger.info(f"ISO Time: {iso_time_recieved_order}")

                
                url = f"{rishvi_base_api_url}/Order/create-order"
                data = {
                        "source": "RISHVI_POS",
                        "subSource": "RISHVI_POS",
                        "referenceNumber": str(order.pos_reference),
                        "postalServiceId": str( order.shipping_service_id.service_id or "00000000-0000-0000-0000-000000000000"),
                        "postalServiceName": str(order.shippingName or order.shipping_service_id.postal_service_name or ""),
                        "savePostalServiceIfNotExist": True,
                        "receivedDate": str(iso_time_recieved_order),
                        "dispatchBy": str(iso_time_recieved_order),
                        "currency": str(order.currency_id.name),
                        "paymentStatus": str('UNPAID'),
                        "channelBuyerName": str(order.partner_id.name),
                        "postalServiceCost": float(order.shipping_service_id.amount or 0.0),
                        "postalServiceTaxRate": 0,
                        "status": int(linn_order_invoiced_status),
                        "holdOrCancel": linn_order_Cancel_OnHold_status,
                        "isParked": linn_order_parked_status,
                        "partShipped": linn_order_shipping_status,
                        "useChannelTax": True,
                        "postageCost":  float(order.shipping_service_id.amount or 0.0),

                    "billingAddress": {
                        "fullName": str(order.partner_id.name or "POS Customer"),
                        "address1": str(order.partner_id.street or ""),
                        "town": str(order.partner_id.city or ""),
                        "postCode": str(order.partner_id.zip or ""),
                        "country": str(order.partner_id.country_id.name or ""),
                        "emailAddress": str(order.partner_id.email or ""),
                        "company": str(order.partner_id.company_name or ""),
                        "phoneNumber": str(order.partner_id.phone or "")
                        },
                        "deliveryAddress": {
                            "fullName": str(order.partner_id.name or "POS Customer"),
                            "address1": str(order.partner_id.street or ""),
                            "town": str(order.partner_id.city or ""),
                            "postCode": str(order.partner_id.zip or ""),
                            "country": str(order.partner_id.country_id.name or ""),
                            "emailAddress": str(order.partner_id.email or ""),
                            "company": str(order.partner_id.company_id.name or ""),
                            "phoneNumber": str(order.partner_id.phone or "")
                        },

                        "orderItems": [
                            {
                                "sku": str(line.product_id.default_code or ""),
                                "itemNumber": str(line.product_id.linnworks_item_id or ""),
                                "itemTitle": str(line.product_id.name or ""),
                                "pricePerUnit": float(line.price_unit or 0.0),
                                "qty": int(line.qty or 0),
                                "taxRate": float(sum(t.amount for t in
                                                     line.tax_ids_after_fiscal_position) if line.tax_ids_after_fiscal_position else 0.0),
                                "taxCostInclusive": False,
                                "discount": float(line.discount or 0.0),
                            }
                            for line in order.lines
                            if not getattr(line, "is_shipping_line", False)
                        ],

                    "notes": [
                            {
                                "note": order.general_note if order.general_note else "",
                                "createdBy": "RISHVI",
                                "internal": True
                            }
                        ]
                    }
                

                
                params = {"appName": rishvi_app, "appToken": lw_token}
                headers = {"accept": "*/*", "Content-Type": "application/json"}

                
                # _logger.info(data)
                try:
                    response = requests.post(url, params=params, headers=headers, data=json.dumps(data), timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    if response.status_code == 200:
                        if order.linnworks_sync==True:
                            return {
                                "type": "ir.actions.client",
                                "tag": "display_notification",
                                "params": {
                                    "title": "Success",
                                    "message": data['message'],
                                    "type": "success",
                                    "sticky": True,  # Disappears after a few seconds
                                }
                            }
                        order.write({
                            'linnworks_order_id': data['orderId'],
                            'linn_order_number':data['numOrderId'],
                            'linnworks_sync': True,
                        })
                        return order_ids
                except requests.exceptions.RequestException as e:
                    _logger.error("Error fetching order status counts: %s", e)
                    return order_ids
            except Exception as e:
                    _logger.error(f"Linnworks order sync failed for order {order.id}: {e}")
        return order_ids


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    available_linn_qty = fields.Float(string="Available Linn Quantity")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(PosOrderLine,self).create(vals_list)
        print("\n\n\nvals >>>>>..",vals_list)
        return res

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        res.append('available_linn_qty')
        return res