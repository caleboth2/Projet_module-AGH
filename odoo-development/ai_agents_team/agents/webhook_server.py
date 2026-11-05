"""
agents/webhook_server.py
─────────────────────────
Serveur webhook aiohttp — reçoit les événements GitHub et orchestre les agents.
Lance aussi les tâches planifiées (QA quotidien, sync KB).
"""
import os
import json
import hmac
import hashlib
import asyncio
import logging
from datetime import datetime

import aiohttp
from aiohttp import web

from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent

_logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "").encode()
PORT = int(os.getenv("WEBHOOK_PORT", "8080"))


# ─── Vérification signature GitHub ────────────────────────────────

def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Vérifie la signature HMAC-SHA256 du webhook GitHub."""
    if not WEBHOOK_SECRET:
        return True  # Dev mode sans secret
    expected = "sha256=" + hmac.new(WEBHOOK_SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ─── Handlers webhook ─────────────────────────────────────────────

async def handle_github_webhook(request: web.Request) -> web.Response:
    """Handler principal du webhook GitHub."""
    payload = await request.read()

    # Vérifier la signature
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(payload, sig):
        _logger.warning("⚠️ Webhook signature invalide")
        return web.Response(status=401, text="Invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    data  = json.loads(payload)

    _logger.info("📨 Webhook GitHub reçu : event=%s, action=%s",
                 event, data.get("action", ""))

    # Traitement asynchrone pour ne pas bloquer le webhook
    asyncio.create_task(dispatch_event(event, data))

    return web.Response(status=200, text="OK")


async def dispatch_event(event: str, data: dict):
    """Dispatch asynchrone des événements GitHub vers les agents."""
    try:
        if event == "issues":
            action = data.get("action", "")
            issue_number = data["issue"]["number"]

            if action in ("opened", "reopened"):
                _logger.info("🎯 [Dispatcher] Nouvelle issue #%d → Triage Agent", issue_number)
                agent = TriageAgent()
                result = agent.triage_issue(issue_number)
                _logger.info("✅ [Dispatcher] Triage terminé : %s", result)

            elif action == "labeled" and _is_qa_label(data):
                _logger.info("🧪 [Dispatcher] Issue #%d labelisée qa-needed → QA Agent", issue_number)
                # Déclencher le QA Agent si l'issue concerne un build Android
                # (implémenté dans le scheduler QA)

    except Exception as e:
        _logger.error("❌ [Dispatcher] Erreur dispatch event %s : %s", event, e)


def _is_qa_label(data: dict) -> bool:
    """Vérifie si le label ajouté est 'qa-needed'."""
    label = data.get("label", {}).get("name", "")
    return label == "qa-needed"


# ─── Handler Q&A Knowledge ────────────────────────────────────────

async def handle_knowledge_query(request: web.Request) -> web.Response:
    """
    Endpoint REST pour le Knowledge Explorer Agent.
    POST /api/knowledge/ask  {"question": "...", "auto_create": true}
    """
    try:
        data = await request.json()
        question = data.get("question", "").strip()
        if not question:
            return web.json_response({"error": "question requise"}, status=400)

        agent = KnowledgeExplorerAgent()
        result = agent.ask(question, auto_create_missing=data.get("auto_create", True))

        return web.json_response({
            "question":           result.question,
            "answer":             result.answer,
            "sources":            result.sources,
            "confidence":         result.confidence,
            "gap_detected":       result.gap_detected,
            "articles_created":   result.articles_created,
            "suggested_articles": result.suggested_articles,
        })
    except Exception as e:
        _logger.error("❌ [KB API] Erreur : %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def handle_reindex(request: web.Request) -> web.Response:
    """POST /api/knowledge/reindex — Réindexe la KB dans ChromaDB."""
    agent = KnowledgeExplorerAgent()
    count = agent.reindex_knowledge_base()
    return web.json_response({"indexed": count, "timestamp": datetime.now().isoformat()})


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — Health check pour monitoring."""
    return web.json_response({
        "status": "ok",
        "agents": ["qa_explorer", "triage_agent", "knowledge_explorer"],
        "timestamp": datetime.now().isoformat(),
    })


# ─── Application aiohttp ──────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/webhook/github",       handle_github_webhook)
    app.router.add_post("/api/knowledge/ask",    handle_knowledge_query)
    app.router.add_post("/api/knowledge/reindex", handle_reindex)
    app.router.add_get("/health",                handle_health)
    return app


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    _logger.info("🚀 AI Agents Team Webhook Server — port %d", PORT)
    web.run_app(create_app(), port=PORT)
