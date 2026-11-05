/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class LLMChatWidget extends Component {
    static template = "local_llm_odoo.LLMChatWidget";

    setup() {
        this.notification = useService("notification");

        this.state = useState({
            conversations: [],
            currentConversation: null,
            messages: [],
            inputMessage: "",
            isLoading: false,
            isSidebarOpen: true,
        });

        this.messagesEndRef = useRef("messagesEnd");

        onMounted(() => {
            this.loadConversations();
        });

        this.pollTimeout = null;
        onWillUnmount(() => {
            if (this.pollTimeout) {
                clearTimeout(this.pollTimeout);
            }
        });
    }

    async loadConversations() {
        try {
            const result = await rpc("/llm/conversations", {});
            if (result.error) {
                console.error("Error loading conversations:", result.error);
                this.notification.add(result.error, { type: "danger" });
            } else {
                this.state.conversations = result.conversations || [];
            }
        } catch (error) {
            console.error("Failed to load conversations:", error);
            this.notification.add("Failed to load conversations. Please refresh the page.", { type: "danger" });
        }
    }

    async loadMessages(conversationId) {
        try {
            const result = await rpc(`/llm/conversation/${conversationId}/messages`, {});
            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
            } else {
                this.state.messages = result.messages;
                this.scrollToBottom();
            }
        } catch (error) {
            this.notification.add("Failed to load messages", { type: "danger" });
        }
    }

    async selectConversation(conversation) {
        this.state.currentConversation = conversation;
        await this.loadMessages(conversation.id);
    }

    async sendMessage() {
        const message = this.state.inputMessage.trim();
        if (!message) return;

        // Add user message to UI immediately
        this.state.messages.push({
            role: "user",
            content: message,
            create_date: new Date().toISOString(),
        });

        this.state.inputMessage = "";
        this.state.isLoading = true;
        this.scrollToBottom();

        if (this.pollTimeout) {
            clearTimeout(this.pollTimeout);
        }

        try {
            const result = await rpc("/llm/chat", {
                conversation_id: this.state.currentConversation?.id || false,
                message: message,
            });

            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
                // Remove the optimistically added message
                this.state.messages.pop();
                this.state.isLoading = false;
                this.scrollToBottom();
            } else {
                // Update current conversation ID if it was a new conversation
                let isNew = !this.state.currentConversation;
                if (isNew) {
                    this.state.currentConversation = { id: result.conversation_id };
                    await this.loadConversations();
                }

                // Démarrer le polling
                let attempts = 0;
                const maxAttempts = 150; // 300 seconds max

                const poll = async () => {
                    if (!this.state.isLoading) return;
                    attempts++;
                    if (attempts > maxAttempts) {
                        this.state.isLoading = false;
                        this.notification.add("Délai d'attente dépassé pour la réponse de l'assistant.", { type: "danger" });
                        this.scrollToBottom();
                        return;
                    }
                    try {
                        await this.loadMessages(this.state.currentConversation.id);
                        const lastMsg = this.state.messages[this.state.messages.length - 1];
                        if (lastMsg && lastMsg.role === "assistant") {
                            this.state.isLoading = false;
                            this.scrollToBottom();
                            if (isNew) {
                                // Rafraîchir les conversations pour afficher le nouveau titre
                                await this.loadConversations();
                            }
                            return;
                        }
                    } catch (e) {
                        console.error("Error polling messages", e);
                    }
                    if (this.state.isLoading) {
                        this.pollTimeout = setTimeout(poll, 2000);
                    }
                };
                this.pollTimeout = setTimeout(poll, 2000);
            }
        } catch (error) {
            this.notification.add("Failed to send message", { type: "danger" });
            this.state.messages.pop();
            this.state.isLoading = false;
            this.scrollToBottom();
        }
    }

    newConversation() {
        this.state.currentConversation = null;
        this.state.messages = [];
    }

    toggleSidebar() {
        this.state.isSidebarOpen = !this.state.isSidebarOpen;
    }

    scrollToBottom() {
        setTimeout(() => {
            if (this.messagesEndRef.el) {
                this.messagesEndRef.el.scrollIntoView({ behavior: "smooth" });
            }
        }, 100);
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleString();
    }
}

// Register as a client action
registry.category("actions").add("llm_chat_widget", LLMChatWidget);
