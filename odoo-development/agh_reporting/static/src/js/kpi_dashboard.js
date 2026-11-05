/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class KpiDashboard extends Component {
    static template = "agh_reporting.KpiDashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            kpis: [],
            loading: true,
        });
        onWillStart(async () => {
            await this.loadKPIs();
        });
    }

    async loadKPIs() {
        try {
            const result = await this.orm.searchRead(
                "account.kpi",
                [],
                ["name", "kpi_code", "unit", "target_value"],
            );
            this.state.kpis = result || [];
        } catch (e) {
            console.error("Erreur chargement KPIs:", e);
        } finally {
            this.state.loading = false;
        }
    }
}

registry.category("actions").add("agh_reporting_kpi_dashboard", KpiDashboard);
