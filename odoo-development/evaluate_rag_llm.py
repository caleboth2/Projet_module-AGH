# -*- coding: utf-8 -*-
import json
import time
import sys

def run_evaluation(env):
    print("--- STARTING RAG & LLM EVALUATION ---")
    
    # 1. Get or create agent
    agent = env['agh.ai.agent'].search([], limit=1)
    if not agent:
        print("Creating default test agent...")
        agent = env['agh.ai.agent'].create({
            'name': 'Assistant Evaluation',
            'agent_type': 'executor',
            'model_name': 'llama3.2:1b',
            'ollama_host': 'http://host.docker.internal:11434'
        })
    else:
        print(f"Using existing agent: {agent.name} (Model: {agent.model_name}, Host: {agent.ollama_host})")

    # List of queries to evaluate (from latex_evaluation_rag.txt)
    queries = [
        # Table 1
        {"id": 1, "table": 1, "query": "Quel est le dernier commit sur le projet App Cuisine ?"},
        {"id": 2, "table": 1, "query": "Qui est le responsable du livrable maquette Figma v3 ?"},
        {"id": 3, "table": 1, "query": "Quelle est la procédure de validation d'un livrable ?"},
        {"id": 4, "table": 1, "query": "Quelles APIs sont utilisées dans le module marketing ?"},
        {"id": 5, "table": 1, "query": "Quel est le statut actuel de l'App Fitness ?"},
        {"id": 6, "table": 1, "query": "Comment configurer le webhook GitHub dans Odoo ?"},
        {"id": 7, "table": 1, "query": "Quels sont les tokens/s de Llama sur notre serveur ?"},
        {"id": 8, "table": 1, "query": "Qui a approuvé le cahier des charges App Nutrition ?"},
        {"id": 9, "table": 1, "query": "Quelle version de Flutter est utilisée en production ?"},
        {"id": 10, "table": 1, "query": "Comment exporter les données Gumroad vers Excel ?"},
        {"id": 11, "table": 1, "query": "Quels livrables sont en attente de révision ?"},
        {"id": 12, "table": 1, "query": "Quelle est la politique de nommage des commits ?"},
        {"id": 13, "table": 1, "query": "Qui contacter en cas de panne du serveur Ollama ?"},
        {"id": 14, "table": 1, "query": "Quelle est la durée moyenne d'onboarding après déploiement ?"},
        {"id": 15, "table": 1, "query": "Comment créer un nouvel article dans la base de connaissances ?"},
        # Table 2
        {"id": 1, "table": 2, "query": "Quel est le dernier commit sur le projet App Cuisine v2 ?"},
        {"id": 2, "table": 2, "query": "Qui est responsable du livrable maquette Figma version 3 ?"},
        {"id": 3, "table": 2, "query": "Quelle est la procédure de validation d'un livrable code ?"},
        {"id": 4, "table": 2, "query": "Quelles APIs sont utilisées pour synchroniser Gumroad ?"},
        {"id": 5, "table": 2, "query": "Comment indexer un nouveau document dans la base de connaissances ?"},
        {"id": 6, "table": 2, "query": "Quel est le statut actuel du livrable App Fitness backend ?"},
        {"id": 7, "table": 2, "query": "Quels commits GitHub sont liés à l'App Perte de poids ?"},
        {"id": 8, "table": 2, "query": "Quelle version de Flutter est utilisée dans l'App Cuisine ?"},
        {"id": 9, "table": 2, "query": "Quels KPIs marketing sont suivis pour l'App Fitness ?"},
        {"id": 10, "table": 2, "query": "Comment configurer le webhook GitHub dans Odoo ?"},
        {"id": 11, "table": 2, "query": "Quelle est la durée moyenne d'un sprint dans ce projet ?"},
        {"id": 12, "table": 2, "query": "Qui a approuvé la maquette Figma du module onboarding ?"},
        {"id": 13, "table": 2, "query": "Quels tests ont été effectués sur le connecteur Figma ?"},
        {"id": 14, "table": 2, "query": "Quel est le taux de conversion Gumroad du mois d'avril ?"},
        {"id": 15, "table": 2, "query": "Comment relancer Ollama en cas de timeout ?"}
    ]
    import os
    results = []
    if os.path.exists("/tmp/evaluation_results.json"):
        try:
            with open("/tmp/evaluation_results.json", "r", encoding="utf-8") as f:
                results = json.load(f)
            print(f"Loaded {len(results)} existing results from cache.")
        except Exception as e:
            print(f"Failed to load cache: {e}")
            results = []

    def is_processed(table, q_id):
        return any(r["table"] == table and r["id"] == q_id for r in results)
    
    for idx, q_info in enumerate(queries):
        q_id = q_info["id"]
        table = q_info["table"]
        query = q_info["query"]
        
        if is_processed(table, q_id):
            print(f"[{idx+1}/{len(queries)}] Table {table} Q{q_id} already processed. Skipping.")
            continue
            
        print(f"[{idx+1}/{len(queries)}] Table {table} Q{q_id}: {query}")
        
        start_time = time.time()
        error_msg = None
        response_text = ""
        
        try:
            with env.cr.savepoint():
                session = env['agh.ai.agent.session'].create({
                    'agent_id': agent.id,
                    'user_id': env.user.id
                })
                response_text = session.execute_command(query)
        except Exception as e:
            error_msg = str(e)
            print(f"   -> ❌ Error: {e}")
            
        elapsed = time.time() - start_time
        print(f"   -> Completed in {elapsed:.2f}s")
        
        results.append({
            "id": q_id,
            "table": table,
            "query": query,
            "response": response_text,
            "time": elapsed,
            "error": error_msg
        })
        
        # Periodic saving
        with open("/tmp/evaluation_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

    print("--- EVALUATION COMPLETE ---")

run_evaluation(env)
env.cr.commit()
