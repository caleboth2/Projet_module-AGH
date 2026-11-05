"""
models/ai_agent_run_log.py
───────────────────────────
Modèle Odoo pour le monitoring des agents IA.
Enregistre chaque exécution, statut et KPIs dans la base Odoo.
"""
from odoo import models, fields, api


class AiAgentRunLog(models.Model):
    """
    Historique des exécutions des agents IA.
    Alimenté automatiquement par OdooRPC.log_agent_run().
    """
    _name = 'ai.agent.run.log'
    _description = 'Log d\'exécution — Agents IA'
    _order = 'create_date desc'
    _rec_name = 'summary'

    agent_name = fields.Selection([
        ('QA Explorer',        '🧪 QA Explorer'),
        ('Triage Agent',       '🎯 Triage Agent'),
        ('Knowledge Explorer', '📚 Knowledge Explorer'),
    ], string='Agent', required=True, index=True)

    status = fields.Selection([
        ('success', '✅ Succès'),
        ('warning', '⚠️ Avertissement'),
        ('error',   '❌ Erreur'),
        ('running', '🔄 En cours'),
    ], string='Statut', default='running', required=True)

    summary = fields.Char(string='Résumé', required=True)
    details = fields.Text(string='Détails techniques')

    # ── KPIs par agent ────────────────────────────────────────────
    # QA Explorer
    bugs_found      = fields.Integer(string='Bugs détectés', default=0)
    tickets_created = fields.Integer(string='Tickets créés',  default=0)
    apk_version     = fields.Char(string='Version APK testée')

    # Triage Agent
    issues_triaged  = fields.Integer(string='Issues triées', default=0)
    articles_linked = fields.Integer(string='Articles Knowledge liés', default=0)

    # Knowledge Explorer
    questions_answered = fields.Integer(string='Questions répondues', default=0)
    articles_auto_created = fields.Integer(string='Articles auto-créés', default=0)
    avg_confidence = fields.Float(string='Confiance moyenne RAG (%)', digits=(5, 1))

    duration_seconds = fields.Float(string='Durée (s)', digits=(10, 2))

    @api.model
    def get_dashboard_data(self) -> dict:
        """Agrège les KPIs pour le tableau de bord Odoo."""
        agents = ['QA Explorer', 'Triage Agent', 'Knowledge Explorer']
        data = {}
        for agent in agents:
            last = self.search([('agent_name', '=', agent)], limit=1)
            total = self.search_count([('agent_name', '=', agent)])
            errors = self.search_count([
                ('agent_name', '=', agent),
                ('status', '=', 'error'),
            ])
            data[agent] = {
                'last_run':    last.create_date.isoformat() if last and last.create_date else None,
                'last_status': last.status if last else 'never',
                'last_summary': last.summary if last else 'Aucune exécution',
                'total_runs':  total,
                'error_count': errors,
            }
        return data


class AiAgentConfig(models.Model):
    """
    Configuration globale des agents IA (URL serveur, tokens, options).
    Accessible depuis Knowledge > Configuration > Agents IA.
    """
    _name = 'ai.agent.config'
    _description = 'Configuration — Agents IA'
    _rec_name = 'name'

    name = fields.Char(string='Nom', required=True, default='Configuration Agents IA')
    active = fields.Boolean(default=True)

    # ── Serveur agents ─────────────────────────────────────────────
    webhook_url = fields.Char(
        string='URL Webhook Agents',
        default='http://localhost:8080',
        help='URL du serveur webhook des agents IA (webhook_server.py)',
    )

    # ── LLM Local ─────────────────────────────────────────────────
    local_llm_url = fields.Char(
        string='URL LLM Local (Ollama)',
        default='http://localhost:11434',
    )
    local_llm_model = fields.Char(
        string='Modèle local',
        default='mistral:7b-instruct',
    )

    # ── QA Explorer ───────────────────────────────────────────────
    qa_enabled       = fields.Boolean(string='QA Explorer actif', default=True)
    qa_monkey_events = fields.Integer(string='Monkey Events', default=500)
    android_device   = fields.Char(string='Device ADB', default='emulator-5554')

    # ── Triage Agent ──────────────────────────────────────────────
    triage_enabled   = fields.Boolean(string='Triage Agent actif', default=True)
    github_repo      = fields.Char(
        string='GitHub Repo',
        default='AGH-Data-Agency-Holding/odoo-development',
    )

    # ── Knowledge Explorer ────────────────────────────────────────
    knowledge_enabled       = fields.Boolean(string='Knowledge Explorer actif', default=True)
    knowledge_reindex_cron  = fields.Boolean(
        string='Réindexation auto (nuit)', default=True,
    )
    rag_relevance_threshold = fields.Float(
        string='Seuil pertinence RAG', default=0.65, digits=(3, 2),
    )

    def action_trigger_reindex(self):
        """Déclenche la réindexation de la KB depuis l'interface Odoo."""
        import requests
        config = self.search([], limit=1)
        if not config:
            return
        try:
            resp = requests.post(
                f"{config.webhook_url}/api/knowledge/reindex",
                timeout=300,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '✅ Réindexation terminée',
                    'message': f"{data.get('indexed', 0)} articles indexés dans ChromaDB",
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as e:
            raise models.ValidationError(f"Erreur réindexation : {e}")
