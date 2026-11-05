/** @odoo-module **/

import { Component, useState, onRendered, onWillUnmount, useRef, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export class AiAgentChat extends Component {
    static template = "ai_agents_team.AiAgentChat";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.user = user;
        this.state = useState({
            messages: [],
            userInput: "",
            isTyping: false,
            session_id: null,
        });
        this.chatBodyRef = useRef("chatBody");
        this.suggestions = [
            "Quelles technologies sont utilisées pour l'application Recettes de Cuisine ?",
            "Donne-moi un résumé du projet Cheb3ni",
            "Qui contacter en cas de panne du serveur ?",
            "Qu'est-ce que l'application ALLO JN ?"
        ];

        // Initialiser la session
        this._initSession();

        this.pollTimeout = null;
        onWillUnmount(() => {
            if (this.pollTimeout) {
                clearTimeout(this.pollTimeout);
            }
        });
    }

    async _initSession() {
        // Chercher ou créer une session pour l'utilisateur actuel
        const sessions = await this.orm.searchRead("agh.ai.agent.session", [["user_id", "=", this.user.userId]], ["id"], { limit: 1 });
        if (sessions.length > 0) {
            this.state.session_id = sessions[0].id;
            this._loadMessages();
        } else {
            // Créer un agent par défaut s'il n'existe pas
            const agents = await this.orm.searchRead("agh.ai.agent", [], ["id"], { limit: 1 });
            if (agents.length > 0) {
                const newSession = await this.orm.create("agh.ai.agent.session", [{
                    agent_id: agents[0].id,
                }]);
                this.state.session_id = newSession[0];
            }
        }
    }

    async _loadMessages() {
        if (!this.state.session_id) return;
        const messages = await this.orm.searchRead("agh.ai.agent.message", [["session_id", "=", this.state.session_id]], ["role", "content"], { order: "create_date asc" });
        this.state.messages = messages;
        this._scrollToBottom();
    }

    async selectSuggestion(promptText) {
        this.state.userInput = promptText;
        await this.sendMessage();
    }

    async sendMessage() {
        if (!this.state.userInput.trim() || this.state.isTyping) return;

        const text = this.state.userInput;
        this.state.userInput = "";
        this.state.isTyping = true;

        // Clear any active timeout
        if (this.pollTimeout) {
            clearTimeout(this.pollTimeout);
        }

        // Ajouter le message utilisateur localement
        this.state.messages.push({ role: "user", content: text });
        this._scrollToBottom();

        try {
            await this.orm.call("agh.ai.agent.session", "execute_command", [this.state.session_id, text]);
            
            let attempts = 0;
            const maxAttempts = 150; // 300 seconds max

            const poll = async () => {
                if (!this.state.isTyping) return;
                attempts++;
                if (attempts > maxAttempts) {
                    this.state.isTyping = false;
                    this.notification.add("Délai d'attente dépassé pour la réponse de l'agent.", { type: "danger" });
                    this._scrollToBottom();
                    return;
                }
                try {
                    await this._loadMessages();
                    const lastMsg = this.state.messages[this.state.messages.length - 1];
                    if (lastMsg && lastMsg.role === "assistant") {
                        this.state.isTyping = false;
                        this._scrollToBottom();
                        return;
                    }
                } catch (e) {
                    console.error("Error polling messages", e);
                }
                if (this.state.isTyping) {
                    this.pollTimeout = setTimeout(poll, 2000);
                }
            };
            this.pollTimeout = setTimeout(poll, 2000);

        } catch (error) {
            this.notification.add("Erreur de l'agent IA", { type: "danger" });
            this.state.isTyping = false;
            this._scrollToBottom();
        }
    }

    async clearChat() {
        if (!this.state.session_id) return;
        this.state.isTyping = true;
        try {
            await this.orm.call("agh.ai.agent.session", "clear_messages", [this.state.session_id]);
            this.state.messages = [];
            this.notification.add("La conversation a été réinitialisée.", { type: "success" });
        } catch (error) {
            this.notification.add("Erreur lors de la réinitialisation.", { type: "danger" });
        } finally {
            this.state.isTyping = false;
            this._scrollToBottom();
        }
    }

    _scrollToBottom() {
        setTimeout(() => {
            if (this.chatBodyRef.el) {
                this.chatBodyRef.el.scrollTop = this.chatBodyRef.el.scrollHeight;
            }
        }, 100);
    }

    onKeyPress(ev) {
        if (ev.key === "Enter") {
            this.sendMessage();
        }
    }

    formatMessage(content) {
        if (content === null || content === undefined || content === false || content === "") {
            return "";
        }
        if (typeof content !== 'string') {
            content = String(content);
        }
        
        // 1. Échapper le HTML pour des raisons de sécurité (XSS)
        let escaped = content
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
        
        // 2. Traitement ligne par ligne pour les structures de type bloc (listes, titres)
        let lines = escaped.split("\n");
        let inList = false;
        let result = [];
        
        for (let line of lines) {
            let isHeader = false;
            if (line.startsWith("### ")) {
                line = `<h5 class="mt-2 mb-1 fw-bold">${line.substring(4)}</h5>`;
                isHeader = true;
            } else if (line.startsWith("## ")) {
                line = `<h4 class="mt-2 mb-1 fw-bold">${line.substring(3)}</h4>`;
                isHeader = true;
            } else if (line.startsWith("# ")) {
                line = `<h3 class="mt-2 mb-1 fw-bold">${line.substring(2)}</h3>`;
                isHeader = true;
            }
            
            let isListItem = false;
            if (line.startsWith("- ") || line.startsWith("* ")) {
                line = `<li>${line.substring(2)}</li>`;
                isListItem = true;
            }
            
            if (isListItem) {
                if (!inList) {
                    result.push("<ul class='my-1'>");
                    inList = true;
                }
                result.push(line);
            } else {
                if (inList) {
                    result.push("</ul>");
                    inList = false;
                }
                if (!isHeader && line.trim()) {
                    result.push(`<p class="mb-1">${line}</p>`);
                } else {
                    result.push(line);
                }
            }
        }
        if (inList) {
            result.push("</ul>");
        }
        
        let html = result.join("\n");
        
        // Bloc de code
        html = html.replace(/```([\s\S]*?)```/g, "<pre class='bg-dark text-light p-2 rounded-3 border-0 my-2 font-monospace fs-6' style='white-space: pre-wrap;'><code>$1</code></pre>");
        
        // Code en ligne
        html = html.replace(/`([^`]+)`/g, "<code class='bg-light text-danger px-2 py-0.5 rounded-2 font-monospace fs-6'>$1</code>");
        
        // Gras
        html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        
        // Italique
        html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
        
        return markup(html);
    }
}

registry.category("actions").add("ai_agent_chat_action", AiAgentChat);
