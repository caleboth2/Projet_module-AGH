"""
tests/unit/test_triage_agent.py
────────────────────────────────
Tests unitaires du Triage Agent.
Mock GitHub API + LLM + Odoo RPC.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, ANY


# ── Fixtures ──────────────────────────────────────────────────────

SAMPLE_ISSUE = {
    "number": 99,
    "title": "App crashes on Android 14 when opening Settings",
    "body": "Steps: 1. Open app 2. Tap Settings\nExpected: Settings screen\nActual: Crash",
    "labels": [],
}

SAMPLE_TRIAGE_RESPONSE = json.dumps({
    "type": "bug",
    "moscow": "must",
    "priority": "critical",
    "skills_needed": ["android", "kotlin", "crash"],
    "story_points": 3,
    "epic_keywords": ["android", "settings", "crash"],
    "summary_fr": "L'application plante sur Android 14 lors de l'ouverture des Paramètres.",
    "triage_comment": "Bug critique Android 14. Assigné au dev mobile en priorité.",
})


@pytest.fixture
def mock_llm():
    with patch("ai_agents_team.agents.triage_agent.triage_agent.LLMConnector") as MockLLM:
        instance = MockLLM.return_value
        instance.chat.return_value = SAMPLE_TRIAGE_RESPONSE
        instance.embed.return_value = [0.1] * 384
        yield instance


@pytest.fixture
def mock_github():
    with patch("ai_agents_team.agents.triage_agent.triage_agent.GitHubTool") as MockGH:
        instance = MockGH.return_value
        instance.get_issue.return_value = SAMPLE_ISSUE
        instance.add_labels.return_value = True
        instance.set_assignees.return_value = True
        instance.post_comment.return_value = True
        instance.ensure_labels_exist.return_value = None
        yield instance


@pytest.fixture
def mock_odoo():
    with patch("ai_agents_team.agents.triage_agent.triage_agent.OdooRPC") as MockOdoo:
        instance = MockOdoo.return_value
        instance.search_read.return_value = [{"id": 1, "name": "Bugs & Correctifs"}]
        instance.create_knowledge_article.return_value = 42
        instance.get_active_sprints.return_value = [
            {"id": 5, "name": "Sprint 3", "project_id": [1, "App Factory"]}
        ]
        instance.create_bug_task.return_value = 101
        instance.log_agent_run.return_value = 1
        yield instance


@pytest.fixture
def mock_memory():
    with patch("ai_agents_team.agents.triage_agent.triage_agent.ChromaStore") as MockChroma:
        instance = MockChroma.return_value
        instance.upsert_ticket.return_value = None
        yield instance


# ── Tests ──────────────────────────────────────────────────────────

class TestTriageAgentAnalysis:

    def test_analyze_returns_correct_type(self, mock_llm, mock_github, mock_odoo, mock_memory):
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent.triage_issue(99)
        assert result["type"] == "bug"

    def test_analyze_returns_correct_moscow(self, mock_llm, mock_github, mock_odoo, mock_memory):
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent.triage_issue(99)
        assert result["moscow"] == "must"

    def test_assignee_is_android_dev(self, mock_llm, mock_github, mock_odoo, mock_memory):
        """Les skills 'android, kotlin' doivent matcher dev-android."""
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent.triage_issue(99)
        assert result["assignee"] == "dev-android"

    def test_github_labels_applied(self, mock_llm, mock_github, mock_odoo, mock_memory):
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent.triage_issue(99)
        mock_github.add_labels.assert_called_once_with(99, ANY)
        labels = mock_github.add_labels.call_args[0][1]
        assert "triage:bug" in labels
        assert "moscow:must" in labels

    def test_knowledge_article_created(self, mock_llm, mock_github, mock_odoo, mock_memory):
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent.triage_issue(99)
        assert result["article_id"] == 42
        mock_odoo.create_knowledge_article.assert_called_once()

    def test_sprint_linked_for_must(self, mock_llm, mock_github, mock_odoo, mock_memory):
        """Un ticket 'must' doit être lié au sprint actif."""
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent.triage_issue(99)
        assert result["sprint_id"] == 5

    def test_llm_fallback_on_json_error(self, mock_github, mock_odoo, mock_memory):
        """Si le LLM retourne du JSON invalide → triage par défaut."""
        with patch("ai_agents_team.agents.triage_agent.triage_agent.LLMConnector") as MockLLM:
            instance = MockLLM.return_value
            instance.chat.return_value = "Ce n'est pas du JSON valide..."
            instance.embed.return_value = [0.1] * 384
            from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
            agent = TriageAgent()
            result = agent.triage_issue(99)
            # Doit retourner le triage par défaut sans lever d'exception
            assert result["type"] == "question"
            assert result["moscow"] == "could"

    def test_find_best_assignee_no_match(self, mock_llm, mock_github, mock_odoo, mock_memory):
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent._find_best_assignee(["ruby", "rails", "elixir"])
        assert result is None

    def test_comment_posted_to_github(self, mock_llm, mock_github, mock_odoo, mock_memory):
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        agent.triage_issue(99)
        mock_github.post_comment.assert_called_once_with(99, ANY)
        comment = mock_github.post_comment.call_args[0][1]
        assert "Triage Automatique" in comment
        assert "must" in comment.lower() or "Must" in comment


class TestTriageAgentEdgeCases:

    def test_empty_body_issue(self, mock_llm, mock_github, mock_odoo, mock_memory):
        """Issue sans description ne doit pas planter."""
        mock_github.get_issue.return_value = {
            "number": 100,
            "title": "Simple title",
            "body": None,
            "labels": [],
        }
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent.triage_issue(100)
        assert "type" in result

    def test_no_active_sprint_for_must(self, mock_llm, mock_github, mock_odoo, mock_memory):
        """Si pas de sprint actif, sprint_id doit être None (pas d'erreur)."""
        mock_odoo.get_active_sprints.return_value = []
        from ai_agents_team.agents.triage_agent.triage_agent import TriageAgent
        agent = TriageAgent()
        result = agent.triage_issue(99)
        assert result["sprint_id"] is None
