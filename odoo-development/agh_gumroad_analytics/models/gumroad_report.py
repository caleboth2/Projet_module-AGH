"""Génération hebdomadaire d'un rapport IA d'analyse commerciale.

Souveraineté : l'IA est appelée localement via Ollama (http://host.docker.internal:11434),
les données financières ne quittent jamais l'infrastructure AGH."""
import logging
from datetime import timedelta
import json

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None


# URL souveraine Ollama (overridable via ir.config_parameter)
DEFAULT_OLLAMA_URL = 'http://host.docker.internal:11434'
DEFAULT_OLLAMA_MODEL = 'llama3.1'

KNOWLEDGE_CATEGORY = 'Analyses Commerciales / Gumroad'


class AghGumroadReport(models.Model):
    _name = 'agh.gumroad.report'
    _description = 'AGH Gumroad Weekly AI Report'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char('Title', required=True)
    date = fields.Date('Report Date', default=fields.Date.context_today, required=True)
    period_start = fields.Date('Period Start')
    period_end = fields.Date('Period End')
    content_html = fields.Html('Report Content')
    summary = fields.Text('Executive Summary')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('published', 'Published'),
    ], default='draft', tracking=True)

    total_revenue = fields.Float('Total Revenue (period)')
    total_sales = fields.Integer('Total Sales (period)')
    growth_rate = fields.Float('Growth vs previous period (%)')

    knowledge_article_id = fields.Char('Knowledge Article')

    # ---------- Aggregation ----------
    @api.model
    def _aggregate_period(self, start, end):
        Product = self.env['agh.gumroad.product']
        result = []
        for product in Product.search([]):
            sales = product.sale_ids.filtered(
                lambda s: s.sale_date and start <= s.sale_date.date() <= end and not s.refunded
            )
            qty = sum(sales.mapped('quantity'))
            revenue = sum(sales.mapped('total_price'))
            referrers = {}
            for s in sales:
                referrers[s.referrer or 'direct'] = referrers.get(s.referrer or 'direct', 0) + 1
            result.append({
                'product': product.name,
                'project': product.project_id.name or '-',
                'sales': qty,
                'revenue': round(revenue, 2),
                'avg_basket': round(revenue / qty, 2) if qty else 0,
                'top_sources': sorted(referrers.items(), key=lambda x: -x[1])[:3],
                'roi': round(product.project_id.gumroad_roi, 1) if product.project_id else 0,
            })
        return result

    # ---------- IA souveraine (Ollama local) ----------
    def _call_ai(self, prompt):
        """Appel LLM **local** via Ollama. Aucune donnée ne sort de l'infrastructure AGH.
        Endpoint : http://host.docker.internal:11434/api/chat
        Modèle par défaut : llama3.1 (paramétrable via ir.config_parameter)."""
        ICP = self.env['ir.config_parameter'].sudo()
        base_url = (ICP.get_param('agh_gumroad_analytics.ollama_url') or DEFAULT_OLLAMA_URL).rstrip('/')
        model = ICP.get_param('agh_gumroad_analytics.ollama_model') or DEFAULT_OLLAMA_MODEL

        if not requests:
            return self._fallback_report(prompt)

        system_msg = (
            "Tu es un analyste commercial pour AGH Consulting. Réponds en français, "
            "format HTML structuré avec les sections : "
            "<h2>Synthèse</h2>, <h2>Tendances</h2>, <h2>Cash cows</h2>, "
            "<h2>Apps à faible traction</h2>, <h2>Recommandations</h2>, <h2>Alertes</h2>. "
            "Sois concis et actionnable."
        )
        try:
            r = requests.post(
                f'{base_url}/api/chat',
                json={
                    'model': model,
                    'stream': False,
                    'messages': [
                        {'role': 'system', 'content': system_msg},
                        {'role': 'user', 'content': prompt},
                    ],
                    'options': {'temperature': 0.4},
                },
                timeout=180,
            )
            if r.status_code == 200:
                payload = r.json()
                content = (payload.get('message') or {}).get('content') or payload.get('response')
                if content:
                    return content
                _logger.warning("Ollama returned empty content: %s", payload)
            else:
                _logger.warning("Ollama error %s: %s", r.status_code, r.text[:200])
        except Exception:
            _logger.exception("Ollama call failed (souveraineté: pas de fallback cloud)")
        return self._fallback_report(prompt)

    def _fallback_report(self, prompt):
        return ("<h2>Rapport hebdomadaire Gumroad (mode fallback)</h2>"
                "<p><i>IA locale Ollama indisponible. Vérifiez que le service "
                "tourne sur http://host.docker.internal:11434.</i></p>"
                f"<pre>{(prompt or '')[:4000]}</pre>")

    # ---------- Generation ----------
    def action_generate(self):
        for report in self:
            end = report.period_end or fields.Date.context_today(self)
            start = report.period_start or (end - timedelta(days=7))
            data = self._aggregate_period(start, end)
            prev_data = self._aggregate_period(start - timedelta(days=7), start - timedelta(days=1))

            total_rev = sum(d['revenue'] for d in data)
            total_sales = sum(d['sales'] for d in data)
            prev_rev = sum(d['revenue'] for d in prev_data)
            growth = ((total_rev - prev_rev) / prev_rev * 100.0) if prev_rev else 0.0

            prompt = (
                f"Analyse les performances commerciales Gumroad du {start} au {end}.\n\n"
                f"Données période courante:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n\n"
                f"Données période précédente:\n{json.dumps(prev_data, indent=2, ensure_ascii=False)}\n\n"
                f"Revenu total: {total_rev:.2f} (vs {prev_rev:.2f}, croissance {growth:.1f}%)\n"
                f"Ventes totales: {total_sales}\n\n"
                "Identifie les apps cash cow, les apps à faible traction, recommande "
                "des priorisations ou arrêts, et signale toute anomalie (chute > 30% ou pic > 50%)."
            )
            content = report._call_ai(prompt)
            report.write({
                'period_start': start,
                'period_end': end,
                'content_html': content,
                'total_revenue': total_rev,
                'total_sales': total_sales,
                'growth_rate': growth,
                'state': 'generated',
            })
        return True

    # ---------- Knowledge auto-classification ----------
    def _get_or_create_knowledge_parent(self):
        """Renvoie l'article racine 'Analyses Commerciales / Gumroad' (le crée si absent).
        Compatible avec le module Knowledge standard ainsi qu'avec knowledge_plus_final_v3."""
        Article = self.env.get('knowledge.article')
        if Article is None:
            return False
        parts = [p.strip() for p in KNOWLEDGE_CATEGORY.split('/') if p.strip()]
        parent = False
        for label in parts:
            domain = [('name', '=', label)]
            domain.append(('parent_id', '=', parent.id if parent else False))
            node = Article.search(domain, limit=1)
            if not node:
                vals = {'name': label}
                if parent:
                    vals['parent_id'] = parent.id
                # Champs optionnels selon variantes du module Knowledge
                if 'internal_permission' in Article._fields:
                    vals['internal_permission'] = 'write'
                if 'is_article_visible_by_everyone' in Article._fields:
                    vals['is_article_visible_by_everyone'] = True
                node = Article.create(vals)
            parent = node
        return parent

    def action_publish_to_knowledge(self):
        Article = self.env.get('knowledge.article')
        for report in self:
            if Article is None:
                report.message_post(body=_("Module Knowledge non installé."))
                report.state = 'published'
                continue
            parent = report._get_or_create_knowledge_parent()
            vals = {
                'name': report.name,
                'body': report.content_html or '',
            }
            if parent:
                vals['parent_id'] = parent.id
            article = Article.create(vals)
            report.knowledge_article_id = article.display_name
            report.state = 'published'
        return True

    @api.model
    def cron_weekly_report(self):
        end = fields.Date.context_today(self)
        start = end - timedelta(days=7)
        report = self.create({
            'name': _('Gumroad Weekly Report - %s') % end,
            'period_start': start,
            'period_end': end,
        })
        report.action_generate()
        report.action_publish_to_knowledge()
        for line in report._aggregate_period(start, end):
            prev = next((p for p in report._aggregate_period(
                start - timedelta(days=7), start - timedelta(days=1))
                if p['product'] == line['product']), None)
            if prev and prev['revenue'] > 0:
                delta = (line['revenue'] - prev['revenue']) / prev['revenue'] * 100
                if delta < -30:
                    _logger.warning("ALERTE: chute de %.1f%% sur %s", delta, line['product'])
        return True
