import base64

from odoo import http
from odoo import fields
from odoo.http import request


class ApkDownloadController(http.Controller):

    @http.route('/my/licenses', type='http', auth='user', website=True)
    def portal_my_licenses(self, **kwargs):
        licenses = request.env['agh.apk.license'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id),
        ], order='create_date desc')
        return request.render('agh_apk_store.portal_my_licenses', {
            'licenses': licenses,
            'page_name': 'licenses',
        })

    @http.route(
        '/shop/apk/download/<string:token>',
        type='http',
        auth='public',
        website=True,
    )
    def download_apk(self, token):
        license_record = request.env['agh.apk.license'].sudo().search([
            ('download_token', '=', token),
            ('state', '=', 'active'),
            '|',
            ('valid_until', '=', False),
            ('valid_until', '>=', fields.Date.today()),
        ], limit=1)

        if not license_record or license_record.sale_order_id.state not in ('sale', 'done'):
            return request.not_found()

        product = license_record.product_id.product_tmpl_id
        if not product.apk_file:
            return request.not_found()

        filename = product.apk_filename or '%s.apk' % product.name
        return request.make_response(
            base64.b64decode(product.apk_file),
            headers=[
                ('Content-Type', 'application/vnd.android.package-archive'),
                ('Content-Disposition', 'attachment; filename="%s"' % filename),
            ],
        )