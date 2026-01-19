/** @odoo-module **/

import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { Order } from "@point_of_sale/app/models/pos_order";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(OrderSummary.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
    },

    _setValue(val) {
        const selectedLine = this.currentOrder.get_selected_orderline();
        const numpadMode = this.pos.numpadMode;
        console.log("Selected line: ", selectedLine, numpadMode);

        if (selectedLine && numpadMode === "quantity") {
            const numericVal = parseFloat(val);
            if (numericVal > selectedLine.available_linn_qty) {
                this.dialog.add(AlertDialog, {
                    title: _t(`No quantity available!!`),
                    body: _t(`There is no stock available of ${selectedLine.full_product_name}`),
                });
                this.numberBuffer.reset();
                return false;
            }
        }
        return super._setValue(val);
    },
});
