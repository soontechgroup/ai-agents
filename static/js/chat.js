// AI Chatbot Demo JavaScript

class ChatBot {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        
        this.initializeEventListeners();
        this.updateStats();
        
        console.log('AI Chatbot Demo initialized');
    }
    
    initializeEventListeners() {
        // Send message on button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter key
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Character counter
        this.messageInput.addEventListener('input', () => {
            const charCount = this.messageInput.value.length;
            document.getElementById('charCount').textContent = `${charCount}/500`;
            
            if (charCount > 450) {
                document.getElementById('charCount').style.color = '#e53e3e';
            } else {
                document.getElementById('charCount').style.color = '#a0aec0';
            }
        });
        
        // Control buttons
        document.getElementById('clearMemory').addEventListener('click', () => this.clearMemory());
        document.getElementById('runDemo').addEventListener('click', () => this.runDemo());
        document.getElementById('showStats').addEventListener('click', () => this.showStats());
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // Disable input while processing
        this.setInputDisabled(true);
        this.showLoading(true);
        
        // Add user message to chat
        this.addMessage('user', message);
        this.messageInput.value = '';
        document.getElementById('charCount').textContent = '0/500';
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            
            if (data.error) {
                this.addMessage('assistant', `Error: ${data.error}`, {
                    sources: ['Error'],
                    processing_time: 0
                });
            } else {
                // Add assistant response
                this.addMessage('assistant', data.response, {
                    sources: data.sources,
                    memory_used: data.memory_used,
                    web_results: data.web_results,
                    facts_retrieved: data.facts_retrieved,
                    processing_time: data.processing_time,
                    metadata: data.metadata
                });
                
                // Update stats
                this.updateStats();
                this.updateStatus(`Processed in ${data.processing_time}s`);
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.addMessage('assistant', 'Sorry, I encountered a network error. Please try again.', {
                sources: ['Error'],
                processing_time: 0
            });
        } finally {
            this.setInputDisabled(false);
            this.showLoading(false);
        }
    }
    
    addMessage(type, content, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Process content for better display
        const processedContent = this.processMessageContent(content);
        messageContent.innerHTML = processedContent;
        
        const messageMeta = document.createElement('div');
        messageMeta.className = 'message-meta';
        
        const timestamp = new Date().toLocaleTimeString();
        const sources = this.formatSources(metadata.sources || []);
        const processingInfo = this.formatProcessingInfo(metadata);
        
        messageMeta.innerHTML = `
            <span class="timestamp">${timestamp}</span>
            <span class="sources">${sources}${processingInfo}</span>
        `;
        
        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(messageMeta);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    processMessageContent(content) {
        // Convert line breaks to <br> tags
        content = content.replace(/\n/g, '<br>');
        
        // Convert **bold** to <strong>
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert URLs to links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        content = content.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');
        
        return content;
    }
    
    formatSources(sources) {
        if (!sources || sources.length === 0) return 'No sources';
        
        const sourceMap = {
            'Memory': '🧠 Memory',
            'Web Search': '🌐 Web',
            'mock': '🎭 Demo'
        };
        
        return sources.map(source => sourceMap[source] || source).join(', ');
    }
    
    formatProcessingInfo(metadata) {
        if (!metadata) return '';
        
        const parts = [];
        
        if (metadata.memory_used > 0) {
            parts.push(`${metadata.memory_used} memories`);
        }
        
        if (metadata.web_results > 0) {
            parts.push(`${metadata.web_results} web results`);
        }
        
        if (metadata.facts_retrieved > 0) {
            parts.push(`${metadata.facts_retrieved} facts`);
        }
        
        if (metadata.processing_time) {
            parts.push(`${metadata.processing_time}s`);
        }
        
        return parts.length > 0 ? ` (${parts.join(', ')})` : '';
    }
    
    async clearMemory() {
        if (!confirm('Are you sure you want to clear all memory? This cannot be undone.')) {
            return;
        }
        
        this.showLoading(true);
        this.updateStatus('Clearing memory...');
        
        try {
            const response = await fetch('/api/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Clear chat messages except welcome message
                const messages = this.chatMessages.querySelectorAll('.message');
                messages.forEach((message, index) => {
                    if (index > 0) { // Keep first message (welcome)
                        message.remove();
                    }
                });
                
                this.addMessage('assistant', '🧹 Memory cleared! I\'ve forgotten our previous conversations.', {
                    sources: ['System'],
                    processing_time: 0
                });
                
                this.updateStats();
                this.updateStatus('Memory cleared');
            } else {
                this.addMessage('assistant', `Failed to clear memory: ${data.error}`, {
                    sources: ['Error'],
                    processing_time: 0
                });
            }
            
        } catch (error) {
            console.error('Clear memory error:', error);
            this.addMessage('assistant', 'Failed to clear memory due to network error.', {
                sources: ['Error'],
                processing_time: 0
            });
        } finally {
            this.showLoading(false);
        }
    }
    
    async runDemo() {
        if (!confirm('This will run a demo conversation. Continue?')) {
            return;
        }
        
        this.showLoading(true);
        this.updateStatus('Running demo...');
        
        try {
            const response = await fetch('/api/demo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.demo_results) {
                // Add each demo conversation turn
                for (const result of data.demo_results) {
                    this.addMessage('user', result.user_message);
                    
                    await new Promise(resolve => setTimeout(resolve, 500)); // Small delay
                    
                    this.addMessage('assistant', result.assistant_response, result.metadata);
                    
                    await new Promise(resolve => setTimeout(resolve, 800)); // Delay between turns
                }
                
                this.addMessage('assistant', `✨ Demo completed! Processed ${data.total_turns} conversation turns.`, {
                    sources: ['Demo'],
                    processing_time: 0
                });
                
                this.updateStats();
                this.updateStatus('Demo completed');
            } else {
                this.addMessage('assistant', `Demo failed: ${data.error}`, {
                    sources: ['Error'],
                    processing_time: 0
                });
            }
            
        } catch (error) {
            console.error('Demo error:', error);
            this.addMessage('assistant', 'Demo failed due to network error.', {
                sources: ['Error'],
                processing_time: 0
            });
        } finally {
            this.showLoading(false);
        }
    }
    
    async showStats() {
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            if (stats.error) {
                this.addMessage('assistant', `Stats error: ${stats.error}`, {
                    sources: ['Error'],
                    processing_time: 0
                });
                return;
            }
            
            const statsText = this.formatStatsMessage(stats);
            this.addMessage('assistant', statsText, {
                sources: ['System'],
                processing_time: 0
            });
            
        } catch (error) {
            console.error('Stats error:', error);
            this.addMessage('assistant', 'Failed to retrieve stats due to network error.', {
                sources: ['Error'],
                processing_time: 0
            });
        } finally {
            this.showLoading(false);
        }
    }
    
    formatStatsMessage(stats) {
        const memory = stats.memory_system || {};
        const search = stats.search_tool || {};
        
        return `📊 **Chatbot Statistics**

**Memory System:**
• Conversations: ${memory.conversation_count || 0}
• Documents stored: ${memory.stored_documents || 0}
• Processing stages: ${memory.processing_stages ? memory.processing_stages.length : 0}

**Search Tool:**
• Provider: ${search.provider || 'unknown'}
• Status: ${search.has_api_key ? 'Live search' : 'Mock data'}

**Features:**
${(stats.capabilities || []).map(cap => `• ${cap}`).join('\n')}

**Model:** ${stats.model || 'Unknown'}`;
    }
    
    async updateStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            if (!stats.error) {
                const memory = stats.memory_system || {};
                document.getElementById('convCount').textContent = memory.conversation_count || 0;
                document.getElementById('docCount').textContent = memory.stored_documents || 0;
            }
        } catch (error) {
            console.error('Failed to update stats:', error);
        }
    }
    
    updateStatus(message, duration = 3000) {
        const statusElement = document.getElementById('status');
        const originalText = statusElement.textContent;
        
        statusElement.textContent = message;
        statusElement.style.background = '#4299e1';
        
        setTimeout(() => {
            statusElement.textContent = originalText;
            statusElement.style.background = '#48bb78';
        }, duration);
    }
    
    setInputDisabled(disabled) {
        this.messageInput.disabled = disabled;
        this.sendButton.disabled = disabled;
        
        if (disabled) {
            this.sendButton.textContent = 'Sending...';
        } else {
            this.sendButton.textContent = 'Send';
            this.messageInput.focus();
        }
    }
    
    showLoading(show) {
        if (show) {
            this.loadingOverlay.classList.add('show');
        } else {
            this.loadingOverlay.classList.remove('show');
        }
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatBot();
});

// Update processing time display
setInterval(() => {
    const now = new Date().toLocaleTimeString();
    document.getElementById('lastProcessing').textContent = `${now}`;
}, 1000);