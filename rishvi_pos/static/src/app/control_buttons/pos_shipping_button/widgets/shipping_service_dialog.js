
/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class ShippingServiceDialog extends Component {
    static template = "ShippingServiceDialogTemplate";

    static props = {
        currentShippingService: { optional: true },
        getPayload: Function,
        close: Function,
    };

    setup() {
        // Initialize state for services, selection, loading, error
        this.state = useState({
            services: [],
            selectedService: this.props.currentShippingService || null,
            isLoading: true,
            error: null,
        });

        // Fetch services from API on component start
        onWillStart(async () => {
    try {
        const result = await rpc("/pos/shipping/services");

        // If result.data exists, use it; else assume result itself is array
        const servicesArray = Array.isArray(result)
            ? result
            : Array.isArray(result.data)
            ? result.data
            : [];

        this.state.services = servicesArray.map((s, index) => ({
            ...s,
            _uid: s.id || index,
            amount: s.amount || 0, // Add amount from API

        }));
    } catch (err) {
        console.error("Failed to fetch services:", err);
        this.state.services = [];
        this.state.error = "Could not fetch shipping services";
    } finally {
        this.state.isLoading = false;
    }
});

    }

    // When user clicks a service button
    selectService(service) {
        this.state.selectedService = service;
    }

    // OK button click
    onOkClick() {
        if (this.state.selectedService) {
            this.props.getPayload(this.state.selectedService);
        }
        this.props.close();
    }
}
