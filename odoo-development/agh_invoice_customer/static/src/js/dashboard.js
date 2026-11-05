/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class InvoiceDashboard extends Component {
    static template = "agh_invoice_customer.Dashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            totalCA: 0,
            totalUnpaid: 0,
            overdueCount: 0,
            currency: "",
            loading: true,
            error: false,
        });
        onWillStart(async () => {
            await this.loadKPIs();
        });
    }

    async loadKPIs() {
        try {
            const result = await this.orm.call(
                "account.move",
                "get_invoice_dashboard_data",
                []
            );
            Object.assign(this.state, result, { loading: false, error: false });
        } catch (e) {
            this.state.loading = false;
            this.state.error = true;
        }
    }
}

registry.category("actions").add("agh_invoice_customer_dashboard", InvoiceDashboard);
