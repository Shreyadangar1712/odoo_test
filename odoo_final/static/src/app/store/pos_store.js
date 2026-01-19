/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore, {
    setup(...args) {
        super.setup(...args);

        // Custom fields
        this.shippingService = null;
        this.selectedShippingService = null;
    },

    setSelectedShippingService(service) {
        this.selectedShippingService = service;
        this.trigger('shipping-service-changed');
    },

    getSelectedShippingService() {
        return this.selectedShippingService;
    },

    updateOrderWithShippingService() {
        const currentOrder = this.get_order();
        if (currentOrder && this.selectedShippingService) {
            currentOrder.set_shipping_service(this.selectedShippingService);
            this.trigger('order-updated');
        }
    }
});
