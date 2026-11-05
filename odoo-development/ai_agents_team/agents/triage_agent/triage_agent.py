"""
agents/triage_agent/triage_agent.py
────────────────────────────────────
Triage Agent — Qualification et Assignation Automatique des Tickets GitHub.

Flux :
  1. Écoute les webhooks GitHub (nouvelles issues / issues modifiées)
  2. Analyse le contenu via LLM local
  3. Qualifie : bug / feature / question / doc
  4. Calcule la priorité MoSCoW
  5. Assigne au développeur le plus adapté
  6. Crée/met à jour l'article Knowledge associé dans Odoo
  7. Ajoute le ticket au sprint actif de l'Epic concerné
"""
import os
import json
import logging
import re
from typing import Optional

from ai_agents_team.core.llm.connector import LLMConnector
from ai_agents_team.core.memory.chroma_store import ChromaStore
from ai_agents_team.core.tools.odoo_rpc import OdooRPC
from ai_agents_team.core.tools.github_tool import GitHubTool

_logger = logging.getLogger(__name__)


# ── Configuration des développeurs et leurs compétences ────────────
TEAM_MATRIX = json.loads(os.getenv("TEAM_MATRIX", """
[
  {"github": "dev-backend",   "skills": ["odoo", "python", "api", "database", "migration"],
   "odoo_user_id": 3},
  {"github": "dev-android",   "skills": ["android", "kotlin", "java", "mobile", "adb"],
   "odoo_user_id": 4},
  {"github": "dev-frontend",  "skills": ["javascript", "xml", "css", "views", "qweb"],
   "odoo_user_id": 5},
  {"github": "lead-ba",       "skills": ["specification", "knowledge", "documentation", "agile"],
   "odoo_user_id": 2}
]
"""))

# Catégories de knowledge pour les articles auto-créés
TRIAGE_CATEGORY_MAP = {
    "bug":     "Bugs & Correctifs",
    "feature": "Fonctionnalités",
    "question": "FAQ & Support",
    "doc":     "Documentation",
}


class TriageAgent:
    """
    Agent de triage automatique des tickets GitHub.
    Qualifie, priorise, assigne et synchronise avec Odoo Knowledge + Agile.
    """

    SYSTEM_PROMPT = (
        "Tu es un expert en gestion de projet Agile spécialisé dans le triage de tickets. "
        "Tu analyses les titres et descriptions de tickets GitHub et retournes UNIQUEMENT "
        "un objet JSON (sans markdown) avec ces champs :\n"
        "- type: 'bug' | 'feature' | 'question' | 'doc'\n"
        "- moscow: 'must' | 'should' | 'could' | 'wont'\n"
        "- priority: 'critical' | 'high' | 'medium' | 'low'\n"
        "- skills_needed: liste de compétences techniques requises (max 4)\n"
        "- story_points: estimation 1-8\n"
        "- epic_keywords: mots-clés pour identifier l'Epic concerné (max 3)\n"
        "- summary_fr: résumé du ticket en 1 phrase en français\n"
        "- triage_comment: commentaire de triage professionnel en français (2-3 phrases)\n"
        "Sois précis et factuel."
    )

    def __init__(self):
        self.llm    = LLMConnector()
        self.memory = ChromaStore()
        self.odoo   = OdooRPC()
        self.github = GitHubTool()

    # ─── Point d'entrée principal ────────────────────────────────────

    def triage_issue(self, issue_number: int) -> dict:
        """
        Triage complet d'une issue GitHub.

        :param issue_number: Numéro de l'issue GitHub
        :return: Résultat du triage {type, moscow, assignee, article_id, sprint_id}
        """
        _logger.info("🎯 [Triage Agent] Issue #%d", issue_number)

        # 1. Récupérer l'issue
        issue = self.github.get_issue(issue_number)
        title = issue.get("title", "")
        body  = issue.get("body", "") or ""

        # 2. Analyse LLM
        triage = self._analyze_with_llm(title, body)
        _logger.info("📊 [Triage Agent] Analyse : type=%s, moscow=%s, priority=%s",
                     triage.get("type"), triage.get("moscow"), triage.get("priority"))

        # 3. Appliquer les labels GitHub
        labels = self._build_labels(triage)
        self.github.add_labels(issue_number, labels)

        # 4. Trouver et assigner le développeur
        assignee = self._find_best_assignee(triage.get("skills_needed", []))
        if assignee:
            self.github.set_assignees(issue_number, [assignee["github"]])

        # 5. Poster un commentaire de triage
        self.github.post_comment(
            issue_number,
            self._build_triage_comment(triage, assignee, issue_number)
        )

        # 6. Synchroniser avec Odoo
        article_id = self._sync_with_knowledge(issue, triage)
        sprint_id  = self._link_to_sprint(issue, triage, assignee)

        # 7. Indexer dans ChromaDB
        self._index_ticket(issue, triage)

        # 8. Logger dans Odoo
        summary = (
            f"Issue #{issue_number} triée : {triage.get('type')} / "
            f"{triage.get('moscow')} → {assignee['github'] if assignee else 'non assigné'}"
        )
        self.odoo.log_agent_run("Triage Agent", "success", summary)

        return {
            "issue_number": issue_number,
            "type":         triage.get("type"),
            "moscow":       triage.get("moscow"),
            "priority":     triage.get("priority"),
            "assignee":     assignee["github"] if assignee else None,
            "article_id":   article_id,
            "sprint_id":    sprint_id,
            "labels":       labels,
        }

    def triage_all_open(self) -> list[dict]:
        """Triage de toutes les issues ouvertes non encore triées."""
        issues = self.github.list_open_issues(limit=50)
        untriaged = [
            i for i in issues
            if not any(lbl["name"] in ["triage:bug", "triage:feature", "triage:question"]
                       for lbl in i.get("labels", []))
        ]
        _logger.info("🎯 [Triage Agent] %d issue(s) à trier", len(untriaged))
        results = []
        for issue in untriaged:
            try:
                result = self.triage_issue(issue["number"])
                results.append(result)
            except Exception as e:
                _logger.error("❌ [Triage Agent] Erreur issue #%d : %s", issue["number"], e)
        return results

    # ─── Analyse LLM ────────────────────────────────────────────────

    def _analyze_with_llm(self, title: str, body: str) -> dict:
        """Analyse le ticket avec le LLM et retourne le triage structuré."""
        user_msg = (
            f"Triage ce ticket GitHub :\n\n"
            f"**Titre** : {title}\n\n"
            f"**Description** :\n{body[:3000] if body else '(vide)'}"
        )
        try:
            raw = self.llm.chat(self.SYSTEM_PROMPT, user_msg)
            raw = re.sub(r"```json|```", "", raw).strip()
            return json.loads(raw)
        except Exception as e:
            _logger.error("❌ [Triage Agent] Erreur LLM : %s", e)
            return {
                "type": "question", "moscow": "could", "priority": "low",
                "skills_needed": [], "story_points": 1, "epic_keywords": [],
                "summary_fr": title, "triage_comment": "Triage automatique indisponible.",
            }

    # ─── Assignation ────────────────────────────────────────────────

    def _find_best_assignee(self, skills_needed: list[str]) -> Optional[dict]:
        """Trouve le développeur avec le plus de compétences correspondantes."""
        if not skills_needed:
            return None
        scores = []
        for dev in TEAM_MATRIX:
            score = sum(1 for s in skills_needed if s.lower() in dev["skills"])
            scores.append((score, dev))
        scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_dev = scores[0]
        return best_dev if best_score > 0 else None

    # ─── Labels ─────────────────────────────────────────────────────

    def _build_labels(self, triage: dict) -> list[str]:
        """Construit la liste des labels GitHub à appliquer."""
        labels = [f"triage:{triage.get('type', 'question')}"]
        moscow = triage.get("moscow", "could")
        if moscow in ("must", "should"):
            labels.append(f"moscow:{moscow}")
        priority = triage.get("priority", "low")
        if priority in ("critical", "high"):
            labels.append(f"priority:{priority}")
        return labels

    # ─── Commentaire ────────────────────────────────────────────────

    def _build_triage_comment(self, triage: dict, assignee: Optional[dict],
                               issue_number: int) -> str:
        assignee_mention = f"@{assignee['github']}" if assignee else "*(assignation manuelle requise)*"
        moscow_labels = {
            "must": "🔴 Must Have",
            "should": "🟡 Should Have",
            "could": "🟢 Could Have",
            "wont": "⚪ Won't Have",
        }
        return f"""## 🤖 Triage Automatique — AI Agents Team

**Type** : `{triage.get('type', 'question')}` | **Priorité MoSCoW** : {moscow_labels.get(triage.get('moscow', 'could'))}
**Points estimés** : `{triage.get('story_points', 1)} SP` | **Assigné** : {assignee_mention}

### 📋 Résumé
{triage.get('summary_fr', '')}

### 💬 Notes de triage
{triage.get('triage_comment', '')}

---
*🤖 Triage automatique par le Triage Agent (Issue #45) — Vérifiez et ajustez si nécessaire.*
"""

    # ─── Synchronisation Odoo ────────────────────────────────────────

    def _sync_with_knowledge(self, issue: dict, triage: dict) -> Optional[int]:
        """
        Crée ou met à jour un article Knowledge Odoo pour ce ticket.
        Retourne l'ID de l'article créé/mis à jour.
        """
        try:
            issue_number = issue["number"]
            title  = issue.get("title", "")
            body   = issue.get("body", "") or ""
            cat_name = TRIAGE_CATEGORY_MAP.get(triage.get("type", "question"), "FAQ & Support")

            # Chercher une catégorie existante dans Odoo
            cats = self.odoo.search_read(
                "knowledge.category",
                [("name", "ilike", cat_name)],
                ["id", "name"],
                limit=1,
            )
            cat_id = cats[0]["id"] if cats else None

            content = (
                f"<h2>GitHub Issue #{issue_number}</h2>"
                f"<p><strong>Type :</strong> {triage.get('type')} | "
                f"<strong>Priorité :</strong> {triage.get('moscow')}</p>"
                f"<h3>Description</h3>"
                f"<p>{body[:2000]}</p>"
                f"<h3>Résumé IA</h3>"
                f"<p>{triage.get('summary_fr', '')}</p>"
            )

            article_id = self.odoo.create_knowledge_article(
                title=f"[GitHub #{issue_number}] {title}",
                content=content,
                category_id=cat_id,
            )
            _logger.info("📄 [Triage Agent] Article Knowledge créé : id=%s", article_id)
            return article_id
        except Exception as e:
            _logger.error("❌ [Triage Agent] Erreur sync Knowledge : %s", e)
            return None

    def _link_to_sprint(self, issue: dict, triage: dict,
                         assignee: Optional[dict]) -> Optional[int]:
        """Lie le ticket au sprint actif si priorité must/should."""
        if triage.get("moscow") not in ("must", "should"):
            return None
        try:
            sprints = self.odoo.get_active_sprints()
            if not sprints:
                return None
            sprint = sprints[0]
            # Créer une tâche dans le sprint
            project_id = sprint["project_id"][0] if isinstance(sprint["project_id"], list) else 1
            task_id = self.odoo.create_bug_task(
                project_id=project_id,
                title=issue.get("title", ""),
                description=f"GitHub Issue #{issue['number']}",
                story_points=triage.get("story_points", 1),
                sprint_id=sprint["id"],
            )
            _logger.info("🏃 [Triage Agent] Tâche %s liée au sprint '%s'",
                         task_id, sprint["name"])
            return sprint["id"]
        except Exception as e:
            _logger.error("❌ [Triage Agent] Erreur liaison sprint : %s", e)
            return None

    def _index_ticket(self, issue: dict, triage: dict):
        """Indexe le ticket dans ChromaDB pour future contextualisation."""
        try:
            text = f"{issue.get('title', '')} {issue.get('body', '')}"
            embedding = self.llm.embed(text[:1000])
            self.memory.upsert_ticket(
                issue_number=issue["number"],
                title=issue.get("title", ""),
                body=issue.get("body", "") or "",
                embedding=embedding,
                labels=[triage.get("type", ""), triage.get("moscow", "")],
            )
        except Exception as e:
            _logger.warning("⚠️ [Triage Agent] Erreur indexation ChromaDB : %s", e)
