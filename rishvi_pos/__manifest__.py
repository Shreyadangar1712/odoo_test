# -*- coding: utf-8 -*-

{
    "name": "Point Of Sale Linnworks Integration",
    "version": "18.0.1.0",
    "category": "General",
    "depends": ['point_of_sale','stock','base','web'],
    "price": 99.00,
    "currency": "EUR",
    "summary": "Point Of Sale Linnworks Integration",
    "description": """
        Point Of Sale Linnworks Integration
    """,
    "author": "Rishvi ltd",
    "website": "https://www.rishvi.com",
    "data": [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
        # 'views/product.xml',
        "views/product_category_view.xml",
        'views/pos_shipping_services.xml',

        'views/pos_shipping_actions.xml',
        # 'wizard/import_shipping_services_wizard.xml',
        # 'wizard/import_wizard.xml',
    ],
    "assets": {
        "point_of_sale._assets_pos": [

            # ========== POS ORDER PATCHES ==========

            # ========== PRODUCT SCREEN PATCH ==========
            # "rishvi_pos/static/src/screens/product_screen.js",

            # ========== MODEL OVERRIDES ==========
            "rishvi_pos/static/src/overrides/models/pos_store.js",
            "rishvi_pos/static/src/models/pos_order_line.js",

            # ========== CUSTOM ORDERLINE TEMPLATE OVERRIDE ==========
            "rishvi_pos/static/src/overrides/orderline/orderline.xml",

            # ========== CUSTOM PRODUCT CARD (OPTIONAL COMPONENT) ==========
            "rishvi_pos/static/src/app/generic_components/product_card/product_card.xml",

            # Shipping service dialog popup
            "rishvi_pos/static/src/app/control_buttons/pos_shipping_button/widgets/shipping_service_dialog.js",
            "rishvi_pos/static/src/app/control_buttons/pos_shipping_button/widgets/shipping_service_dialog.xml",
            # Patch the Order model to store shipping services
            "rishvi_pos/static/src/app/generic_components/order_widget/order.js",
            "rishvi_pos/static/src/app/store/pos_store.js",

            # ========== POS ORDER WIDGET ==========
            # Show shipping service in the order summary
            "rishvi_pos/static/src/app/generic_components/order_widget/order_widget.js",
            "rishvi_pos/static/src/app/generic_components/order_widget/order_widget.xml",
            # "pos_shipping_service/static/src/app/components/order_receipt.js",
            "rishvi_pos/static/src/app/components/order_receipt.xml",
            # ========== SHIPPING SERVICE CONTROL BUTTON ==========
            "rishvi_pos/static/src/app/control_buttons/pos_shipping_button/widgets/control_buttons.js",
            "rishvi_pos/static/src/app/control_buttons/pos_shipping_button/widgets/control_buttons.xml",
            "rishvi_pos/static/src/app/control_buttons/pos_shipping_button/widgets/shipping.scss",

        ],

        "web.assets_backend": [
            "rishvi_pos/static/src/js/pos_dashboard.js",
            "rishvi_pos/static/src/xml/pos_dashboard.xml",
            "rishvi_pos/static/src/scss/pos_dashboard.scss",

        ],
    },

    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "OPL-1",
}
