/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";
import { parseUTCString, qrCodeSrc, random5Chars, uuidv4, gte, lt } from "@point_of_sale/utils";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.shippingService = vals.shippingService || null;
        this.shipping_service_id = vals.shipping_service_id || null;
    },
    serialize() {
        const data = super.serialize(...arguments);
        data.shipping_service_id = this.shipping_service_id
        // Optionally send the amount (if you're storing it separately)
        if (this.shippingService) {
            data.shippingName = this.shippingService.name
            data.shipping_amount = this.shippingService.amount;
        }
        return data;
    },
    set_shipping_service(service) {
        const cleanPrice = parseFloat(String(service.price).replace(/[^\d.]/g, '')) || 0;
        this.shippingService = {
            id: service.id,
            name: service.name,
            amount: cleanPrice,
        };
        this.shippingService = service;
        this.shipping_service_id = service.id;
    },

    get_shipping_service() {
        return this.shippingService;
    },
    getTotalDue() {
        if (this.shippingService) {
            return this.taxTotals.order_sign * this.taxTotals.order_total + this.shippingService.amount;
        }
        else {
            return this.taxTotals.order_sign * this.taxTotals.order_total;
        }
    },
    formatMonetary(amount, { currencyId }) {
        const currency = this.pos.currency_by_id[currencyId];
        if (!currency || typeof amount !== 'number') {
            return amount?.toFixed?.(2) || '0.00';
        }
        return formatCurrency(amount, currency);
    },
    get_change() {
        let { order_sign, order_remaining: remaining } = this.taxTotals;
        if (this.config.cash_rounding) {
            remaining = this.getRoundedRemaining(this.config.rounding_method, remaining);
        }
        const order = this.models["pos.order"].get(this.id);
        if (order && order.shippingName) {
            // Calculate the difference between shipping_amount and remaining
            remaining = Math.abs(remaining) - order.shipping_amount;
            return Math.abs(remaining);
        }
        else {
            return -order_sign * remaining;
        }
    },
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        result.company = this.company;  // required by ReceiptHeader
        result.currency = this.currency;
        const order = this.models["pos.order"].get(this.id);
        if (order && order.shippingName) {
            result.shippingName = order.shippingName;
            result.shipping_amount = order.shipping_amount;
        }
        console.log("Result=======", result);
        return result;
    },
    get taxTotals() {
        const currency = this.config.currency_id;
        const company = this.company;
        const orderLines = this.lines;

        // If each line is negative, we assume it's a refund order.
        // It's a normal order if it doesn't contain a line (useful for pos_settle_due).
        // TODO: Properly differentiate refund orders from normal ones.
        const documentSign =
            this.lines.length === 0 ||
            !this.lines.every((l) => lt(l.qty, 0, { decimals: currency.decimal_places }))
                ? 1
                : -1;

        const baseLines = orderLines.map((line) =>
            accountTaxHelpers.prepare_base_line_for_taxes_computation(
                line,
                line.prepareBaseLineForTaxesComputationExtraValues({
                    quantity: documentSign * line.qty,
                })
            )
        );
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, company);

        // For the generic 'get_tax_totals_summary', we only support the cash rounding that round the whole document.
        const cashRounding =
            !this.config.only_round_cash_method && this.config.cash_rounding
                ? this.config.rounding_method
                : null;

        const taxTotals = accountTaxHelpers.get_tax_totals_summary(baseLines, currency, company, {
            cash_rounding: cashRounding,
        });

        taxTotals.order_sign = documentSign;
        taxTotals.order_total =
            taxTotals.total_amount_currency - (taxTotals.cash_rounding_base_amount_currency || 0.0);
        taxTotals.currency_id = currency.id || (currency && currency.currency_id && currency.currency_id[0]);

        let order_rounding = 0;
        let remaining = 0;
        if (this.shippingService) {
            taxTotals.shippingService = this.shippingService;
            taxTotals.shippingServiceamount = this.shippingService.amount;
            taxTotals.total_amount_currency += this.shippingService.amount;
//            taxTotals.total_amount_currency = this.shippingService.amount
            remaining = taxTotals.order_total + this.shippingService.amount;
        }
        else {
            remaining = taxTotals.order_total;
        }
        const validPayments = this.payment_ids.filter((p) => p.is_done() && !p.is_change);
        for (const [payment, isLast] of validPayments.map((p, i) => [
            p,
            i === validPayments.length - 1,
        ])) {
            const paymentAmount = documentSign * payment.get_amount();
            if (isLast) {
                if (this.config.cash_rounding) {
                    const roundedRemaining = this.getRoundedRemaining(
                        this.config.rounding_method,
                        remaining
                    );
                    if (!floatIsZero(paymentAmount - remaining, this.currency.decimal_places)) {
                        order_rounding = roundedRemaining - remaining;
                    }
                }
            }
            remaining -= paymentAmount;
        }

        taxTotals.order_rounding = order_rounding;
        taxTotals.order_remaining = remaining;

        const remaining_with_rounding = remaining + order_rounding;
        if (floatIsZero(remaining_with_rounding, currency.decimal_places)) {
            taxTotals.order_has_zero_remaining = true;
        } else {
            taxTotals.order_has_zero_remaining = false;
        }

        return taxTotals;
    }

});