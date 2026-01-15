from odoo import models, fields, api, _
import requests
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_is_zero
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class ImportShippingServiceWizard(models.TransientModel):
    _name = 'import.shipping.services.wizard'
    _description = 'Import Shipping Service Wizard'


    # Function to query Prometheus
    def import_data(self):

        try:

            ir_config = self.env["ir.config_parameter"].sudo()
            lw_token = ir_config.get_param("lw_token")
            lw_customer_id = ir_config.get_param("lw_customer_id")
            rishvi_base_api_url = ir_config.get_param("rishvi_base_api_url")
            rishvi_app = ir_config.get_param("rishvi_app")

            url = f'{rishvi_base_api_url}/Inventory/postal-services'

            params = {
                "appName": rishvi_app,
                "appToken": lw_token,
            }

            # url = "https://olbdsknit5g6vrtztqq4wlotea0vvtxm.lambda-url.eu-west-2.on.aws/api/Inventory/postal-services?appName=pos&appToken=a12e1102-7ad2-7bcc-2029-cc910303a813"
            headers = {
                "accept": "*/*",
            }
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            print("\n---DATA==========", data)

            if not isinstance(data, list):
                raise UserError(_("Unexpected data format received from API. Expected a list of services."))

            shipping_service_obj = self.env['pos.shipping.services']
            created_services = []

            for service in data:
                if not isinstance(service, dict):
                    _logger.error(f"Unexpected service data format: {service}")
                    continue

                try:
                    # Extract necessary information
                    service_id = service.get('serviceId')
                    postal_service_name = service.get('postalServiceName')
                    country_code = service.get('countryCode')
                    vendor_name = service.get('vendorName')

                    if not all([service_id, postal_service_name, country_code, vendor_name]):
                        _logger.error(f"Missing required data for service: {service}")
                        continue

                    # Find or create country
                    country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
                    if not country:
                        country = self.env['res.country'].create({'name': country_code, 'code': country_code})

                    # Find or create vendor
                    vendor = self.env['res.partner'].search([('name', '=', vendor_name)], limit=1)
                    if not vendor:
                        vendor = self.env['res.partner'].create({'name': vendor_name})

                    # Create or update the shipping service
                    existing_service = shipping_service_obj.search([('service_id', '=', service_id)], limit=1)
                    if existing_service:
                        existing_service.write({
                            'postal_service_name': postal_service_name,
                            'service_country': country.id,
                            'vendor_id': vendor.id,
                        })
                        created_services.append(existing_service.id)
                    else:
                        new_service = shipping_service_obj.create({
                            'service_id': service_id,
                            'postal_service_name': postal_service_name,
                            'service_country': country.id,
                            'vendor_id': vendor.id,
                        })
                        created_services.append(new_service.id)

                except Exception as e:
                    _logger.error(f"Error creating/updating shipping service {service.get('id', 'Unknown')}: {str(e)}")

            print("\n\n\nCreated/Updated Services >>>>>>.", created_services)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('%s shipping services have been imported/updated.') % len(created_services),
                    'sticky': False,
                }
            }

        except requests.exceptions.RequestException as e:
            _logger.error(f"Failed to fetch postal services: {str(e)}")
            raise UserError(_("Failed to fetch shipping services: %s") % str(e))
        except Exception as e:
            _logger.exception("Unexpected error in postal services fetch")
            raise UserError(_("Unexpected error occurred: %s") % str(e))