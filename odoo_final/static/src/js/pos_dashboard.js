/** @odoo-module **/
import {
    registry
} from "@web/core/registry";
import {
    Component,useState
} from "@odoo/owl";
import {
    rpc
} from "@web/core/network/rpc";

class PosShippingDashboard extends Component {
    setup() {
        // reactive-like fields (we re-render manually via this.render())
        this.loading = false;
        this.pagesCount = 0;
        this.inventoryCountLinn = 0;
        this.inventoryCountRishvi = 0;
        this.syncProgress = 0;
        this.syncing = false;
        this.accpectedTime = 0;
        this.currentPageSyncing = 1;
        this.state = useState({ loading: false });  // 👈 Correct useState

        // load initial counts if you want:
        //    this._loadCounts();
    }

    // call your server code via the dataset RPC to run the transient's import_data
    async importShipping() {
        this.loading = true;
        this.render();
        try {
            // 1) create transient (optional). If your wizard doesn't need fields you can skip create.
            // const newId = await rpc('/web/dataset/call_kw', {
            //   model: 'import.shipping.services.wizard',
            //   method: 'create',
            //   args: [{}],
            //   kwargs: {},
            // });

            // 2) Call import_data on the model (your cron used model.search(...).import_data())
            const res = await rpc('/web/dataset/call_kw', {
                model: 'import.shipping.services.wizard',
                method: 'import_data',
                args: [
                    []
                ], // model-level call; or use [ [newId] ] for record-level
                kwargs: {},
            });

            // 3) If the server returned an Odoo action (display_notification) handle it:
            if (res && res.type === 'ir.actions.client' && res.tag === 'display_notification') {
                const msg = (res.params && res.params.message) ? res.params.message : 'Import completed';
                // try both notification services safely
                try {
                    if (this.env.services.notification && this.env.services.notification.add) {
                        this.env.services.notification.add(msg, {
                            type: 'success'
                        });
                    } else if (this.env.services.notify && this.env.services.notify.add) {
                        this.env.services.notify.add(msg, {
                            type: 'success'
                        });
                    } else {
                        // fallback - console log
                        console.log('Import success:', msg);
                    }
                } catch (nerr) {
                    console.warn('Notification failed:', nerr);
                    console.log('Import success (no notification):', msg);
                }
            } else {
                // generic success fallback (server didn't return the display_notification action)
                try {
                    if (this.env.services.notification && this.env.services.notification.add) {
                        this.env.services.notification.add('Shipping services imported/updated.', {
                            type: 'success'
                        });
                    } else if (this.env.services.notify && this.env.services.notify.add) {
                        this.env.services.notify.add('Shipping services imported/updated.', {
                            type: 'success'
                        });
                    } else {
                        console.log('Import success (no notification service): shipping services imported/updated.');
                    }
                } catch (nerr) {
                    console.warn('Notification failed:', nerr);
                }
            }
        } catch (err) {
            console.error('Import RPC error or handling error:', err);
            // show a more helpful UI message with the server error text if available
            let text = 'Failed to import shipping services. See logs.';
            if (err && err.data && err.data.message) {
                text = err.data.message;
            } else if (err && err.message) {
                text = err.message;
            }
            try {
                if (this.env.services.notification && this.env.services.notification.add) {
                    this.env.services.notification.add(text, {
                        type: 'danger',
                        sticky: true
                    });
                } else if (this.env.services.notify && this.env.services.notify.add) {
                    this.env.services.notify.add(text, {
                        type: 'danger',
                        sticky: true
                    });
                } else {
                    alert(text);
                }
            } catch (nerr) {
                console.warn('Failed to show error notification:', nerr);
            }
        } finally {
            this.loading = false;
            this.render();
        }
    }
  async enableDiscount() {
        this.state.loading = true;
        this.render();

        try {
            await rpc('/web/dataset/call_kw', {
                model: 'rishvi.dashboard.discount',
                method: 'action_enable_discounts',
                args: [[]],
                kwargs: {},
            });

            // 👇 Correct way to show notification
            this.env.services.notification.add("Discounts have been enabled successfully!", {
                type: "success",
            });
        } catch (error) {
            console.error("Enable discount failed:", error);
            this.env.services.notification.add(
                "Failed to enable discounts: " + (error.message || "Unknown error"),
                { type: "danger", sticky: true }
            );
        } finally {
            this.state.loading = false;
            this.render();
        }
    }

    async enablePriceLists() {
        this.state.loading = true;
        this.render();

        try {
            await rpc('/web/dataset/call_kw', {
                model: 'rishvi.dashboard.discount',
                method: 'action_enable_pricelists',
                args: [],   // 👈 Keep consistent format
                kwargs: {},
            });

            this.env.services.notification.add("Pricelists have been enabled successfully!", {
                type: "success",
            });
        } catch (error) {
            console.error("Enable pricelists failed:", error);
            this.env.services.notification.add(
                "Failed to enable pricelists: " + (error.message || "Unknown error"),
                { type: "danger", sticky: true }
            );
        } finally {
            this.state.loading = false;
            this.render();
        }
    }
     async getProductCaregories() {
      try {
          async function callWithRetry(url, params = {}, maxRetries = 3, delayMs = 1000) {
              for (let attempt = 1; attempt <= maxRetries; attempt++) {
                try {
                  const response = await rpc(url, params);  // your Odoo RPC call
                  if (response) return response;            // success → exit loop
                } catch (err) {
                  console.warn(`Attempt ${attempt} failed:`, err);
                  if (attempt < maxRetries) {
                    console.log(`Retrying in ${delayMs / 1000}s...`);
                    await new Promise(r => setTimeout(r, delayMs));  // wait before retry
                  } else {
                      console.error("All retry attempts failed.");
                      this.env.services.notification.add(
                          "Sorry! Please try again after some time.",
                          {
                            type: "warning",
                            sticky: true, // ✅ makes the notification stay visible until dismissed
                          }
                        );

                  }
                }
              }
            }
          const response = await callWithRetry("/my/api/get_product_category_details", {}, 3, 1000);
          this.env.services.notification.add("Product Categories details fetched!", { type: "success", sticky: true, });
      } catch (error) {
          console.error("Error fetching Product Categories:", error);
          this.env.services.notification.add("Failed to load Product Categories.", { type: "danger", sticky: true, });
      }
  }
}

// template name used below in the XML template file
PosShippingDashboard.template = "rishvi_pos.PosShippingTemplate";

// register client action tag
registry.category("actions").add("pos_shipping_dashboard", PosShippingDashboard);

export default PosShippingDashboard;