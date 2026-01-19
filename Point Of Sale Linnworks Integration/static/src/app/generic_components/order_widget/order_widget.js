/** @odoo-module **/

import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { useState, onMounted, onWillUpdateProps } from "@odoo/owl";


patch(OrderWidget.prototype, {
    get shippingService() {
        if (this.props.lines.length >= 1){
            const currentOrder = this.props.lines[0].order_id;
            const service = currentOrder?.get_shipping_service?.();
            return service;
        }
    },
});