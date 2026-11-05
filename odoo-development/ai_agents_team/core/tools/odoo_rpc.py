"""
core/tools/odoo_rpc.py
──────────────────────
Client Odoo XML-RPC pour les agents IA.
Permet de lire/écrire dans tous les modèles Odoo depuis les agents Python.
"""
import os
import logging
import xmlrpc.client
from typing import Any, Optional

_logger = logging.getLogger(__name__)


class OdooRPC:
    """
    Wrapper XML-RPC Odoo simplifié pour les agents IA.

    Variables d'environnement requises :
        ODOO_URL      : http://localhost:8069
        ODOO_DB       : nom_base
        ODOO_USER     : admin@company.com
        ODOO_PASSWORD : mot_de_passe
    """

    def __init__(self):
        self.url      = os.getenv("ODOO_URL", "http://localhost:8069")
        self.db       = os.getenv("ODOO_DB", "odoo")
        self.user     = os.getenv("ODOO_USER", "admin")
        self.password = os.getenv("ODOO_PASSWORD", "admin")
        self._uid: Optional[int] = None
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    # ─── Auth ───────────────────────────────────────────────────────

    def _get_uid(self) -> int:
        if self._uid is None:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self._uid = common.authenticate(self.db, self.user, self.password, {})
            if not self._uid:
                raise RuntimeError("❌ Odoo authentication failed — vérifiez ODOO_USER/ODOO_PASSWORD")
            _logger.info("✅ Odoo connecté (uid=%s)", self._uid)
        return self._uid

    def _execute(self, model: str, method: str, *args, **kwargs) -> Any:
        return self._models.execute_kw(
            self.db, self._get_uid(), self.password,
            model, method, args, kwargs
        )

    # ─── CRUD génériques ────────────────────────────────────────────

    def search_read(self, model: str, domain: list, fields: list,
                    limit: int = 100, order: str = "") -> list[dict]:
        kwargs = {"fields": fields, "limit": limit}
        if order:
            kwargs["order"] = order
        return self._execute(model, "search_read", domain, **kwargs)

    def read(self, model: str, ids: list[int], fields: list) -> list[dict]:
        return self._execute(model, "read", ids, {"fields": fields})

    def create(self, model: str, vals: dict) -> int:
        return self._execute(model, "create", vals)

    def write(self, model: str, ids: list[int], vals: dict) -> bool:
        return self._execute(model, "write", ids, vals)

    def search(self, model: str, domain: list, limit: int = 100) -> list[int]:
        return self._execute(model, "search", domain, {"limit": limit})

    # ─── Méthodes métier spécialisées ───────────────────────────────

    def get_approved_articles(self, limit: int = 500) -> list[dict]:
        """Récupère les articles Knowledge approuvés pour indexation RAG."""
        return self.search_read(
            "knowledge.article",
            [("state", "=", "approved"), ("active", "=", True)],
            ["id", "name", "content", "category_id", "tag_ids", "state"],
            limit=limit,
        )

    def get_active_sprints(self) -> list[dict]:
        """Retourne les sprints Agile en cours."""
        return self.search_read(
            "agile.sprint",
            [("state", "=", "active")],
            ["id", "name", "project_id", "task_ids", "article_ids",
             "story_points_total", "story_points_done", "doc_coverage_pct"],
        )

    def create_knowledge_article(self, title: str, content: str,
                                 category_id: Optional[int] = None,
                                 sprint_id: Optional[int] = None) -> int:
        """Crée un article Knowledge depuis un agent."""
        vals = {
            "name": title,
            "content": content,
            "state": "draft",
        }
        if category_id:
            vals["category_id"] = category_id
        article_id = self.create("knowledge.article", vals)
        if sprint_id:
            # Lier l'article au sprint actif
            self.write("agile.sprint", [sprint_id], {
                "article_ids": [(4, article_id)]
            })
        _logger.info("📄 Article Knowledge créé : id=%s, titre='%s'", article_id, title)
        return article_id

    def link_bug_to_sprint(self, sprint_id: int, task_id: int) -> bool:
        """Lie une tâche bug au sprint actif."""
        return self.write("agile.sprint", [sprint_id], {
            "task_ids": [(4, task_id)]
        })

    def create_bug_task(self, project_id: int, title: str, description: str,
                        story_points: int = 1, sprint_id: Optional[int] = None) -> int:
        """Crée une tâche bug Odoo depuis le QA Agent."""
        vals = {
            "name": f"🐛 [QA] {title}",
            "description": description,
            "project_id": project_id,
            "task_type": "bug",
            "story_points": story_points,
            "moscow": "must",
        }
        task_id = self.create("project.task", vals)
        if sprint_id:
            self.link_bug_to_sprint(sprint_id, task_id)
        return task_id

    def log_agent_run(self, agent_name: str, status: str,
                      summary: str, details: str = "") -> int:
        """Enregistre une exécution d'agent dans le log Odoo."""
        return self.create("ai.agent.run.log", {
            "agent_name": agent_name,
            "status": status,
            "summary": summary,
            "details": details,
        })
