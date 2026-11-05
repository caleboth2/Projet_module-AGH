{
    'name': 'AI Agents Team – QA / Triage / Knowledge Explorer',
    'version': '18.0.1.0.0',
    'category': 'Technical/AI',
    'summary': 'Équipe d\'agents IA autonomes : QA Exploratoire Android, Triage GitHub, Knowledge Onboarding',
    'description': """
        ══════════════════════════════════════════════════════
        BRANCHE : feature/ai-agents-team
        BASE    : knowledge_plus_agile_integration (v18.0.6.0.0)
        ISSUE   : #45 Déploiement Equipe d'Agents IA Autonomes
        ══════════════════════════════════════════════════════

        *** QA EXPLORER AGENT ***
        - Monkey testing intelligent sur builds Android (ADB)
        - Génération automatique de rapports de bugs
        - Création de tickets GitHub Issues depuis Odoo
        - Liaison bugs ↔ sprints Agile actifs (agile.sprint)
        - Couverture de test calculée par sprint

        *** TRIAGE AGENT ***
        - Écoute webhook GitHub Issues (nouvelle issue)
        - Qualification automatique : bug / feature / question
        - Priorité MoSCoW calculée par LLM local
        - Assignation automatique au développeur compétent
        - Création/mise à jour article Knowledge associé
        - Ajout au sprint actif de l'Epic concerné

        *** KNOWLEDGE EXPLORER AGENT ***
        - Interface Q&A conversationnelle sur la KB Odoo
        - RAG (Retrieval Augmented Generation) sur knowledge.article
        - Détection lacunes documentaires → suggest_missing_content
        - Génération articles onboarding via templates BA existants
        - Scoring pertinence réponses (grounded answers)

        *** CORE LAYER ***
        - Connecteur LLM Local (Ollama/vLLM sur GPU dédié)
        - Connecteur Claude Anthropic (fallback cloud)
        - ChromaDB — index vectoriel des articles Knowledge
        - GitHub MCP Tool (issues, labels, assignees)
        - Android ADB Tool (APK deploy, ui-automator)
        - Odoo RPC Tool (lecture/écriture tous modèles)

        *** MONITORING ODOO ***
        - Tableau de bord agents (statut, dernière exécution, KPIs)
        - Historique des actions de chaque agent
        - Alertes Odoo si agent en erreur (mail + chatter)
        - Métriques : bugs trouvés, tickets triés, questions résolues

        *** ARCHITECTURE MICRO-SERVICES ***
        - Chaque agent = processus Python indépendant
        - Communication inter-agents via Redis Pub/Sub
        - Supervision systemd / Supervisor
        - GPU isolé par agent (CUDA_VISIBLE_DEVICES)
    """,
    'author': 'AGH Data Agency Holding — App Factory Team',
    'website': 'https://github.com/AGH-Data-Agency-Holding/odoo-development',
    'depends': [
        'mail',
        'project',
        'knowledge_plus_final_v3',
    ],
    'external_dependencies': {
        'python': [
            'requests',
        ]
    },
    'assets': {
        'web.assets_backend': [
            'ai_agents_team/static/src/css/ai_agent_chat.css',
            'ai_agents_team/static/src/js/ai_agent_chat_v2.js',
            'ai_agents_team/static/src/xml/ai_agent_chat.xml',
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/agent_config_data.xml',
        'views/ai_agent_chat_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'icon': '/ai_agents_team/static/description/icon.png',
}
