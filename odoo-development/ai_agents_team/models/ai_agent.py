from odoo import models, fields, api, registry, _
import requests
import json
import logging
import re
import html
import threading

_logger = logging.getLogger(__name__)

class AiAgent(models.Model):
    _name = 'agh.ai.agent'
    _description = 'Agent IA Autonome'

    name = fields.Char(string='Nom de l\'Agent', required=True)
    agent_type = fields.Selection([
        ('executor', 'Agent d\'Exécution (Actions)'),
        ('analyst', 'Agent Analyste (Data)'),
        ('knowledge', 'Agent Knowledge (RAG)')
    ], string='Type d\'Agent', default='executor')
    
    ollama_host = fields.Char(string='URL Ollama', default='http://host.docker.internal:11434')
    model_name = fields.Char(string='Modèle LLM', default='llama3.2:1b-instruct-q4_K_M')
    
    active = fields.Boolean(default=True)
    system_prompt = fields.Text(string='Prompt Système', default="Tu es un agent expert Odoo. Tu peux exécuter des actions via des outils.")

    def _call_llm(self, messages, tools=None):
        """Appel au LLM avec support du Tool Calling."""
        url = f"{self.ollama_host}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 180,  # Limite les tokens générés pour rester rapide sur CPU et éviter les timeouts
            }
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(url, json=payload, timeout=300)
            resp.raise_for_status()
            return resp.json().get("message", {})
        except Exception as e:
            _logger.error("Erreur Agent LLM : %s", e)
            return {"role": "assistant", "content": f"Erreur de communication : {e}"}

class AiAgentSession(models.Model):
    _name = 'agh.ai.agent.session'
    _description = 'Session de conversation Agent IA'

    agent_id = fields.Many2one('agh.ai.agent', string='Agent', required=True)
    user_id = fields.Many2one('res.users', string='Utilisateur', default=lambda self: self.env.user)
    message_ids = fields.One2many('agh.ai.agent.message', 'session_id', string='Messages')

    def clear_messages(self):
        """Supprime tous les messages de la session actuelle pour vider l'historique."""
        self.ensure_one()
        self.message_ids.unlink()
        return True

    def execute_command(self, user_text):
        """Cycle principal de l'agent (Asynchrone)."""
        self.env['agh.ai.agent.message'].create({
            'session_id': self.id,
            'role': 'user',
            'content': user_text
        })
        # Commit de la transaction actuelle pour que le thread asynchrone voie le message utilisateur
        self.env.cr.commit()

        # Lancer le traitement en arrière-plan
        dbname = self.env.cr.dbname
        user_id = self.env.user.id
        session_id = self.id

        t = threading.Thread(
            target=self._execute_command_async,
            args=(dbname, session_id, user_id, user_text)
        )
        t.daemon = True
        t.start()
        return True

    @api.model
    def _execute_command_async(self, dbname, session_id, user_id, user_text):
        """Méthode exécutée en arrière-plan avec son propre curseur."""
        reg = registry(dbname)
        with reg.cursor() as cr:
            env = api.Environment(cr, user_id, {})
            session = env['agh.ai.agent.session'].browse(session_id)
            if not session.exists():
                _logger.error("Session %s introuvable dans le thread asynchrone", session_id)
                return
            try:
                session._execute_command_sync(user_text)
                cr.commit()
            except Exception as e:
                _logger.error("Erreur dans le traitement asynchrone de l'agent : %s", e, exc_info=True)
                try:
                    env['agh.ai.agent.message'].create({
                        'session_id': session.id,
                        'role': 'assistant',
                        'content': f"Désolé, une erreur est survenue lors du traitement : {e}"
                    })
                    cr.commit()
                except Exception as ex:
                    _logger.error("Impossible d'enregistrer le message d'erreur : %s", ex)

    def _execute_command_sync(self, user_text):
        """Cycle principal de l'agent : Message -> Tool Call -> Response (Synchrone)."""
        # Nettoyage et classification de la requête
        user_clean = user_text.lower().strip()

        # 1. Détecter si c'est une demande d'action (tâche, timesheet)
        is_action_request = any(w in user_clean for w in [
            'créer une tâche', 'creer une tache', 'crée une tâche', 'cree une tache',
            'créer tâche', 'creer tache', 'nouvelle tâche', 'nouvelle tache', 'create task', 'create a task',
            'saisir des heures', 'saisir heures', 'enregistrer des heures', 'enregistrer heures',
            'log timesheet', 'log hours', 'ajouter des heures', 'ajouter heures'
        ])

        # 2. Détecter si c'est une question de connaissances (RAG)
        contains_knowledge_keywords = any(w in user_clean for w in [
            'cahier', 'recette', 'cuisine', 'gumroad', 'convert', 'taux',
            'sprint', 'commit', 'figma', 'api', 'validation', 'responsable', 'statut'
        ]) or '?' in user_clean or any(user_clean.startswith(w) for w in [
            'quel', 'qui', 'comment', 'quelle', 'quels', 'combien', 'où', 'pourquoi', 'est-ce'
        ])

        # 3. Détecter si c'est une salutation
        is_greeting = (any(w in user_clean for w in ['bonjour', 'salut', 'hello', 'bonsoir', 'hi', 'hey', 'yo'])
                       and not contains_knowledge_keywords) or len(user_clean) < 4

        # 4. RAG intelligent pre-fetch pour les questions de connaissances
        articles = self.env['agh.knowledge.article']
        system_content = self.agent_id.system_prompt
        is_knowledge_query = contains_knowledge_keywords and not is_action_request and not is_greeting

        if is_knowledge_query:
            try:
                articles = self.env['agh.knowledge.article'].find_similar_articles(user_text, limit=2)
                if articles:
                    system_content += "\n\nInformations de la base de connaissances à utiliser pour répondre (Cite obligatoirement la source au format 'Source : [Nom de l'article]') :\n"
                    for art in articles:
                        raw_content = art.content or ""
                        clean_content = html.unescape(re.sub(r'<[^>]+>', ' ', raw_content))
                        clean_content = ' '.join(clean_content.split())
                        system_content += f"--- Article: {art.name} ---\n{clean_content[:1500]}\n"
            except Exception as e:
                _logger.error("RAG search failed in execute_command: %s", e)

        # Préparer l'historique pour le LLM (limité aux 3 derniers messages pour rester rapide sur CPU)
        messages = [{"role": "system", "content": system_content}]
        history_msgs = self.message_ids.sorted('create_date')
        if len(history_msgs) > 3:
            history_msgs = history_msgs[-3:]
        for msg in history_msgs:
            messages.append({"role": msg.role, "content": msg.content})

        # Définition des outils (Phase 2 & 3)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge",
                    "description": "Rechercher des informations dans la base de connaissances (articles, documentation).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "La question ou les mots clés à chercher."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_task",
                    "description": "Créer une nouvelle tâche dans un projet Odoo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Titre de la tâche."},
                            "project_name": {"type": "string", "description": "Nom du projet (ex: 'R&D', 'Marketing')."},
                            "description": {"type": "string", "description": "Description détaillée de la tâche."}
                        },
                        "required": ["name", "project_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "log_timesheet",
                    "description": "Saisir des heures de travail sur une tâche ou un projet.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {"type": "string", "description": "Nom du projet."},
                            "hours": {"type": "number", "description": "Nombre d'heures effectuées (ex: 1.5)."},
                            "description": {"type": "string", "description": "Description du travail effectué."}
                        },
                        "required": ["project_name", "hours", "description"]
                    }
                }
            }
        ]

        # On n'active l'outil LLM natif que s'il s'agit explicitement d'une action.
        # Cela réduit considérablement la taille du prompt et évite les erreurs du LLM 1B.
        use_tools = is_action_request and not is_greeting and not is_knowledge_query
        
        response = self.agent_id._call_llm(messages, tools=tools if use_tools else None)
        
        tool_calls = []
        if use_tools:
            if response.get("tool_calls"):
                for tc in response["tool_calls"]:
                    tool_calls.append({
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                        "id": tc.get("id"),
                        "native": True
                    })
            else:
                # Tente de parser un appel d'outil en texte brut (JSON)
                tc_text = self._parse_text_tool_call(response.get("content", ""))
                if tc_text:
                    tool_calls.append(tc_text)

        if tool_calls:
            # On a un ou plusieurs appels d'outils
            for tc in tool_calls:
                function_name = tc["name"]
                args = tc["arguments"]
                
                # Exécution sécurisée de l'outil
                result = self._dispatch_tool(function_name, args)
                
                # Ajouter le résultat au contexte
                if tc.get("native"):
                    messages.append(response)
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tc.get("id")
                    })
                else:
                    # Message de l'assistant simulé et résultat du tool simulé
                    messages.append({
                        "role": "assistant",
                        "content": response.get("content") or json.dumps(tc)
                    })
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": "call_simulated"
                    })
            
            # Deuxième appel pour la réponse finale
            final_response = self.agent_id._call_llm(messages)
            content = final_response.get("content", "")
        else:
            content = response.get("content", "")

        # Garantir l'affichage de la source pour les requêtes RAG
        if is_knowledge_query and articles and content:
            source_names = [art.name for art in articles]
            if "source" not in content.lower():
                content += f"\n\nSource : {', '.join(source_names)}"

        # Nettoyage préventif du HTML dans la réponse finale
        if content:
            content = re.sub(r'</?(p|div)[^>]*>', '\n', content)
            content = re.sub(r'<br\s*/?>', '\n', content)
            content = re.sub(r'</?(strong|b)[^>]*>', '**', content)
            content = re.sub(r'</?(em|i)[^>]*>', '*', content)
            content = re.sub(r'<[^>]+>', '', content)
            content = html.unescape(content)

        # Sauvegarder la réponse finale
        self.env['agh.ai.agent.message'].create({
            'session_id': self.id,
            'role': 'assistant',
            'content': content
        })
        return content

    def _parse_text_tool_call(self, content):
        """Tente de parser un appel d'outil formaté en texte brut par le LLM (fallbacks)."""
        if not content:
            return None
        
        content_clean = content.strip()
        start = content_clean.find('{')
        end = content_clean.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = content_clean[start:end+1]
            try:
                data = json.loads(json_str)
                name = data.get("name") or data.get("function")
                args = data.get("arguments") or data.get("parameters") or data.get("args") or data
                
                if name:
                    return {
                        "name": name,
                        "arguments": args if isinstance(args, dict) else {"query": str(args)},
                        "native": False
                    }
                
                # Recherche implicite si clé "query"
                if isinstance(data, dict) and "query" in data:
                    return {
                        "name": "search_knowledge",
                        "arguments": {"query": data["query"]},
                        "native": False
                    }
            except:
                pass
        return None

    def _dispatch_tool(self, name, args):
        """Exécute la fonction Python associée à l'outil."""
        try:
            # Tolérer les variations de nommage des outils (surtout pour les petits modèles LLM qui hallucinent le nom)
            name_clean = name.lower().strip() if isinstance(name, str) else ""
            if "task" in name_clean or "tâche" in name_clean or "todo" in name_clean:
                name = "create_task"
            elif "timesheet" in name_clean or "heures" in name_clean or "log" in name_clean:
                name = "log_timesheet"
            else:
                # Tout autre appel (comme 'recette', 'cheb3ni', 'allojn' etc.) est redirigé vers search_knowledge
                name = "search_knowledge"

            if name == "search_knowledge":
                query = ""
                if isinstance(args, dict):
                    query = args.get("query") or args.get("parameters", {}).get("query")
                    if not query:
                        for val in args.values():
                            if isinstance(val, str) and len(val) > 2:
                                query = val
                                break
                else:
                    query = str(args)
                
                if not query:
                    query = "Recettes"

                articles = self.env['agh.knowledge.article'].find_similar_articles(query, limit=3)
                if not articles:
                    return "Aucun article trouvé pour cette recherche."
                res = "Articles trouvés :\n"
                for art in articles:
                    raw_content = art.content or ""
                    clean_content = html.unescape(re.sub(r'<[^>]+>', ' ', raw_content))
                    clean_content = ' '.join(clean_content.split())
                    res += f"- {art.name} : {clean_content[:500]}...\n"
                return res

            elif name == "create_task":
                project_name = args.get("project_name") if isinstance(args, dict) else ""
                project = self.env['project.project'].search([('name', 'ilike', project_name)], limit=1)
                if not project:
                    return f"Erreur : Projet '{project_name}' introuvable."
                task = self.env['project.task'].create({
                    'name': args.get("name") if isinstance(args, dict) else "Nouvelle tâche",
                    'project_id': project.id,
                    'description': args.get("description", "") if isinstance(args, dict) else ""
                })
                return f"Succès : Tâche '{task.name}' créée dans le projet '{project.name}' (ID: {task.id})."

            elif name == "log_timesheet":
                project_name = args.get("project_name") if isinstance(args, dict) else ""
                project = self.env['project.project'].search([('name', 'ilike', project_name)], limit=1)
                if not project:
                    return f"Erreur : Projet '{project_name}' introuvable."
                
                hours = args.get("hours") if isinstance(args, dict) else 0
                timesheet = self.env['account.analytic.line'].create({
                    'name': args.get("description") if isinstance(args, dict) else "Saisie IA",
                    'project_id': project.id,
                    'unit_amount': hours,
                    'employee_id': self.env.user.employee_id.id or False
                })
                return f"Succès : {hours}h saisies sur le projet '{project.name}'."

            return f"Outil {name} non implémenté."
        except Exception as e:
            _logger.error("Erreur exécution outil %s : %s", name, e)
            return f"Erreur lors de l'exécution de l'outil : {e}"

class AiAgentMessage(models.Model):
    _name = 'agh.ai.agent.message'
    _description = 'Message de session Agent'
    _order = 'create_date asc'

    session_id = fields.Many2one('agh.ai.agent.session', string='Session', ondelete='cascade')
    role = fields.Selection([('system', 'Système'), ('user', 'Utilisateur'), ('assistant', 'IA'), ('tool', 'Outil')], required=True)
    content = fields.Text(string='Contenu')
    tool_call_id = fields.Char(string='ID Appel Outil')
