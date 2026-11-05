"""
tests/integration/test_knowledge_rag.py
────────────────────────────────────────
Tests d'intégration du pipeline RAG du Knowledge Explorer Agent.
Teste le flux complet : question → embedding → ChromaDB → LLM → réponse.
"""
import pytest
from unittest.mock import MagicMock, patch


MOCK_ARTICLES = [
    {
        "article_id": 10,
        "title": "Guide Onboarding Développeur",
        "content": "Ce guide explique les étapes d'onboarding pour les nouveaux développeurs. "
                   "Cloner le dépôt, installer Odoo 18, configurer l'environnement Python.",
        "score": 0.91,
    },
    {
        "article_id": 11,
        "title": "Architecture Technique — App Factory",
        "content": "L'architecture utilise Odoo 18 comme backend, React Native pour mobile, "
                   "et des agents IA LangGraph pour l'automatisation.",
        "score": 0.78,
    },
]

MOCK_EMBEDDING = [0.05] * 384


@pytest.fixture
def mock_rag_pipeline():
    """Configure tous les mocks pour le pipeline RAG."""
    with patch("ai_agents_team.agents.knowledge_explorer.knowledge_agent.LLMConnector") as MockLLM, \
         patch("ai_agents_team.agents.knowledge_explorer.knowledge_agent.ChromaStore") as MockChroma, \
         patch("ai_agents_team.agents.knowledge_explorer.knowledge_agent.OdooRPC") as MockOdoo:

        llm = MockLLM.return_value
        llm.embed.return_value = MOCK_EMBEDDING
        llm.chat.return_value = (
            "Pour configurer votre environnement, référez-vous au "
            "[Guide Onboarding Développeur] qui explique les étapes clés."
        )

        chroma = MockChroma.return_value
        chroma.search_articles.return_value = MOCK_ARTICLES

        odoo = MockOdoo.return_value
        odoo.log_agent_run.return_value = 1
        odoo.search_read.return_value = [{"id": 3, "name": "Documentation"}]
        odoo.create_knowledge_article.return_value = 55

        yield {"llm": llm, "chroma": chroma, "odoo": odoo}


class TestKnowledgeExplorerRAG:

    def test_ask_returns_answer(self, mock_rag_pipeline):
        from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent
        agent = KnowledgeExplorerAgent()
        result = agent.ask("Comment configurer mon environnement de développement ?")
        assert result.answer != ""
        assert "Guide Onboarding" in result.answer

    def test_sources_populated(self, mock_rag_pipeline):
        from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent
        agent = KnowledgeExplorerAgent()
        result = agent.ask("Comment configurer mon environnement de développement ?")
        assert len(result.sources) == 2
        assert result.sources[0]["article_id"] == 10
        assert result.sources[0]["score"] == 0.91

    def test_confidence_reflects_top_score(self, mock_rag_pipeline):
        from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent
        agent = KnowledgeExplorerAgent()
        result = agent.ask("Comment configurer mon environnement ?")
        assert result.confidence == pytest.approx(0.91)

    def test_no_gap_when_high_confidence(self, mock_rag_pipeline):
        from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent
        agent = KnowledgeExplorerAgent()
        result = agent.ask("Comment configurer mon environnement ?")
        # score 0.91 > seuil 0.65 → pas de gap
        assert not result.gap_detected

    def test_gap_detected_when_low_confidence(self, mock_rag_pipeline):
        """Quand ChromaDB retourne des articles peu pertinents → gap détecté."""
        mock_rag_pipeline["chroma"].search_articles.return_value = [
            {"article_id": 99, "title": "Titre non lié", "content": "Contenu vague", "score": 0.40}
        ]
        mock_rag_pipeline["llm"].chat.side_effect = [
            "Je n'ai pas trouvé de réponse précise dans la KB.",  # Réponse RAG
            '{"missing_articles": [{"title": "Guide Setup CI/CD", "template_type": "general"}]}',  # Gap detection
            "<h2>Guide CI/CD</h2><p>Contenu généré...</p>",  # Génération article
        ]
        from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent
        agent = KnowledgeExplorerAgent()
        result = agent.ask("Comment configurer le pipeline CI/CD ?", auto_create_missing=False)
        assert result.gap_detected

    def test_auto_create_missing_articles(self, mock_rag_pipeline):
        """Quand gap détecté + auto_create=True → articles créés dans Odoo."""
        mock_rag_pipeline["chroma"].search_articles.return_value = [
            {"article_id": 99, "title": "Pas pertinent", "content": "...", "score": 0.30}
        ]
        mock_rag_pipeline["llm"].chat.side_effect = [
            "Réponse incomplète.",
            '{"missing_articles": [{"title": "Guide Docker Local", "template_type": "general"}]}',
            "<h2>Guide Docker Local</h2><p>Installez Docker...</p>",
        ]
        mock_rag_pipeline["chroma"].upsert_article = MagicMock()
        from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent
        agent = KnowledgeExplorerAgent()
        result = agent.ask("Comment lancer Odoo en Docker ?", auto_create_missing=True)
        assert result.gap_detected
        assert len(result.articles_created) > 0
        mock_rag_pipeline["odoo"].create_knowledge_article.assert_called()

    def test_embedding_called_for_query(self, mock_rag_pipeline):
        from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent
        agent = KnowledgeExplorerAgent()
        agent.ask("Question test")
        mock_rag_pipeline["llm"].embed.assert_called_once()

    def test_articles_below_threshold_filtered(self, mock_rag_pipeline):
        """Articles avec score < MIN_ARTICLE_SCORE (0.50) doivent être filtrés."""
        mock_rag_pipeline["chroma"].search_articles.return_value = [
            {"article_id": 1, "title": "Bon article",     "content": "...", "score": 0.80},
            {"article_id": 2, "title": "Article faible",  "content": "...", "score": 0.30},
            {"article_id": 3, "title": "Article moyen",   "content": "...", "score": 0.60},
        ]
        from ai_agents_team.agents.knowledge_explorer.knowledge_agent import KnowledgeExplorerAgent
        agent = KnowledgeExplorerAgent()
        result = agent.ask("Question ?")
        # Seuls les articles >= 0.50 doivent apparaître
        assert len(result.sources) == 2
        assert all(s["score"] >= 0.50 for s in result.sources)
