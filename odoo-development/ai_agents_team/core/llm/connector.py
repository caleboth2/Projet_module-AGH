"""
core/llm/connector.py
─────────────────────
Connecteur LLM unifié pour les agents IA.
Stratégie : Local LLM (Ollama/vLLM) en priorité → Claude Anthropic en fallback.
"""
import os
import logging
import requests
from typing import Optional
from dataclasses import dataclass, field

_logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration du connecteur LLM, chargée depuis les variables d'environnement."""
    # Local LLM (Ollama / vLLM sur GPU dédié)
    local_llm_url: str = field(default_factory=lambda: os.getenv("LOCAL_LLM_URL", "http://localhost:11434"))
    local_model: str = field(default_factory=lambda: os.getenv("LOCAL_LLM_MODEL", "mistral:7b-instruct"))

    # Anthropic Claude (fallback cloud)
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    claude_model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"))

    # Paramètres communs
    max_tokens: int = 2000
    temperature: float = 0.2          # Faible pour des réponses déterministes
    timeout: int = 120
    use_local_first: bool = True       # Priorité local, fallback cloud


class LLMConnector:
    """
    Connecteur LLM unifié.
    Essaie d'abord le LLM local (Ollama), puis Claude si local KO.

    Usage :
        llm = LLMConnector()
        response = llm.chat(system="Tu es un expert QA", user="Génère un rapport de bug.")
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()

    # ─── Interface publique ─────────────────────────────────────────

    def chat(self, system: str, user: str, *, force_cloud: bool = False) -> str:
        """
        Génère une réponse LLM.
        :param system: Prompt système (rôle de l'agent)
        :param user:   Message utilisateur / tâche
        :param force_cloud: Forcer Claude même si local disponible
        :return: Texte généré
        """
        if self.config.use_local_first and not force_cloud:
            try:
                return self._call_local(system, user)
            except Exception as e:
                _logger.warning("⚡ LLM local indisponible (%s) — fallback Claude", e)

        return self._call_claude(system, user)

    def embed(self, text: str) -> list[float]:
        """
        Génère un embedding vectoriel via Ollama (nomic-embed-text).
        Utilisé par ChromaDB pour le RAG.
        """
        try:
            resp = requests.post(
                f"{self.config.local_llm_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["embedding"]
        except Exception as e:
            _logger.error("Erreur embedding Ollama : %s", e)
            raise

    # ─── Implémentations privées ────────────────────────────────────

    def _call_local(self, system: str, user: str) -> str:
        """Appel Ollama /api/chat (OpenAI-compatible)."""
        payload = {
            "model": self.config.local_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        resp = requests.post(
            f"{self.config.local_llm_url}/api/chat",
            json=payload,
            timeout=self.config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()

    def _call_claude(self, system: str, user: str) -> str:
        """Appel Anthropic /v1/messages (identique au connector knowledge_ai_assistant.py)."""
        if not self.config.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY non configurée et LLM local indisponible.")

        payload = {
            "model": self.config.claude_model,
            "max_tokens": self.config.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.config.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=self.config.timeout,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()
