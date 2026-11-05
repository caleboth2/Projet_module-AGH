"""
core/tools/github_tool.py
─────────────────────────
Client GitHub REST API pour le Triage Agent.
Gère : lecture issues, ajout labels, assignation, commentaires.
"""
import os
import logging
import requests
from typing import Optional

_logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubTool:
    """
    Wrapper GitHub REST API pour le Triage Agent.

    Variables d'environnement requises :
        GITHUB_TOKEN : ghp_xxxxxxxxxxxxxxxxxxxx
        GITHUB_REPO  : AGH-Data-Agency-Holding/odoo-development
    """

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.repo  = os.getenv("GITHUB_REPO", "AGH-Data-Agency-Holding/odoo-development")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    # ─── Issues ─────────────────────────────────────────────────────

    def get_issue(self, issue_number: int) -> dict:
        """Récupère une issue GitHub."""
        resp = self.session.get(
            f"{GITHUB_API}/repos/{self.repo}/issues/{issue_number}",
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def list_open_issues(self, labels: list[str] = None, limit: int = 30) -> list[dict]:
        """Liste les issues ouvertes, optionnellement filtrées par labels."""
        params = {"state": "open", "per_page": limit}
        if labels:
            params["labels"] = ",".join(labels)
        resp = self.session.get(
            f"{GITHUB_API}/repos/{self.repo}/issues",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def add_labels(self, issue_number: int, labels: list[str]) -> bool:
        """Ajoute des labels à une issue."""
        resp = self.session.post(
            f"{GITHUB_API}/repos/{self.repo}/issues/{issue_number}/labels",
            json={"labels": labels},
            timeout=15,
        )
        return resp.status_code in (200, 201)

    def set_assignees(self, issue_number: int, assignees: list[str]) -> bool:
        """Assigne des développeurs à une issue."""
        resp = self.session.post(
            f"{GITHUB_API}/repos/{self.repo}/issues/{issue_number}/assignees",
            json={"assignees": assignees},
            timeout=15,
        )
        return resp.status_code in (200, 201)

    def post_comment(self, issue_number: int, body: str) -> bool:
        """Poste un commentaire de triage automatique."""
        resp = self.session.post(
            f"{GITHUB_API}/repos/{self.repo}/issues/{issue_number}/comments",
            json={"body": body},
            timeout=15,
        )
        return resp.status_code == 201

    def update_issue(self, issue_number: int, title: Optional[str] = None,
                     body: Optional[str] = None, milestone: Optional[int] = None) -> bool:
        """Met à jour une issue (titre, corps, milestone)."""
        payload = {}
        if title:
            payload["title"] = title
        if body:
            payload["body"] = body
        if milestone:
            payload["milestone"] = milestone
        if not payload:
            return True
        resp = self.session.patch(
            f"{GITHUB_API}/repos/{self.repo}/issues/{issue_number}",
            json=payload,
            timeout=15,
        )
        return resp.status_code == 200

    def create_issue(self, title: str, body: str,
                     labels: list[str] = None,
                     assignees: list[str] = None) -> dict:
        """Crée une nouvelle issue GitHub (utilisé par le QA Agent pour les bugs)."""
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        resp = self.session.post(
            f"{GITHUB_API}/repos/{self.repo}/issues",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        issue = resp.json()
        _logger.info("🐛 Issue GitHub créée : #%s — %s", issue["number"], title)
        return issue

    # ─── Labels ─────────────────────────────────────────────────────

    def ensure_labels_exist(self, labels_config: list[dict]) -> None:
        """
        S'assure que les labels nécessaires existent dans le repo.
        labels_config = [{"name": "bug", "color": "d73a4a", "description": "..."}]
        """
        existing = {
            lbl["name"]
            for lbl in self.session.get(
                f"{GITHUB_API}/repos/{self.repo}/labels",
                params={"per_page": 100},
            ).json()
        }
        for lbl in labels_config:
            if lbl["name"] not in existing:
                self.session.post(
                    f"{GITHUB_API}/repos/{self.repo}/labels",
                    json=lbl,
                    timeout=10,
                )
                _logger.info("🏷️ Label créé : %s", lbl["name"])
