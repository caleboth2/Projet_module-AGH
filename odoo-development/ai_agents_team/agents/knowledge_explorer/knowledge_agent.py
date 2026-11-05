"""
agents/knowledge_explorer/knowledge_agent.py
─────────────────────────────────────────────
Knowledge Explorer Agent — Support Onboarding par RAG sur la KB Odoo.

Flux :
  1. Reçoit une question utilisateur (onboarding / support)
  2. Génère un embedding de la question
  3. Cherche les articles Knowledge les plus pertinents (ChromaDB)
  4. Génère une réponse fondée (grounded) via LLM + contexte KB
  5. Score la pertinence — si faible → déclenche suggest_missing_content
  6. Génère automatiquement des articles manquants via les templates BA
"""
import logging
from typing import Optional
from dataclasses import dataclass, field

from ai_agents_team.core.llm.connector import LLMConnector
from ai_agents_team.core.memory.chroma_store import ChromaStore
from ai_agents_team.core.tools.odoo_rpc import OdooRPC

_logger = logging.getLogger(__name__)

# Seuil de pertinence : en dessous → réponse insuffisante, générer du contenu
RELEVANCE_THRESHOLD = 0.65
# Seuil minimal pour inclure un article dans le contexte RAG
MIN_ARTICLE_SCORE   = 0.50


@dataclass
class KnowledgeAnswer:
    """Réponse structurée du Knowledge Explorer Agent."""
    question: str
    answer: str
    sources: list[dict] = field(default_factory=list)   # [{article_id, title, score}]
    confidence: float = 0.0
    gap_detected: bool = False
    articles_created: list[int] = field(default_factory=list)
    suggested_articles: list[str] = field(default_factory=list)


class KnowledgeExplorerAgent:
    """
    Agent Knowledge : Q&A conversationnel sur la base de connaissances Odoo.
    Intègre RAG, détection de lacunes et génération automatique de contenu.
    """

    SYSTEM_RAG = (
        "Tu es un assistant expert en onboarding et support pour une App Factory. "
        "Tu réponds aux questions en te basant UNIQUEMENT sur les extraits de la base de "
        "connaissances fournis. Si la réponse n'est pas dans les extraits, dis-le clairement "
        "et suggère de créer la documentation manquante. "
        "Réponds en français, de manière concise et structurée. "
        "Cite les sources par leur titre entre [crochets]."
    )

    SYSTEM_GAP_DETECTION = (
        "Tu es un consultant en documentation pour une équipe Agile. "
        "Analyse la question posée et les articles existants fournis. "
        "Identifie les ARTICLES MANQUANTS et génère un titre pour chacun. "
        "Réponds en JSON uniquement : "
        '{"missing_articles": [{"title": "...", "template_type": "user_stories|market_study|'
        'personas|strategic_decision|post_mortem|general"}]}'
    )

    def __init__(self):
        self.llm    = LLMConnector()
        self.memory = ChromaStore()
        self.odoo   = OdooRPC()

    # ─── Point d'entrée principal ────────────────────────────────────

    def ask(self, question: str, auto_create_missing: bool = True) -> KnowledgeAnswer:
        """
        Répond à une question d'onboarding/support via RAG.

        :param question:             Question de l'utilisateur
        :param auto_create_missing:  Si True, crée automatiquement les articles manquants
        :return: KnowledgeAnswer avec réponse, sources et actions effectuées
        """
        _logger.info("📚 [KB Agent] Question : %s", question[:80])

        # 1. Embedding de la question
        query_embedding = self.llm.embed(question)

        # 2. Recherche RAG dans ChromaDB
        relevant_articles = self.memory.search_articles(
            query_embedding=query_embedding,
            n_results=5,
            state_filter="approved",
        )
        # Filtrer par score minimal
        relevant_articles = [a for a in relevant_articles if a["score"] >= MIN_ARTICLE_SCORE]

        # 3. Construire le contexte RAG
        context = self._build_rag_context(relevant_articles)
        confidence = max((a["score"] for a in relevant_articles), default=0.0)

        # 4. Générer la réponse
        answer_text = self._generate_answer(question, context)

        # 5. Détecter les lacunes si confiance insuffisante
        gap_detected = confidence < RELEVANCE_THRESHOLD
        articles_created = []
        suggested_articles = []

        if gap_detected:
            _logger.info("⚠️ [KB Agent] Lacune détectée (score=%.2f) → analyse contenu manquant",
                         confidence)
            suggested_articles = self._detect_missing_content(question, relevant_articles)

            if auto_create_missing and suggested_articles:
                articles_created = self._create_missing_articles(
                    question, suggested_articles, relevant_articles
                )

        # 6. Logger dans Odoo
        sources_summary = ", ".join(a["title"] for a in relevant_articles[:3])
        self.odoo.log_agent_run(
            "Knowledge Explorer",
            "success",
            f"Q: {question[:60]}... | Sources: {sources_summary or 'aucune'} | "
            f"Confiance: {confidence:.0%} | Articles créés: {len(articles_created)}",
        )

        return KnowledgeAnswer(
            question=question,
            answer=answer_text,
            sources=[{
                "article_id": a["article_id"],
                "title":      a["title"],
                "score":      round(a["score"], 3),
            } for a in relevant_articles],
            confidence=confidence,
            gap_detected=gap_detected,
            articles_created=articles_created,
            suggested_articles=suggested_articles,
        )

    def reindex_knowledge_base(self) -> int:
        """
        Réindexe tous les articles Knowledge approuvés dans ChromaDB.
        À lancer lors de l'installation ou après un lot de nouveaux articles.
        :return: Nombre d'articles indexés
        """
        _logger.info("🔄 [KB Agent] Réindexation complète de la base Knowledge...")
        articles = self.odoo.get_approved_articles(limit=1000)
        count = 0
        for article in articles:
            try:
                text = f"{article['name']}\n\n{article.get('content', '')}"
                embedding = self.llm.embed(text[:2000])
                category  = article.get("category_id", [None, ""])[1] if article.get("category_id") else ""
                self.memory.upsert_article(
                    article_id=article["id"],
                    title=article["name"],
                    content=text,
                    category=category,
                    state=article.get("state", "approved"),
                    embedding=embedding,
                )
                count += 1
            except Exception as e:
                _logger.warning("⚠️ [KB Agent] Erreur indexation article %s : %s",
                                article["id"], e)
        _logger.info("✅ [KB Agent] %d articles indexés dans ChromaDB", count)
        return count

    # ─── RAG ────────────────────────────────────────────────────────

    def _build_rag_context(self, articles: list[dict]) -> str:
        """Construit le contexte textuel à partir des articles pertinents."""
        if not articles:
            return "Aucun article pertinent trouvé dans la base de connaissances."
        parts = []
        for i, art in enumerate(articles, 1):
            parts.append(
                f"--- Source {i} : [{art['title']}] (pertinence: {art['score']:.0%}) ---\n"
                f"{art['content'][:1000]}\n"
            )
        return "\n".join(parts)

    def _generate_answer(self, question: str, context: str) -> str:
        """Génère la réponse via LLM avec le contexte RAG."""
        user_msg = (
            f"**Question** : {question}\n\n"
            f"**Extraits de la base de connaissances** :\n{context}\n\n"
            f"Génère une réponse claire et structurée basée sur ces extraits."
        )
        return self.llm.chat(self.SYSTEM_RAG, user_msg)

    # ─── Détection de lacunes ────────────────────────────────────────

    def _detect_missing_content(self, question: str,
                                  existing_articles: list[dict]) -> list[str]:
        """
        Identifie les articles manquants via le LLM et retourne leurs titres.
        Utilise aussi `suggest_missing_content` de knowledge_ai_assistant via Odoo.
        """
        existing_titles = [a["title"] for a in existing_articles]

        # Appel LLM local pour détecter les lacunes
        user_msg = (
            f"Question sans réponse dans la KB : '{question}'\n\n"
            f"Articles existants :\n"
            + "\n".join(f"- {t}" for t in existing_titles)
        )
        try:
            import json, re
            raw = self.llm.chat(self.SYSTEM_GAP_DETECTION, user_msg)
            raw = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(raw)
            suggestions = [
                item["title"]
                for item in data.get("missing_articles", [])
            ]
            _logger.info("💡 [KB Agent] %d article(s) manquant(s) identifié(s)", len(suggestions))
            return suggestions
        except Exception as e:
            _logger.warning("⚠️ [KB Agent] Erreur détection lacunes : %s", e)
            return []

    def _create_missing_articles(self, question: str,
                                   suggested_titles: list[str],
                                   context_articles: list[dict]) -> list[int]:
        """
        Crée automatiquement les articles manquants via les templates BA d'Odoo.
        Appelle knowledge.ai.assistant.fill_template via Odoo RPC.
        """
        created_ids = []

        # Trouver la catégorie "Documentation" ou similaire
        cats = self.odoo.search_read(
            "knowledge.category",
            [("name", "ilike", "documentation")],
            ["id", "name"],
            limit=1,
        )
        cat_id = cats[0]["id"] if cats else None

        for title in suggested_titles[:3]:  # Max 3 articles auto-créés par session
            try:
                context_info = (
                    f"Titre de l'article : {title}\n"
                    f"Question déclenchante : {question}\n"
                    f"Articles connexes existants : "
                    + ", ".join(a["title"] for a in context_articles[:3])
                )

                # Générer le contenu via LLM (template générique)
                content = self.llm.chat(
                    "Tu rédiges un article de base de connaissances professionnel en HTML. "
                    "Utilise des balises <h2>, <h3>, <ul>, <p>. "
                    "Contenu structuré, actionnable, en français.",
                    f"Génère un article complet pour : '{title}'\n\nContexte : {context_info}",
                    force_cloud=True,  # Utiliser Claude pour la qualité rédactionnelle
                )

                # Créer dans Odoo
                article_id = self.odoo.create_knowledge_article(
                    title=f"[Auto] {title}",
                    content=content,
                    category_id=cat_id,
                )
                # Réindexer dans ChromaDB
                embedding = self.llm.embed(f"{title}\n{content[:1000]}")
                self.memory.upsert_article(
                    article_id=article_id,
                    title=title,
                    content=content[:2000],
                    category="auto-generated",
                    state="draft",
                    embedding=embedding,
                )
                created_ids.append(article_id)
                _logger.info("📄 [KB Agent] Article auto-créé : id=%s, titre='%s'",
                             article_id, title)
            except Exception as e:
                _logger.error("❌ [KB Agent] Erreur création article '%s' : %s", title, e)

        return created_ids
