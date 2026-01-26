/** @odoo-module */
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(vals) {
        // this.available_linn_qty = this.available_linn_qty;
        return super.setup(...arguments);
    },
    getDisplayData() {
        return {
            available: this.available_linn_qty || 0,
            ...super.getDisplayData(),
        };
    },
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                available: { type: Number, optional: true },
            },
        },
    },
});

patch(Orderline.prototype, {
    setup() {
        super.setup();
        this.available_linn_qty = this.props.line.available;
        console.log(this.props.line)
    },
});
