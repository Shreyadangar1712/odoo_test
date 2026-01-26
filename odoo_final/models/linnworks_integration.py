from odoo import models, fields, api, _
import logging
import requests
from odoo.exceptions import UserError
import base64
from io import BytesIO
from PIL import Image

_logger = logging.getLogger(__name__)


class LinnworksIntegration(models.Model):
    _name = 'linnworks.integration'
    _description = 'Linnworks Integration'

    name = fields.Char('Name', default='Linnworks')
    application_id = fields.Char('Application ID', required=True)
    application_secret = fields.Char('Application Secret', required=True)
    instance_token = fields.Char('Instance Token', required=True)
    auth_token = fields.Char('Auth Token')
    server_url = fields.Char('Server URL')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    product_import_qty = fields.Integer()

    def _get_auth_token_cust(self):
        for rec in self:
            rec._get_auth_token()

    def action_test_linnworks_connection(self):
        result = self._get_auth_token()
        if result and result.get('type') == 'ir.actions.client':
            return result
        return True


    def _get_auth_token(self):
        """Authenticate with Linnworks API and get fresh token"""
        try:
            auth_url = "https://api.linnworks.net/api/Auth/AuthorizeByApplication"
            payload = {
                "ApplicationId": self.application_id,
                "ApplicationSecret": self.application_secret,
                "Token": self.instance_token,
            }
            response = requests.post(auth_url, json=payload, headers={"accept": "application/json"})
            response.raise_for_status()
            auth_data = response.json()

            self.write({
                'auth_token': auth_data.get('Token'),
                'server_url': auth_data.get('Server')
            })
            if response.status_code == 200:
                _logger.info("Linnworks connection successful. Returning notification action.")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection to Linnworks successful!'),
                        'type': 'success',
                        'sticky': False,
                        'next': {
                            'type': 'ir.actions.act_window_close'
                        }
                    }
                }
            else:
                _logger.error(f"Linnworks connection failed. Status code: {response.status_code}")
                raise UserError(f"Connection failed! Status code: {response.status_code}\n{response.text}")
        except Exception as e:
            _logger.error(f"Linnworks Authentication Failed: {e}")
            raise UserError(_("Linnworks Authentication Failed: %s") % e)


    def import_products(self):
        """Main import function with proper authentication handling.
        Will only import 200 products for testing purposes."""
        self.ensure_one()
        print("\n\n\nThis method is called================")
        # First, get authentication token
        if not self._get_auth_token():
            raise UserError(_("Failed to authenticate with Linnworks API"))

        # Prepare API request with dynamic server URL
        stock_url = f"{self.server_url}/api/Stock/GetStockItemsFull"
        headers = {
            "Authorization": self.auth_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        page = 1
        products_imported = 0
        products_per_page = min(100, self.product_import_qty)  # Limit to 100 per page or less

        while products_imported < self.product_import_qty:
            payload = {
                "keyword": "",
                "loadCompositeParents": True,
                "loadVariationParents": True,
                "entriesPerPage": products_per_page,
                "pageNumber": page,
                "dataRequirements": ["StockLevels", "Pricing",
                                     "Supplier", "ShippingInformation", "ChannelTitle",
                                     "ChannelDescription", "ChannelPrice",
                                     "ExtendedProperties", "Images"],
                "searchTypes": ["SKU", "Title", "Barcode"]
            }

            try:
                # Make the request to Linnworks API
                response = requests.post(stock_url, headers=headers, json=payload)
                response.raise_for_status()  # Raise exception for bad status codes
                data = response.json()

            except requests.exceptions.RequestException as e:
                _logger.error(f"Failed to fetch products (Page {page}): {e}")
                break  # Break if there is a failure in fetching products

            items = data
            if not items:
                break  # Exit loop if no items are returned from the

            # Process each product
            for item in items:
                if products_imported >= self.product_import_qty:
                    break  # Stop if we've reached the import limit

                try:
                    # Stop processing after 200 products for testing purposes
                    # if product_count >= 20285:
                    #     _logger.info("Imported 20285 products for testing. Stopping import.")
                    #     return True
                    # Process each product individually
                    self._process_product(item)
                    products_imported += 1
                    # product_count += 1  # Increment the product count after each successful import

                except Exception as e:
                    _logger.error(f"Error processing product SKU {item.get('ItemNumber')}: {e}")
                    continue  # Continue to the next product if the current one fails

            if products_imported >= self.product_import_qty:
                break  # Stop if we've reached the import limit

            page += 1
        _logger.info(f"Imported {products_imported} products.")

        return True

    def _process_product(self, item):
        """Process individual product and update stock"""
        Product = self.env['product.product']
        StockQuant = self.env['stock.quant']

        sku = item.get('ItemNumber')
        itemid = item.get('StockItemId')
        name = item.get('ItemTitle')
        barcode = item.get('BarcodeNumber')
        image = item.get('Images', [])
        tax = item.get('TaxRate', 0.0)
        pos_category = item.get('CategoryName')
        retail_price = item.get('RetailPrice', 0.0)
        # print("\n\nitemid",itemid)

        if image:
            main_image_url = next((img.get('FullSource') for img in image if img.get('IsMain')), None)
            if main_image_url:
                image = main_image_url
            else:
                image = image[0].get('FullSource')  # If no main image, take the first one
        else:
            image = None  # If no images, set as None

        if image:
            try:
                # Download the image
                response = requests.get(image)
                response.raise_for_status()  # Ensure the request was successful
                img_data = response.content

                # Convert the image to Base64
                img_base64 = base64.b64encode(img_data).decode('utf-8')

                # Update the image to be in Base64 format for Odoo
                image = img_base64
            except requests.exceptions.RequestException as e:
                _logger.error(f"Failed to download image for SKU {sku}: {e}")
                image = None  # If there is an issue, set image to None

        # Find the main stock level (sum all locations or pick specific ones)
        total_stock = sum([
            level.get('Available', 0)
            for level in item.get('StockLevels', [])
        ])
        # print("\n\n", total_stock)
        PosCategory = self.env['pos.category']
        category = PosCategory.search([('name', '=', pos_category)], limit=1)
        if not category:
            # If category doesn't exist, create it
            category = PosCategory.create({
                'name': pos_category,
            })
        # Get or create product
        # product = Product.search([('default_code', '=', sku)], limit=1)
        product = Product.search([('linnworks_item_id', '=', itemid)], limit=1)
        if not product:
            # Check if the barcode is already used by another product
            existing_barcode_product = Product.search([('barcode', '=', barcode)], limit=1) if barcode else None
            create_vals = {
                'name': name,
                'default_code': sku,
                'type': 'consu',
                'is_storable': True,
                'available_in_pos': True,
                'pos_categ_ids': [(4, category.id)] if category else [],
                'image_1920': image,
                'list_price': retail_price,
                'linnworks_item_id':itemid,
            }
            # for stLevel in item.get('StockLevels'):
            create_vals['linnworks_location_id'] = ','.join([stLevel.get('Location').get('StockLocationId') for stLevel in item.get('StockLevels')])

            if barcode and not existing_barcode_product:
                create_vals['barcode'] = barcode
            elif existing_barcode_product:
                _logger.warning(f"Barcode {barcode} already exists for product {existing_barcode_product.default_code} (ID: {existing_barcode_product.id}). Skipping barcode assignment for new product with SKU {sku}.")

            product = Product.create(create_vals)
            print("\n\nPRODUCT", product)
        else:
            # Update existing product with new data from Linnworks
            update_vals = {}
            # Update product name if changed
            if product.name != name:
                update_vals['name'] = name

            print("itemid",itemid)
            if product.linnworks_item_id != itemid:
                update_vals['linnworks_item_id'] = itemid
                print("\n\nupdate_vals['linnworks_item_id']",update_vals['linnworks_item_id'])

            # Update barcode if changed and not duplicate
            if barcode and product.barcode != barcode:
                existing_barcode_product = Product.search([('barcode', '=', barcode), ('id', '!=', product.id)], limit=1)
                if not existing_barcode_product:
                    update_vals['barcode'] = barcode
                else:
                    _logger.warning(f"Barcode {barcode} already used by product {existing_barcode_product.default_code}, skipping update for {sku}")

            # Update image if changed
            if image and image != product.image_1920:
                update_vals['image_1920'] = image

            # Update price if changed
            if product.list_price != retail_price:
                update_vals['list_price'] = retail_price

            # Update POS category (replace existing categories)
            if category:
                update_vals['pos_categ_ids'] = [(6, 0, [category.id])]

            # Apply all updates if any
            if update_vals:
                # print("\n\nPRODUCT", product.id)
                # update_vals['linnworks_location_id'] = ''
                update_vals['linnworks_location_id'] = ','.join([stLevel.get('Location').get('StockLocationId') for stLevel in item.get('StockLevels')])
                product.write(update_vals)

        # Update stock levels (existing code)
        total_stock = sum(level.get('Available', 0) for level in item.get('StockLevels', []))
    # Update stock in the specified warehouse_id
        location = self.warehouse_id.lot_stock_id
        StockQuant._update_available_quantity(product, location, quantity=total_stock)

    # Add fulfilment center ID field
    fulfilment_center_id = fields.Char(
        string='Fulfilment Center ID',
        required=True,
        default='00000000-0000-0000-0000-000000000000'
    )

    def create_linnworks_order(self, pos_order):
        """Create a draft order in Linnworks from a POS order"""
        self.ensure_one()

        # if not self.auth_token or not self.server_url:
        self._get_auth_token()

        url = f"https://eu-ext.linnworks.net/api/Orders/CreateNewOrder"
        # url = f"{self.server_url}/api/Orders/CreateNewOrder"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": self.auth_token
        }

        # Base payload
        payload = {
            "fulfilmentCenter": self.fulfilment_center_id,
            "createAsDraft": True,
            "CustomerInfo": self._prepare_customer_info(pos_order),
            # "Items": self._prepare_order_items(pos_order.lines),
            "TotalsInfo": self._prepare_totals(pos_order)
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            # return response.json().get('NumOrderId')
            # print("\n\n-------------------------",response.json().get('NumOrderId'),response.json().get('OrderId'))
            return response.json().get('NumOrderId'),response.json().get('OrderId')
        except Exception as e:
            _logger.error(f"Linnworks Order Creation Failed: {e}")
            raise UserError(_("Failed to create Linnworks order: %s") % e)

    def _prepare_customer_info(self, pos_order):
        """Prepare customer data from POS order"""
        partner = pos_order.partner_id
        if not partner:
            return {}

        return {
            "ChannelBuyerName": partner.name or "",
            "Address": {
                "EmailAddress": partner.email or "",
                "Address1": partner.street or "",
                "Address2": partner.street2 or "",
                "Town": partner.city or "",
                "Region": partner.state_id.name or "",
                "PostCode": partner.zip or "",
                "Country": partner.country_id.code or "UNKNOWN",
                "FullName": partner.name or "",
                "Company": partner.parent_id.name if partner.parent_id else "",
                "PhoneNumber": partner.phone or ""
            }
        }

    def _prepare_order_items(self, order_lines):
        """Convert POS order lines to Linnworks items"""
        items = []
        for line in order_lines:
            items.append({
                "SKU": line.product_id.default_code or "",
                "Title": line.product_id.name,
                "Quantity": line.qty,
                "Price": line.price_unit,
            })
        print("\n\nitems",items)
        return items

    def _prepare_totals(self, pos_order):
        """Prepare order totals"""
        return {
            "Subtotal": pos_order.amount_total,
            "Tax": pos_order.amount_tax,
            "TotalCharge": pos_order.amount_total,
            "Currency": pos_order.currency_id.name
        }

    def add_order_item(self, order_id, product, quantity, price_per_unit, tax_rate=0.0):
        """Add an order item to a Linnworks order
        Args:
            order_id (str): Linnworks Order ID (GUID format)
            product (product.product): Odoo product record
            quantity (float): Quantity of the item
            price_per_unit (float): Unit price of the item
            tax_rate (float): Tax rate percentage (default 0.0)
        Returns:
            bool: True if successful
        Raises:
            UserError: If API request fails
        """
        self.ensure_one()

        # Ensure valid authentication
        if not self.auth_token:
            self._get_auth_token()

        # Prepare API URL and headers
        url = f"https://eu-ext.linnworks.net/api/Orders/AddOrderItem"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": self.auth_token
        }

        # Validate required product data
        if not product.linnworks_item_id:
            raise UserError(_("Product %s has no Linnworks Item ID configured") % product.name)

        # Prepare payload
        payload = {
            "orderId": order_id,
            "itemId": product.linnworks_item_id,
            "channelSKU": product.default_code or "",
            "fulfilmentCenter": self.fulfilment_center_id,
            "quantity": quantity,
            "linePricing": {
                "PricePerUnit": price_per_unit,
                "DiscountPercentage": 0.0,  # Assuming no discount
                "TaxRatePercentage": tax_rate,
                "TaxInclusive": True  # Assuming tax inclusive pricing
            },
            "createdDate": fields.Datetime.now().isoformat() + 'Z'  # Current time in ISO8601
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            _logger.info("Successfully added item %s to Linnworks order %s", product.default_code, order_id)
            return True
        except requests.exceptions.RequestException as e:
            error_msg = _("Failed to add item to Linnworks order: %s") % str(e)
            _logger.error(error_msg)
            raise UserError(error_msg)

    def find_instant_stock_items(self, exclude_composites=False, **kwargs):
        """Search instant stock items in Linnworks
        Args:
            keyword (str): Search keyword
            exclude_composites (bool): Exclude composite items
        Returns:
            dict: API response data
        Raises:
            UserError: If API request fails or missing configuration
        """
        print("keyword linnworks_location_id >>>>>>>>>>.",keyword, linnworks_location_id)
        self.ensure_one()

        # Ensure valid authentication
        if not self.auth_token:
            self._get_auth_token()

        # # Get Linnworks location ID from warehouse
        # if not linnworks_location_id:
        #     raise UserError(_("Configure Linnworks Location ID on Warehouse %s") % self.warehouse_id.name)

        # Prepare API request
        url = "https://eu.linnworks.net/api/Stock/FindInstantStockItems"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": self.auth_token
        }

        payload = {
            "request": {
                "keyWord": keyword,
                "locationId": linnworks_location_id,
                "excludeComposites": exclude_composites
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            print("response find_instant_stock_items >>>>>.",response)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = _("Linnworks stock search failed: %s") % str(e)
            _logger.error(error_msg)
            raise UserError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = _("Failed to parse Linnworks API response: %s") % str(e)
            _logger.error(error_msg)
            raise UserError(error_msg)

