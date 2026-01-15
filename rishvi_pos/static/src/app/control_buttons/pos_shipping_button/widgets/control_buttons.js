/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ShippingServiceDialog } from "@rishvi_pos/app/control_buttons/pos_shipping_button/widgets/shipping_service_dialog";
import { useService } from "@web/core/utils/hooks";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = useService("pos");
    },

    async onClickPopup() {
        const currentOrder = this.pos.get_order();
        let currentShippingService = currentOrder ? currentOrder.get_shipping_service() : undefined;

        this.env.services.dialog.add(ShippingServiceDialog, {
    currentShippingService: currentShippingService,
    getPayload: (selectedService) => {
        const order = this.pos.get_order();
        if (order) {
            order.set_shipping_service(selectedService);
            this.env.bus.trigger("shipping-service-updated", {
                order,
                service: selectedService,
            });

        }
    },
    close: () => console.log("Dialog closed"),
});


    },
});
