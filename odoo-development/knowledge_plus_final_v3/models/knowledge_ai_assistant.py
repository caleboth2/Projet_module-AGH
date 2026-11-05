from odoo import models, fields, api, _
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class KnowledgeAiAssistant(models.Model):
    _name = 'agh.knowledge.ai.assistant'
    _description = 'Assistant IA Local (Ollama) - Knowledge'

    name = fields.Char(string='Nom du profil IA', required=True, default='Assistant IA Local')
    
    # ── Paramètres Ollama ───────────────────────────────────────────
    ollama_host = fields.Char(
        string='URL Serveur Ollama', 
        default='http://host.docker.internal:11434',
        help="L'URL de votre instance Ollama (ex: http://host.docker.internal:11434)"
    )
    model_name = fields.Selection([
        ('llama3.2:1b', 'Llama 3.2 1B (Ultra Léger - Recommandé)'),
        ('llama3', 'Llama 3 (Standard)'),
        ('mistral', 'Mistral 7B (Rapide)'),
        ('phi3', 'Phi-3 (Léger)'),
    ], string='Modèle LLM Local', default='llama3.2:1b', required=True)
    
    max_tokens = fields.Integer(string='Tokens max', default=2048)
    temperature = fields.Float(string='Température', default=0.7)
    active = fields.Boolean(default=True)

    def _get_active_assistant(self):
        assistant = self.search([('active', '=', True)], limit=1)
        if not assistant:
            raise models.ValidationError("Aucun assistant LLM local configuré.")
        return assistant

    def _call_ollama(self, system_prompt: str, user_message: str) -> str:
        """Appel à l'API Ollama locale."""
        url = f"{self.ollama_host}/api/generate"
        
        full_prompt = f"System: {system_prompt}\n\nUser: {user_message}"
        
        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens,
                "temperature": self.temperature,
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "Erreur: Pas de réponse du LLM.")
        except Exception as e:
            _logger.error("Erreur Ollama : %s", e)
            raise models.ValidationError(f"Impossible de joindre le LLM Local ({self.ollama_host}). Vérifiez qu'Ollama est lancé. Erreur: {e}")

    def _get_embeddings(self, text: str):
        """Génère un vecteur d'embedding pour un texte donné."""
        url = f"{self.ollama_host}/api/embeddings"
        payload = {
            "model": "nomic-embed-text",
            "prompt": text
        }
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json().get("embedding", [])
        except Exception as e:
            _logger.error("Erreur Embeddings Ollama : %s", e)
            return []

    # ── Fonctionnalités IA ──────────────────────────────────────────

    def generate_summary(self, article_content: str, article_name: str) -> str:
        system = "Tu es un assistant expert. Rédige un résumé structuré en français (3-5 points clés)."
        user = f"Titre : {article_name}\nContenu : {article_content[:5000]}"
        return self._call_ollama(system, user)

    def generate_meeting_notes(self, raw_notes: str, project_name: str = '') -> str:
        system = "Tu es un assistant spécialisé en compte-rendu de réunion professionnel."
        user = f"Notes brutes : {raw_notes[:4000]}"
        return self._call_ollama(system, user)

    def fill_template(self, template_type: str, context_info: str) -> str:
        system = "Tu es un consultant expert. Génère un contenu HTML structuré pour ce document."
        user = f"Type : {template_type}\nContexte : {context_info}"
        return self._call_ollama(system, user)
