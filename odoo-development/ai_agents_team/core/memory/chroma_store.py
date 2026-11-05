"""
core/memory/chroma_store.py
───────────────────────────
Base vectorielle ChromaDB pour le RAG des agents.
Indexe les articles knowledge.article d'Odoo.
"""
import logging
from typing import Optional
import chromadb
from chromadb.config import Settings

_logger = logging.getLogger(__name__)

COLLECTION_KNOWLEDGE = "knowledge_articles"
COLLECTION_BUGS      = "qa_bug_reports"
COLLECTION_TICKETS   = "github_tickets"


class ChromaStore:
    """
    Interface ChromaDB pour la mémoire vectorielle des agents.

    Collections :
    - knowledge_articles : articles Knowledge Odoo (RAG onboarding)
    - qa_bug_reports     : historique des bugs QA (déduplication)
    - github_tickets     : tickets GitHub indexés (triage)
    """

    def __init__(self, persist_path: str = "/data/chromadb"):
        self.client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._init_collections()

    def _init_collections(self):
        """Crée les collections si elles n'existent pas."""
        for name in [COLLECTION_KNOWLEDGE, COLLECTION_BUGS, COLLECTION_TICKETS]:
            self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        _logger.info("✅ ChromaDB collections initialisées")

    # ─── Knowledge Articles ─────────────────────────────────────────

    def upsert_article(self, article_id: int, title: str, content: str,
                       category: str, state: str, embedding: list[float]):
        """Indexe ou met à jour un article Knowledge."""
        col = self.client.get_collection(COLLECTION_KNOWLEDGE)
        col.upsert(
            ids=[str(article_id)],
            embeddings=[embedding],
            documents=[content[:2000]],
            metadatas=[{
                "article_id": article_id,
                "title": title,
                "category": category,
                "state": state,
            }],
        )

    def search_articles(self, query_embedding: list[float],
                        n_results: int = 5, state_filter: Optional[str] = "approved"
                        ) -> list[dict]:
        """
        Recherche les articles les plus pertinents pour une requête.
        :param query_embedding: Embedding de la question
        :param n_results: Nombre de résultats
        :param state_filter: Filtrer par état (approved, draft, None = tous)
        :return: Liste de dicts {article_id, title, content, score}
        """
        col = self.client.get_collection(COLLECTION_KNOWLEDGE)
        where = {"state": state_filter} if state_filter else None
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
        items = []
        for i, doc_id in enumerate(results["ids"][0]):
            items.append({
                "article_id": results["metadatas"][0][i]["article_id"],
                "title":      results["metadatas"][0][i]["title"],
                "content":    results["documents"][0][i],
                "score":      1 - results["distances"][0][i],  # cosine → similarity
            })
        return items

    # ─── Bug Reports QA ─────────────────────────────────────────────

    def upsert_bug(self, bug_id: str, description: str, embedding: list[float],
                   sprint_id: Optional[int] = None):
        """Indexe un rapport de bug pour déduplication future."""
        col = self.client.get_collection(COLLECTION_BUGS)
        meta = {"bug_id": bug_id}
        if sprint_id:
            meta["sprint_id"] = sprint_id
        col.upsert(
            ids=[bug_id],
            embeddings=[embedding],
            documents=[description[:1000]],
            metadatas=[meta],
        )

    def find_similar_bugs(self, embedding: list[float], n_results: int = 3,
                          threshold: float = 0.85) -> list[dict]:
        """Trouve des bugs similaires (déduplication)."""
        col = self.client.get_collection(COLLECTION_BUGS)
        try:
            results = col.query(query_embeddings=[embedding], n_results=n_results)
        except Exception:
            return []
        items = []
        for i, doc_id in enumerate(results["ids"][0]):
            score = 1 - results["distances"][0][i]
            if score >= threshold:
                items.append({
                    "bug_id":      results["metadatas"][0][i]["bug_id"],
                    "description": results["documents"][0][i],
                    "similarity":  score,
                })
        return items

    # ─── GitHub Tickets ─────────────────────────────────────────────

    def upsert_ticket(self, issue_number: int, title: str, body: str,
                      embedding: list[float], labels: list[str] = None):
        """Indexe un ticket GitHub pour le triage contextuel."""
        col = self.client.get_collection(COLLECTION_TICKETS)
        col.upsert(
            ids=[str(issue_number)],
            embeddings=[embedding],
            documents=[f"{title}\n\n{body}"[:1500]],
            metadatas=[{
                "issue_number": issue_number,
                "title": title,
                "labels": ",".join(labels or []),
            }],
        )

    def find_similar_tickets(self, embedding: list[float], n_results: int = 3) -> list[dict]:
        """Trouve des tickets similaires pour le contexte du triage."""
        col = self.client.get_collection(COLLECTION_TICKETS)
        try:
            results = col.query(query_embeddings=[embedding], n_results=n_results)
        except Exception:
            return []
        return [
            {
                "issue_number": results["metadatas"][0][i]["issue_number"],
                "title":        results["metadatas"][0][i]["title"],
                "labels":       results["metadatas"][0][i]["labels"].split(","),
                "similarity":   1 - results["distances"][0][i],
            }
            for i, _ in enumerate(results["ids"][0])
        ]
