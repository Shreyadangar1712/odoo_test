import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    getReceiptEnv() {
        const env = super.getReceiptEnv();
        env.shippingService = this.props.order.get_shipping_service?.() || null;
        return env;
    }
});
