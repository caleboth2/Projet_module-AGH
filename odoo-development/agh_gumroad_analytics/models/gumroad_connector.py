"""Extension du connecteur AGH : synchronisation produits + ventes Gumroad
avec archivage souverain (res.partner + JSON brut) et correction du prix."""
import json
import logging
from datetime import datetime, timedelta
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GUMROAD_API = 'https://api.gumroad.com/v2'


def _to_amount(value):
    """Convertit un montant Gumroad en float decimal.
    Gumroad renvoie souvent les prix en centimes (ex: 200 pour 2$).
    """
    if value is None or value == '':
        return 0.0
    try:
        # Si c'est déjà un float, on considère que c'est l'unité majeure
        if isinstance(value, float):
            return value
        
        # Si c'est une chaîne, on nettoie
        if isinstance(value, str):
            s = value.strip().replace('$', '').replace(',', '')
            if '.' in s:
                return float(s)
            value = int(s)

        # Règle par défaut pour Gumroad v2 : les entiers sont des centimes
        # Sauf si c'est explicitement 0
        if isinstance(value, int):
            return value / 100.0
            
        return float(value)
    except Exception:
        return 0.0


class AghGumroadConnector(models.Model):
    _inherit = 'agh.gumroad.connector'

    product_ids = fields.One2many('agh.gumroad.product', 'connector_id', string='Products')
    auto_sync = fields.Boolean('Auto Sync (cron)', default=True)

    # ---------- HTTP helpers ----------
    def _get(self, path, params=None):
        self.ensure_one()
        params = dict(params or {})
        params['access_token'] = self.access_token
        url = f'{GUMROAD_API}{path}'
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            raise UserError(_('Gumroad API error %s: %s') % (r.status_code, r.text[:300]))
        data = r.json()
        if not data.get('success'):
            raise UserError(_('Gumroad API returned failure: %s') % data)
        return data

    # ---------- Partner archival (sovereignty) ----------
    def _ensure_partner(self, sale_payload):
        """Crée ou met à jour un res.partner local pour chaque acheteur.
        L'agence conserve ainsi la souveraineté de la base clients."""
        Partner = self.env['res.partner'].sudo()
        email = (sale_payload.get('email') or '').strip().lower()
        name = sale_payload.get('full_name') or sale_payload.get('purchaser_name') or email or 'Gumroad Buyer'
        country_code = sale_payload.get('country_iso2') or sale_payload.get('country')
        country_id = False
        if country_code and len(country_code) == 2:
            c = self.env['res.country'].search([('code', '=', country_code.upper())], limit=1)
            country_id = c.id if c else False
        vals = {
            'name': name,
            'email': email or False,
            'country_id': country_id,
            'comment': _("Importé depuis Gumroad par AGH Gumroad Connector"),
        }
        partner = Partner.search([('email', '=ilike', email)], limit=1) if email else Partner.browse()
        if partner:
            # Mise à jour douce : ne pas écraser un nom déjà personnalisé
            update = {}
            if not partner.country_id and country_id:
                update['country_id'] = country_id
            if update:
                partner.write(update)
        else:
            partner = Partner.create(vals)
        return partner

    def action_sync_products(self):
        Product = self.env['agh.gumroad.product']
        for conn in self:
            data = conn._get('/products')
            for p in data.get('products', []):
                # Utiliser formatted_price si disponible pour refléter le prix réel affiché (ex: $29.99)
                formatted = p.get('formatted_price', '')
                if formatted and '$' in formatted:
                    unit_price = _to_amount(formatted)
                else:
                    unit_price = _to_amount(p.get('price'))
                
                vals = {
                    'name': p.get('name') or 'Unnamed',
                    'gumroad_id': p.get('id'),
                    'gumroad_url': p.get('short_url') or p.get('url'),
                    'price': unit_price,
                    'currency': (p.get('currency') or 'usd').upper(),
                    'published': p.get('published', True),
                    'connector_id': conn.id,
                    'raw_json': json.dumps(p, ensure_ascii=False, indent=2),
                }
                existing = Product.search([('gumroad_id', '=', vals['gumroad_id'])], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    Product.create(vals)

    # ---------- Sync sales ----------
    def action_sync_sales(self, days=1):
        Sale = self.env['agh.gumroad.sale']
        after = (fields.Date.context_today(self) - timedelta(days=days)).isoformat()
        for conn in self:
            if not conn.product_ids:
                conn.action_sync_products()

            page_key = None
            sales_buffer = []
            while True:
                params = {'after': after}
                if page_key:
                    params['page_key'] = page_key
                data = conn._get('/sales', params=params)
                sales_buffer.extend(data.get('sales', []))
                page_key = data.get('next_page_key')
                if not page_key:
                    break

            products_by_gid = {p.gumroad_id: p for p in conn.product_ids}
            for s in sales_buffer:
                gid = s.get('product_id')
                product = products_by_gid.get(gid)
                if not product:
                    continue
                
                quantity = s.get('quantity') or 1
                total_paid = _to_amount(s.get('price'))
                unit = (total_paid / quantity) if quantity else total_paid

                partner = conn._ensure_partner(s)
                vals = {
                    'name': s.get('id'),
                    'product_id': product.id,
                    'partner_id': partner.id if partner else False,
                    'sale_date': s.get('created_at') and s['created_at'].replace('Z', '').replace('T', ' '),
                    'price': unit,
                    'total_price': total_paid,
                    'quantity': quantity,
                    'currency': (s.get('currency') or 'usd').upper(),
                    'email': s.get('email'),
                    'country': s.get('country'),
                    'referrer': s.get('referrer') or 'direct',
                    'refunded': s.get('refunded', False),
                    'raw_json': json.dumps(s, ensure_ascii=False, indent=2),
                }
                existing = Sale.search([('name', '=', vals['name'])], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    Sale.create(vals)

            conn._recompute_metrics(days=days)
            conn.last_sync = fields.Datetime.now()
            conn.status = 'connected'

    def _recompute_metrics(self, days=7):
        Metric = self.env['agh.gumroad.metric']
        today = fields.Date.context_today(self)
        for conn in self:
            for product in conn.product_ids:
                for i in range(days + 1):
                    day = today - timedelta(days=i)
                    start = datetime.combine(day, datetime.min.time())
                    end = start + timedelta(days=1)
                    sales = product.sale_ids.filtered(
                        lambda s: s.sale_date and start <= s.sale_date < end and not s.refunded
                    )
                    if not sales and not Metric.search([('product_id', '=', product.id),
                                                        ('date', '=', day)], limit=1):
                        continue
                    qty = sum(sales.mapped('quantity'))
                    revenue = sum(sales.mapped('total_price'))
                    referrers = {}
                    for s in sales:
                        referrers[s.referrer or 'direct'] = referrers.get(s.referrer or 'direct', 0) + 1
                    top_ref = max(referrers, key=referrers.get) if referrers else False
                    vals = {
                        'product_id': product.id,
                        'date': day,
                        'sales_count': qty,
                        'revenue': revenue,
                        'avg_basket': (revenue / qty) if qty else 0.0,
                        'top_referrer': top_ref,
                    }
                    existing = Metric.search([('product_id', '=', product.id),
                                              ('date', '=', day)], limit=1)
                    if existing:
                        existing.write(vals)
                    else:
                        Metric.create(vals)

    @api.model
    def cron_daily_sync(self):
        for conn in self.search([('auto_sync', '=', True), ('status', '!=', 'error')]):
            try:
                conn.action_sync_sales(days=2)
            except Exception:
                _logger.exception("Gumroad sync failed for %s", conn.name)
                conn.status = 'error'
