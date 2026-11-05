/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.ApkPortalLicense = publicWidget.Widget.extend({
    selector: '.o_portal_wrap',
    events: {
        'click .o_apk_copy_license': '_onCopyLicense',
    },

    async _onCopyLicense(event) {
        const button = event.currentTarget;
        const target = document.getElementById(button.dataset.copyTarget);
        if (!target) {
            return;
        }

        await navigator.clipboard.writeText(target.textContent.trim());
        const originalTitle = button.title;
        button.title = 'Clé copiée';
        window.setTimeout(() => {
            button.title = originalTitle;
        }, 1500);
    },
});