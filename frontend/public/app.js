// RAGme.ai Assistant Frontend JavaScript
class RAGmeAssistant {
    constructor() {
        this.socket = null;
        this.chatHistory = [];
        this.documents = [];
        this.chatSessions = [];
        this.currentChatId = null;
        this.settings = {
            maxDocuments: 20,
            showVectorDbInfo: true
        };
        this.isVisualizationVisible = true;
        this.currentVisualizationType = 'graph'; // Default to network graph
        this.vectorDbInfo = null;
        this.thinkingStartTime = null;
        this.documentRefreshInterval = null; // Add interval for auto-refresh
        this.currentDateFilter = 'current'; // Default to current (this week)
        
        this.init();
    }

    init() {
        this.connectSocket();
        this.setupEventListeners();
        this.setupResizeDivider();
        this.setupVisualizationResize();
        this.loadSettings();
        this.loadChatSessions();
        this.renderChatHistory(); // Render chat history after loading
        this.loadVectorDbInfo();
        this.startAutoRefresh();
    }

    connectSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to RAGme.ai Assistant server');
            // Load documents after connection is established
            this.loadDocuments();
            // Start auto-refresh every 30 seconds
            this.startAutoRefresh();
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from RAGme.ai Assistant server');
            // Stop auto-refresh when disconnected
            this.stopAutoRefresh();
        });

        this.socket.on('chat_response', (response) => {
            // Ensure thinking message is shown for at least 500ms
            const thinkingStartTime = this.thinkingStartTime || 0;
            const minThinkingTime = 500;
            const elapsed = Date.now() - thinkingStartTime;
            
            if (elapsed < minThinkingTime) {
                setTimeout(() => {
                    this.removeThinkingMessage();
                    this.addMessage('ai', response.content, response.id);
                }, minThinkingTime - elapsed);
            } else {
                this.removeThinkingMessage();
                this.addMessage('ai', response.content, response.id);
            }
            
            // Re-enable send button
            const sendButton = document.getElementById('sendButton');
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        });

        this.socket.on('urls_added', (result) => {
            this.showNotification(result.success ? 'success' : 'error', result.message);
            if (result.success) {
                this.loadDocuments();
            }
        });

        this.socket.on('json_added', (result) => {
            this.showNotification(result.success ? 'success' : 'error', result.message);
            if (result.success) {
                this.loadDocuments();
            }
        });

        this.socket.on('documents_listed', (result) => {
            console.log('Documents listed result:', result);
            if (result.success) {
                this.documents = result.documents;
                console.log('Loaded documents:', this.documents.length);
                this.renderDocuments();
                this.updateVisualization();
            } else {
                console.error('Failed to list documents:', result.message);
            }
        });

        this.socket.on('vector_db_info', (result) => {
            if (result.success) {
                this.vectorDbInfo = result.info;
                this.updateVectorDbInfoDisplay();
            }
        });

        this.socket.on('chat_cleared', () => {
            this.clearChat();
        });

        this.socket.on('chat_saved', (result) => {
            this.showNotification(result.success ? 'success' : 'info', result.message);
        });

        this.socket.on('document_summarized', (result) => {
            console.log('Document summarized:', result);
            if (result.success) {
                this.updateDocumentSummary(result.summary);
            } else {
                this.updateDocumentSummary('Failed to generate summary. Please try again.');
            }
        });
    }

    setupEventListeners() {
        // Hamburger menu
        const hamburgerMenu = document.getElementById('hamburgerMenu');
        const menuDropdown = document.getElementById('menuDropdown');
        
        hamburgerMenu.addEventListener('click', (e) => {
            e.stopPropagation();
            menuDropdown.classList.toggle('show');
        });

        document.addEventListener('click', () => {
            menuDropdown.classList.remove('show');
        });

        // Menu items
        document.getElementById('newChat').addEventListener('click', () => {
            this.createNewChat();
        });

        document.getElementById('clearCurrentChat').addEventListener('click', () => {
            this.clearChat();
        });

        document.getElementById('clearHistory').addEventListener('click', () => {
            this.clearChatHistory();
        });

        document.getElementById('clearEverything').addEventListener('click', () => {
            this.clearEverything();
        });

        document.getElementById('settings').addEventListener('click', () => {
            this.showSettingsModal();
        });

        // Sidebar collapse buttons
        document.getElementById('collapseSidebar').addEventListener('click', () => {
            this.toggleSidebar('chatHistorySidebar', 'restoreSidebarBtn');
        });

        document.getElementById('collapseDocuments').addEventListener('click', () => {
            this.toggleSidebar('documentsSidebar', 'restoreDocumentsBtn');
        });

        // Restore buttons
        document.getElementById('restoreSidebarBtn').addEventListener('click', () => {
            this.restoreSidebar('chatHistorySidebar', 'restoreSidebarBtn');
        });

        document.getElementById('restoreDocumentsBtn').addEventListener('click', () => {
            this.restoreSidebar('documentsSidebar', 'restoreDocumentsBtn');
        });

        // Refresh documents button
        document.getElementById('refreshDocuments').addEventListener('click', () => {
            this.refreshDocuments();
        });

        // Date filter selector
        document.getElementById('dateFilterSelector').addEventListener('change', (e) => {
            this.currentDateFilter = e.target.value;
            localStorage.setItem('ragme-date-filter', this.currentDateFilter);
            this.loadDocuments();
        });

        // Chat input
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendButton');

        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        sendButton.addEventListener('click', () => {
            this.sendMessage();
        });

        // Auto-resize textarea
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        });

        // Add content button
        document.getElementById('addContentBtn').addEventListener('click', () => {
            this.showAddContentModal();
        });

        // Modal close buttons
        document.getElementById('closeAddContent').addEventListener('click', () => {
            this.hideModal('addContentModal');
        });

        document.getElementById('closeSettings').addEventListener('click', () => {
            this.hideModal('settingsModal');
        });

        document.getElementById('closeDocumentDetails').addEventListener('click', () => {
            this.hideModal('documentDetailsModal');
        });

        // Add content modal
        document.getElementById('submitAddContent').addEventListener('click', () => {
            this.submitAddContent();
        });

        document.getElementById('cancelAddContent').addEventListener('click', () => {
            this.hideModal('addContentModal');
        });

        // Settings modal
        document.getElementById('saveSettings').addEventListener('click', () => {
            this.saveSettings();
        });

        document.getElementById('cancelSettings').addEventListener('click', () => {
            this.hideModal('settingsModal');
        });

        // Content tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Visualization toggle
        document.getElementById('visualizationToggleBtn').addEventListener('click', () => {
            this.toggleVisualization();
        });

        // Visualization type selector
        document.getElementById('visualizationTypeSelector').addEventListener('change', (e) => {
            this.currentVisualizationType = e.target.value;
            if (this.isVisualizationVisible) {
                this.updateVisualization();
            }
        });

        // Resize divider
        this.setupResizeDivider();

        // Document details modal close
        document.getElementById('closeDocumentDetailsBtn').addEventListener('click', () => {
            this.hideModal('documentDetailsModal');
        });

        // Document details modal delete button
        document.getElementById('deleteDocumentFromDetails').addEventListener('click', () => {
            this.deleteDocumentFromDetails();
        });

        // Email modal
        document.getElementById('closeEmailModal').addEventListener('click', () => {
            this.hideModal('emailModal');
        });

        document.getElementById('cancelEmail').addEventListener('click', () => {
            this.hideModal('emailModal');
        });

        document.getElementById('sendEmail').addEventListener('click', () => {
            this.sendEmail();
        });

        // File upload setup
        this.setupFileUpload();

        // Modal overlay click to close
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    const modalId = overlay.id;
                    this.hideModal(modalId);
                }
            });
        });

    }

    sendMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();
        
        if (!message) return;

        // Add user message
        this.addMessage('user', message);
        
        // Clear input
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Add thinking message
        const thinkingId = this.addThinkingMessage();

        // Send to server
        this.socket.emit('chat_message', {
            content: message,
            timestamp: new Date().toISOString()
        });

        // Disable send button while processing
        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        // Store thinking message ID and start time
        this.currentThinkingId = thinkingId;
        this.thinkingStartTime = Date.now();

        // Re-enable after response (fallback)
        setTimeout(() => {
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }, 10000);
    }

    addThinkingMessage() {
        const messagesContainer = document.getElementById('chatMessages');
        const thinkingId = 'thinking-' + Date.now();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai thinking';
        messageDiv.dataset.messageId = thinkingId;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '🤖';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content thinking-content';
        contentDiv.innerHTML = `
            <div class="thinking-animation">
                <span>thinking</span>
                <span class="dots">
                    <span class="dot">.</span>
                    <span class="dot">.</span>
                    <span class="dot">.</span>
                </span>
            </div>
        `;

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return thinkingId;
    }

    removeThinkingMessage() {
        if (this.currentThinkingId) {
            const thinkingMessage = document.querySelector(`[data-message-id="${this.currentThinkingId}"]`);
            if (thinkingMessage) {
                thinkingMessage.remove();
            }
            this.currentThinkingId = null;
        }
    }

    addMessage(type, content, id = null) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageId = id || Date.now().toString();
        
        const message = {
            id: messageId,
            type,
            content,
            timestamp: new Date().toISOString()
        };

        // Store in chat history
        this.chatHistory.push(message);

        // Update current chat session
        if (this.currentChatId) {
            const currentChat = this.chatSessions.find(c => c.id === this.currentChatId);
            if (currentChat) {
                currentChat.messages.push(message);
                currentChat.updatedAt = new Date().toISOString();
                
                // Update chat title based on first user message
                if (type === 'user' && currentChat.messages.filter(m => m.type === 'user').length === 1) {
                    currentChat.title = content.substring(0, 50) + (content.length > 50 ? '...' : '');
                }
                
                this.saveChatSessions();
                this.renderChatHistory();
            }
        }

        this.renderMessage(message);

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    addWelcomeMessage() {
        const welcomeMessage = `Welcome to **🤖 RAGme.ai Assistant**! 

I can help you with:

• **Adding URLs** - Tell me URLs to crawl and add to your knowledge base
• **Adding documents (Text, PDF, DOCX, etc.)** - Use the "Add Content" button to add files and structured data
• **Answering questions** - Ask me anything about your documents
• **Document management** - View and explore your documents in the right panel

Try asking me to add some URLs or ask questions about your existing documents!`;

        this.addMessage('ai', welcomeMessage);
    }

    createNewChat() {
        const chatId = Date.now().toString();
        const newChat = {
            id: chatId,
            title: 'New Chat',
            messages: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        
        this.chatSessions.unshift(newChat);
        this.currentChatId = chatId;
        this.chatHistory = [];
        
        this.renderChatHistory();
        this.addWelcomeMessage();
        this.saveChatSessions();
    }

    loadChatSessions() {
        const saved = localStorage.getItem('ragme-chat-sessions');
        if (saved) {
            this.chatSessions = JSON.parse(saved);
        }
    }

    saveChatSessions() {
        localStorage.setItem('ragme-chat-sessions', JSON.stringify(this.chatSessions));
    }

    renderChatHistory() {
        const container = document.getElementById('chatHistoryList');
        container.innerHTML = '';

        if (this.chatSessions.length === 0) {
            container.innerHTML = `
                <div class="no-chats">
                    <i class="fas fa-comments"></i>
                    <p>No chat history yet</p>
                    <small>Start a conversation to see it here</small>
                </div>
            `;
            return;
        }

        this.chatSessions.forEach((chat, index) => {
            const chatItem = document.createElement('div');
            chatItem.className = 'chat-history-item';
            chatItem.dataset.chatId = chat.id;
            
            if (chat.id === this.currentChatId) {
                chatItem.classList.add('active');
            }

            const date = new Date(chat.updatedAt);
            const timeString = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            chatItem.innerHTML = `
                <div class="chat-id">#${chat.id}</div>
                <div class="chat-title" data-chat-id="${chat.id}">${chat.title}</div>
                <div class="chat-time">${timeString}</div>
                <button class="chat-save-btn" data-chat-id="${chat.id}" title="Save chat">
                    <i class="fas fa-download"></i>
                </button>
                <button class="chat-email-btn" data-chat-id="${chat.id}" title="Email chat">
                    <i class="fas fa-envelope"></i>
                </button>
                <button class="chat-delete-btn" data-chat-id="${chat.id}" title="Delete chat">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            
            // Add click handler for loading chat
            chatItem.addEventListener('click', (e) => {
                // Don't load chat if clicking on buttons or title (for editing)
                if (!e.target.classList.contains('chat-title') && 
                    !e.target.closest('.chat-delete-btn') &&
                    !e.target.closest('.chat-save-btn') &&
                    !e.target.closest('.chat-email-btn')) {
                    this.loadChat(chat.id);
                }
            });
            
            // Add click handler for editing title
            const titleElement = chatItem.querySelector('.chat-title');
            titleElement.addEventListener('click', (e) => {
                e.stopPropagation();
                this.editChatTitle(chat.id, chat.title);
            });
            
            // Add click handler for deleting chat
            const deleteBtn = chatItem.querySelector('.chat-delete-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteChat(chat.id);
            });
            
            // Add click handler for saving chat
            const saveBtn = chatItem.querySelector('.chat-save-btn');
            saveBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.saveChatAsFile(chat);
            });
            
            // Add click handler for emailing chat
            const emailBtn = chatItem.querySelector('.chat-email-btn');
            emailBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showChatEmailModal(chat);
            });
            
            container.appendChild(chatItem);
        });
    }

    loadChat(chatId) {
        const chat = this.chatSessions.find(c => c.id === chatId);
        if (chat) {
            this.currentChatId = chatId;
            this.chatHistory = [...chat.messages];
            
            const messagesContainer = document.getElementById('chatMessages');
            messagesContainer.innerHTML = '';
            
            this.chatHistory.forEach(msg => {
                this.renderMessage(msg);
            });
            
            this.renderChatHistory();
        }
    }

    editChatTitle(chatId, currentTitle) {
        const titleElement = document.querySelector(`[data-chat-id="${chatId}"]`);
        if (!titleElement) return;
        
        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentTitle;
        input.className = 'chat-title-edit';
        input.style.cssText = `
            width: 100%;
            padding: 2px 4px;
            border: 1px solid #3b82f6;
            border-radius: 4px;
            font-size: inherit;
            font-family: inherit;
            background: white;
            color: #374151;
        `;
        
        const saveTitle = () => {
            const newTitle = input.value.trim();
            if (newTitle && newTitle !== currentTitle) {
                const chatIndex = this.chatSessions.findIndex(c => c.id === chatId);
                if (chatIndex !== -1) {
                    this.chatSessions[chatIndex].title = newTitle;
                    this.saveChatSessions();
                    this.renderChatHistory();
                    this.showNotification('success', 'Chat title updated');
                }
            }
            titleElement.textContent = newTitle || currentTitle;
        };
        
        const cancelEdit = () => {
            titleElement.textContent = currentTitle;
        };
        
        input.addEventListener('blur', saveTitle);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                saveTitle();
            } else if (e.key === 'Escape') {
                cancelEdit();
            }
        });
        
        titleElement.textContent = '';
        titleElement.appendChild(input);
        input.focus();
        input.select();
    }

    deleteChat(chatId) {
        const chat = this.chatSessions.find(c => c.id === chatId);
        if (!chat) {
            this.showNotification('error', 'Chat not found');
            return;
        }
        
        const confirmMessage = `Are you sure you want to delete "${chat.title}"? This action cannot be undone.`;
        if (!confirm(confirmMessage)) {
            return;
        }
        
        // Remove chat from sessions
        this.chatSessions = this.chatSessions.filter(c => c.id !== chatId);
        
        // If this was the current chat, clear it
        if (this.currentChatId === chatId) {
            this.currentChatId = null;
            this.clearChat();
        }
        
        // Save updated sessions
        this.saveChatSessions();
        this.renderChatHistory();
        
        this.showNotification('success', `Deleted chat: ${chat.title}`);
    }

    renderMessage(message) {
        const messagesContainer = document.getElementById('chatMessages');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.type}`;
        messageDiv.dataset.messageId = message.id;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = message.type === 'user' ? '👤' : '🤖';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Parse markdown and sanitize
        const parsedContent = simpleMarkdownParser(message.content);
        const sanitizedContent = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(parsedContent) : parsedContent;
        contentDiv.innerHTML = sanitizedContent;

        // Add copy button for AI messages
        if (message.type === 'ai') {
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.title = 'Copy to clipboard';
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(message.content);
                this.showNotification('success', 'Copied to clipboard!');
            });
            contentDiv.appendChild(copyBtn);

            // Add save button for AI messages
            const saveBtn = document.createElement('button');
            saveBtn.className = 'save-btn';
            saveBtn.innerHTML = '<i class="fas fa-download"></i>';
            saveBtn.title = 'Save as markdown file';
            saveBtn.addEventListener('click', () => {
                this.saveMessageAsFile(message);
            });
            contentDiv.appendChild(saveBtn);

            // Add email button for AI messages
            const emailBtn = document.createElement('button');
            emailBtn.className = 'email-btn';
            emailBtn.innerHTML = '<i class="fas fa-envelope"></i>';
            emailBtn.title = 'Send via email';
            emailBtn.addEventListener('click', () => {
                this.showEmailModal(message);
            });
            contentDiv.appendChild(emailBtn);
        }

        // Add replay button for user messages
        if (message.type === 'user') {
            const replayBtn = document.createElement('button');
            replayBtn.className = 'replay-btn';
            replayBtn.innerHTML = '<i class="fas fa-redo"></i>';
            replayBtn.title = 'Retry this query';
            replayBtn.addEventListener('click', () => {
                this.retryQuery(message.content);
            });
            contentDiv.appendChild(replayBtn);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
    }

    clearChat() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.innerHTML = '';
        this.chatHistory = [];
        this.addWelcomeMessage();
    }

    clearChatHistory() {
        this.chatSessions = [];
        this.currentChatId = null;
        this.chatHistory = [];
        localStorage.removeItem('ragme-chat-sessions');
        this.renderChatHistory();
        this.createNewChat();
        this.showNotification('info', 'Chat history cleared');
    }

    clearEverything() {
        this.clearChat();
        this.documents = [];
        this.renderDocuments();
        this.updateVisualization();
        this.showNotification('info', 'Everything cleared');
    }

    toggleSidebar(sidebarId, restoreBtnId) {
        console.log('Toggling sidebar:', sidebarId, restoreBtnId);
        const sidebar = document.getElementById(sidebarId);
        const restoreBtn = document.getElementById(restoreBtnId);
        
        if (sidebar && restoreBtn) {
            sidebar.classList.add('collapsed');
            restoreBtn.style.display = 'block';
            
            // Hide resize divider when documents sidebar is collapsed
            if (sidebarId === 'documentsSidebar') {
                const resizeDivider = document.getElementById('resizeDivider');
                if (resizeDivider) {
                    resizeDivider.classList.add('hidden');
                }
            }
            
            console.log('Sidebar collapsed, restore button shown');
        } else {
            console.error('Could not find sidebar or restore button:', { sidebar, restoreBtn });
        }
    }

    restoreSidebar(sidebarId, restoreBtnId) {
        console.log('Restoring sidebar:', sidebarId, restoreBtnId);
        const sidebar = document.getElementById(sidebarId);
        const restoreBtn = document.getElementById(restoreBtnId);
        
        if (sidebar && restoreBtn) {
            sidebar.classList.remove('collapsed');
            restoreBtn.style.display = 'none';
            
            // Show resize divider when documents sidebar is restored
            if (sidebarId === 'documentsSidebar') {
                const resizeDivider = document.getElementById('resizeDivider');
                if (resizeDivider) {
                    resizeDivider.classList.remove('hidden');
                }
            }
            
            console.log('Sidebar restored, restore button hidden');
        } else {
            console.error('Could not find sidebar or restore button:', { sidebar, restoreBtn });
        }
    }

    setupResizeDivider() {
        const divider = document.getElementById('resizeDivider');
        const documentsSidebar = document.getElementById('documentsSidebar');
        let isResizing = false;
        let startX = 0;
        let startWidth = 0;

        divider.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = documentsSidebar.offsetWidth;
            document.body.style.cursor = 'col-resize';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const deltaX = startX - e.clientX;
            const newWidth = startWidth + deltaX;
            
            if (newWidth > 200 && newWidth < window.innerWidth * 0.8) {
                documentsSidebar.style.width = newWidth + 'px';
            }
        });

        document.addEventListener('mouseup', () => {
            isResizing = false;
            document.body.style.cursor = '';
        });
    }

    setupVisualizationResize() {
        const resizeHandle = document.getElementById('visualizationResizeHandle');
        const visualization = document.getElementById('documentsVisualization');
        const documentsContent = document.getElementById('documentsContent');
        
        let isResizing = false;
        let startY = 0;
        let startHeight = 0;
        let minHeight = 200; // Minimum height
        let maxHeight = window.innerHeight * 0.7; // Maximum height for manual resizing

        // Update max height when window resizes
        window.addEventListener('resize', () => {
            maxHeight = window.innerHeight * 0.7;
        });

        // Remove the automatic resize observer - only resize when user manually resizes
        // const resizeObserver = new ResizeObserver((entries) => {
        //     for (const entry of entries) {
        //         if (entry.target.id === 'visualizationContent' && this.isVisualizationVisible) {
        //             console.log('Visualization container resized, updating visualization...');
        //             // Debounce the update to avoid too many calls
        //             clearTimeout(this.resizeTimeout);
        //             this.resizeTimeout = setTimeout(() => {
        //                 this.updateVisualization();
        //             }, 100);
        //         }
        //     }
        // });

        // Observe the visualization content container
        // const visualizationContent = document.getElementById('visualizationContent');
        // if (visualizationContent) {
        //     resizeObserver.observe(visualizationContent);
        // }

        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startY = e.clientY;
            startHeight = visualization.offsetHeight;
            resizeHandle.classList.add('resizing');
            document.body.style.cursor = 'ns-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const deltaY = e.clientY - startY;
            const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight + deltaY));
            
            visualization.style.height = newHeight + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizeHandle.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                
                // Only update visualization if it's visible and user manually resized
                if (this.isVisualizationVisible) {
                    console.log('Manual resize complete, updating visualization...');
                    this.updateVisualization();
                }
            }
        });
    }

    showAddContentModal() {
        this.showModal('addContentModal');
        this.switchTab('urls');
    }

    showSettingsModal() {
        this.showModal('settingsModal');
        document.getElementById('maxDocuments').value = this.settings.maxDocuments;
        document.getElementById('showVectorDbInfo').checked = this.settings.showVectorDbInfo;
    }

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('show');
    }

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('show');
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');
    }

    submitAddContent() {
        const activeTab = document.querySelector('.tab-btn.active').dataset.tab;
        
        if (activeTab === 'urls') {
            const urlInput = document.getElementById('urlInput');
            const urls = urlInput.value.trim().split('\n').filter(url => url.trim());
            
            if (urls.length === 0) {
                this.showNotification('error', 'Please enter at least one URL');
                return;
            }

            this.socket.emit('add_urls', { urls });
            urlInput.value = '';
        } else if (activeTab === 'files') {
            const fileInput = document.getElementById('fileInput');
            const files = fileInput.files;
            
            if (files.length === 0) {
                this.showNotification('error', 'Please select at least one file');
                return;
            }

            // Handle file uploads
            this.uploadFiles(files);
        } else if (activeTab === 'json') {
            const jsonInput = document.getElementById('jsonInput');
            const metadataInput = document.getElementById('metadataInput');
            
            try {
                const jsonData = JSON.parse(jsonInput.value.trim());
                const metadata = metadataInput.value.trim() ? JSON.parse(metadataInput.value.trim()) : null;
                
                this.socket.emit('add_json', { jsonData, metadata });
                jsonInput.value = '';
                metadataInput.value = '';
            } catch (error) {
                this.showNotification('error', 'Invalid JSON format');
                return;
            }
        }

        this.hideModal('addContentModal');
    }

    uploadFiles(files) {
        const formData = new FormData();
        
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        // Show loading notification
        this.showNotification('info', `Uploading ${files.length} file(s)...`);

        // Send files to backend
        fetch('/upload-files', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.showNotification('success', `Successfully uploaded ${files.length} file(s)`);
                // Refresh documents list
                this.loadDocuments();
            } else {
                this.showNotification('error', data.message || 'Upload failed');
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            this.showNotification('error', 'Upload failed. Please try again.');
        });
    }

    setupFileUpload() {
        const fileUploadArea = document.getElementById('fileUploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');

        // Click to select files
        fileUploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // Handle file selection
        fileInput.addEventListener('change', (e) => {
            this.updateFileList(e.target.files);
        });

        // Drag and drop functionality
        fileUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUploadArea.classList.add('dragover');
        });

        fileUploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            fileUploadArea.classList.remove('dragover');
        });

        fileUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            fileInput.files = files;
            this.updateFileList(files);
        });
    }

    updateFileList(files) {
        const fileList = document.getElementById('fileList');
        fileList.innerHTML = '';

        Array.from(files).forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            const fileIcon = this.getFileIcon(file.name);
            const fileSize = this.formatFileSize(file.size);
            
            fileItem.innerHTML = `
                <div class="file-item-info">
                    <i class="fas ${fileIcon} file-item-icon"></i>
                    <div>
                        <div class="file-item-name">${this.escapeHtml(file.name)}</div>
                        <div class="file-item-size">${fileSize}</div>
                    </div>
                </div>
                <button class="file-item-remove" onclick="this.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            fileList.appendChild(fileItem);
        });
    }

    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const iconMap = {
            'pdf': 'fa-file-pdf',
            'docx': 'fa-file-word',
            'doc': 'fa-file-word',
            'txt': 'fa-file-alt',
            'md': 'fa-file-alt',
            'json': 'fa-file-code',
            'csv': 'fa-file-csv'
        };
        return iconMap[ext] || 'fa-file';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    saveSettings() {
        const maxDocuments = parseInt(document.getElementById('maxDocuments').value);
        const showVectorDbInfo = document.getElementById('showVectorDbInfo').checked;
        
        if (maxDocuments < 1 || maxDocuments > 100) {
            this.showNotification('error', 'Max documents must be between 1 and 100');
            return;
        }

        this.settings.maxDocuments = maxDocuments;
        this.settings.showVectorDbInfo = showVectorDbInfo;
        localStorage.setItem('ragme-settings', JSON.stringify(this.settings));
        
        // Save date filter preference
        localStorage.setItem('ragme-date-filter', this.currentDateFilter);
        
        this.hideModal('settingsModal');
        this.showNotification('success', 'Settings saved');
        
        // Update vector DB info display based on new setting
        this.updateVectorDbInfoDisplay();
        
        // Reload documents with new settings
        this.loadDocuments();
    }

    loadSettings() {
        const saved = localStorage.getItem('ragme-settings');
        if (saved) {
            this.settings = { ...this.settings, ...JSON.parse(saved) };
        }
        
        // Load date filter preference
        const savedDateFilter = localStorage.getItem('ragme-date-filter');
        if (savedDateFilter) {
            this.currentDateFilter = savedDateFilter;
            // Update the dropdown to reflect the saved preference
            const dateFilterSelector = document.getElementById('dateFilterSelector');
            if (dateFilterSelector) {
                dateFilterSelector.value = this.currentDateFilter;
            }
        }
    }

    loadDocuments() {
        console.log('Loading documents with date filter:', this.currentDateFilter);
        this.socket.emit('list_documents', {
            limit: this.settings.maxDocuments,
            offset: 0,
            dateFilter: this.currentDateFilter
        });
    }

    refreshDocuments() {
        const refreshBtn = document.getElementById('refreshDocuments');
        const icon = refreshBtn.querySelector('i');
        
        // Add loading animation
        refreshBtn.classList.add('loading');
        icon.className = 'fas fa-sync-alt';
        
        // Load documents with current date filter
        this.loadDocuments();
        
        // Also explicitly update visualization after a short delay to ensure it's refreshed
        setTimeout(() => {
            console.log('Explicitly updating visualization after refresh...');
            this.updateVisualization();
        }, 500);
        
        // Remove loading animation after a short delay
        setTimeout(() => {
            refreshBtn.classList.remove('loading');
            icon.className = 'fas fa-sync-alt';
        }, 1000);
        
        // Show notification
        this.showNotification('info', `Refreshing documents (${this.getDateFilterDisplayName()})...`);
    }

    getDateFilterDisplayName() {
        const filterNames = {
            'current': 'Current',
            'month': 'This Month',
            'year': 'This Year',
            'all': 'All'
        };
        return filterNames[this.currentDateFilter] || 'Current';
    }

    startAutoRefresh() {
        // Clear any existing interval
        this.stopAutoRefresh();
        // Start new interval - refresh every 30 seconds
        this.documentRefreshInterval = setInterval(() => {
            console.log('Auto-refreshing documents...');
            this.loadDocuments();
        }, 30000); // 30 seconds
    }

    stopAutoRefresh() {
        if (this.documentRefreshInterval) {
            clearInterval(this.documentRefreshInterval);
            this.documentRefreshInterval = null;
        }
    }

    fetchDocumentSummary(doc) {
        let docIndex = -1;
        
        // Handle chunked documents differently
        if (doc.isGroupedChunks && doc.chunks && doc.chunks.length > 0) {
            // For grouped chunked documents, use the first chunk's index
            const firstChunk = doc.chunks[0];
            docIndex = this.documents.findIndex(d => d.id === firstChunk.id);
        } else if (doc.metadata?.is_chunked && doc.metadata?.total_chunks) {
            // For new chunked documents, find by base URL
            const baseUrl = doc.url.split('#')[0];
            docIndex = this.documents.findIndex(d => {
                const docBaseUrl = d.url.split('#')[0];
                return docBaseUrl === baseUrl;
            });
        } else {
            // For regular documents, find by URL
            docIndex = this.documents.findIndex(d => d.url === doc.url);
        }
        
        if (docIndex === -1) {
            this.updateDocumentSummary('Document not found for summarization.');
            return;
        }
        
        // Set a timeout to show a message if summarization takes too long
        const timeoutId = setTimeout(() => {
            this.updateDocumentSummary('<div class="summary-loading">Still generating summary... This may take a moment for large documents.</div>');
        }, 10000); // 10 seconds
        
        // Request summary from backend
        this.socket.emit('summarize_document', {
            documentId: docIndex.toString()
        });
        
        // Store timeout ID to clear it when summary arrives
        this.summaryTimeoutId = timeoutId;
    }

    updateDocumentSummary(summary) {
        // Clear the timeout if it exists
        if (this.summaryTimeoutId) {
            clearTimeout(this.summaryTimeoutId);
            this.summaryTimeoutId = null;
        }
        
        const contentPreview = document.querySelector('#documentDetailsModal .content-preview');
        if (contentPreview) {
            // Parse markdown and format the summary
            const formattedSummary = this.formatMarkdownSummary(summary);
            contentPreview.innerHTML = formattedSummary;
        }
    }

    formatMarkdownSummary(text) {
        if (!text) {
            return '<div class="no-content">No summary available</div>';
        }
        
        // Simple markdown parsing for common elements
        let formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
            .replace(/^### (.*$)/gim, '<h3>$1</h3>') // H3
            .replace(/^## (.*$)/gim, '<h2>$1</h2>') // H2
            .replace(/^# (.*$)/gim, '<h1>$1</h1>') // H1
            .replace(/^- (.*$)/gim, '<li>$1</li>') // List items
            .replace(/\n\n/g, '</p><p>') // Paragraphs
            .replace(/^(.+)$/gm, '<p>$1</p>'); // Wrap lines in paragraphs
        
        // Clean up empty paragraphs
        formattedText = formattedText.replace(/<p><\/p>/g, '');
        
        return `
            <div class="content-text summary-content">
                ${formattedText}
            </div>
        `;
    }

    renderDocuments() {
        const container = document.getElementById('documentsListContainer');
        container.innerHTML = '';

        if (this.documents.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: #666; padding: 2rem;">
                    <i class="fas fa-file-alt" style="font-size: 3rem; opacity: 0.5; margin-bottom: 1rem;"></i>
                    <p>No documents found</p>
                    <p style="font-size: 0.8rem; margin-top: 0.5rem;">Add some URLs or JSON data to get started</p>
                </div>
            `;
            return;
        }

        // Group documents by their base URL/filename to handle existing chunked documents
        const groupedDocuments = this.groupDocumentsByBaseUrl(this.documents);

        groupedDocuments.forEach((group, index) => {
            const card = document.createElement('div');
            card.className = 'document-card';
            card.dataset.docIndex = index;
            
            // Add click handler for viewing document details
            card.addEventListener('click', (e) => {
                console.log('Card clicked', group, e.target);
                if (!e.target.closest('.document-delete-btn')) {
                    this.showDocumentDetails(group);
                }
            });

            const title = group.url || group.metadata?.filename || `Document ${index + 1}`;
            const date = group.metadata?.date_added || 'Unknown date';
            
            // Handle chunked documents (both new and existing)
            let summary = '';
            let chunkInfo = '';
            
            if (group.metadata?.is_chunked && group.metadata?.total_chunks) {
                // New chunked document format
                const totalChunks = group.metadata.total_chunks;
                const originalFilename = group.metadata.original_filename || title;
                
                summary = group.text ? group.text.substring(0, 200) + '...' : 'No content available';
                chunkInfo = `<span class="chunk-badge"><i class="fas fa-layer-group"></i> ${totalChunks} chunks</span>`;
                
                card.innerHTML = `
                    <div class="document-content">
                        <div class="document-title">
                            <span class="document-title-text">${this.escapeHtml(originalFilename)}</span>
                            ${chunkInfo}
                        </div>
                        <div class="document-meta">
                            <i class="fas fa-calendar"></i> ${date} | 
                            <i class="fas fa-database"></i> ${group.metadata?.collection || 'Default'} |
                            <i class="fas fa-file-alt"></i> Chunked document
                        </div>
                        <div class="document-summary">${this.escapeHtml(summary)}</div>
                    </div>
                    <button class="document-delete-btn" data-doc-index="${index}" title="Delete document">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
            } else if (group.isGroupedChunks && group.totalChunks > 1) {
                // Existing chunked documents that were grouped
                const originalFilename = group.originalFilename || title;
                
                summary = group.combinedText ? group.combinedText.substring(0, 200) + '...' : 'No content available';
                chunkInfo = `<span class="chunk-badge"><i class="fas fa-layer-group"></i> ${group.totalChunks} chunks</span>`;
                
                card.innerHTML = `
                    <div class="document-content">
                        <div class="document-title">
                            <span class="document-title-text">${this.escapeHtml(originalFilename)}</span>
                            ${chunkInfo}
                        </div>
                        <div class="document-meta">
                            <i class="fas fa-calendar"></i> ${date} | 
                            <i class="fas fa-database"></i> ${group.metadata?.collection || 'Default'} |
                            <i class="fas fa-file-alt"></i> Chunked document
                        </div>
                        <div class="document-summary">${this.escapeHtml(summary)}</div>
                    </div>
                    <button class="document-delete-btn" data-doc-index="${index}" title="Delete document">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
            } else {
                // Regular document
                summary = group.text ? group.text.substring(0, 150) + '...' : 'No content available';
                
                card.innerHTML = `
                    <div class="document-content">
                        <div class="document-title">
                            <span class="document-title-text">${this.escapeHtml(title)}</span>
                        </div>
                        <div class="document-meta">
                            <i class="fas fa-calendar"></i> ${date} | 
                            <i class="fas fa-database"></i> ${group.metadata?.collection || 'Default'}
                        </div>
                        <div class="document-summary">${this.escapeHtml(summary)}</div>
                    </div>
                    <button class="document-delete-btn" data-doc-index="${index}" title="Delete document">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
            }

            container.appendChild(card);

            // Attach delete button handler after appending to DOM
            const deleteBtn = card.querySelector('.document-delete-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.deleteDocument(index);
                });
            }

            // Attach card click handler after appending to DOM
            card.addEventListener('click', (e) => {
                console.log('Card clicked', group, e.target);
                if (!e.target.closest('.document-delete-btn')) {
                    this.showDocumentDetails(group);
                }
            });
        });
        
        // Check for text truncation after rendering all documents
        setTimeout(() => {
            this.checkDocumentTitlesTruncation();
        }, 100);
    }

    showDocumentDetails(doc) {
        const modal = document.getElementById('documentDetailsModal');
        const title = document.getElementById('documentDetailsTitle');
        const body = document.getElementById('documentDetailsBody');

        // Find the document index in the grouped documents array
        const groupedDocuments = this.groupDocumentsByBaseUrl(this.documents);
        const docIndex = groupedDocuments.findIndex(d => d.url === doc.url || d.id === doc.id);
        
        // Store the document index for deletion
        modal.dataset.docIndex = docIndex;

        let displayTitle = doc.url || doc.metadata?.filename || 'Document Details';
        
        // Use original filename for chunked documents
        if (doc.isGroupedChunks && doc.originalFilename) {
            displayTitle = doc.originalFilename;
        } else if (doc.metadata?.is_chunked && doc.metadata?.original_filename) {
            displayTitle = doc.metadata.original_filename;
        }

        title.textContent = displayTitle;

        // Create metadata tags (including collection and type)
        const metadataTags = this.createMetadataTags(doc.metadata);
        
        // Show loading state for content
        const loadingContent = `
            <div class="content-preview">
                <div class="content-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Generating AI summary...</p>
                </div>
            </div>
        `;

        const details = `
            <div class="document-details-section">
                <h4><i class="fas fa-link"></i> URL/ID</h4>
                <div class="detail-value">${this.escapeHtml(doc.url || 'N/A')}</div>
            </div>
            
            <div class="document-details-section">
                <h4><i class="fas fa-calendar"></i> Date Added</h4>
                <div class="detail-value">${this.formatDate(doc.metadata?.date_added) || 'Unknown'}</div>
            </div>
            
            ${metadataTags ? `
                <div class="document-details-section">
                    <h4><i class="fas fa-tags"></i> Metadata</h4>
                    <div class="metadata-tags">
                        ${metadataTags}
                    </div>
                </div>
            ` : ''}
            
            <div class="document-details-section">
                <h4><i class="fas fa-robot"></i> AI Summary</h4>
                ${loadingContent}
            </div>
        `;

        body.innerHTML = details;
        this.showModal('documentDetailsModal');
        
        // Check for text truncation in modal details
        setTimeout(() => {
            this.checkDetailValuesTruncation();
        }, 100);
        
        // Fetch AI summary
        this.fetchDocumentSummary(doc);
    }

    formatDate(dateString) {
        if (!dateString) return null;
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (e) {
            return dateString;
        }
    }

    createMetadataTags(metadata) {
        if (!metadata) return '';
        
        const tags = [];
        const excludeKeys = ['date_added']; // Only exclude date_added, show everything else
        
        Object.entries(metadata).forEach(([key, value]) => {
            if (!excludeKeys.includes(key)) {
                let displayValue = value;
                
                // Format specific fields
                if (key === 'type') {
                    displayValue = this.formatDocumentType(value);
                } else if (key === 'collection') {
                    displayValue = value || 'Default';
                } else if (typeof value === 'object') {
                    displayValue = JSON.stringify(value);
                } else {
                    displayValue = String(value);
                }
                
                tags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">${this.escapeHtml(this.formatMetadataKey(key))}</span>
                        <span class="tag-value">${this.escapeHtml(displayValue)}</span>
                    </div>
                `);
            }
        });
        
        return tags.join('');
    }

    formatDocumentType(type) {
        if (!type) return 'Unknown';
        
        const typeMap = {
            'webpage': 'URL',
            'pdf': 'PDF',
            'docx': 'DOCX',
            'txt': 'Text',
            'json': 'JSON',
            'xml': 'XML',
            'csv': 'CSV'
        };
        
        return typeMap[type.toLowerCase()] || type.charAt(0).toUpperCase() + type.slice(1);
    }

    formatMetadataKey(key) {
        const keyMap = {
            'type': 'Type',
            'collection': 'Collection',
            'url': 'URL',
            'filename': 'Filename',
            'source': 'Source',
            'category': 'Category'
        };
        
        return keyMap[key] || key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
    }

    formatContentPreview(text) {
        if (!text) {
            return '<div class="no-content">No content available</div>';
        }
        
        // Clean and format the text
        let formattedText = text
            .replace(/\n\s*\n/g, '\n\n') // Remove extra blank lines
            .replace(/\t/g, '    ') // Replace tabs with spaces
            .trim();
        
        // Limit to first 1000 characters with ellipsis
        const maxLength = 1000;
        const truncated = formattedText.length > maxLength;
        const displayText = truncated ? formattedText.substring(0, maxLength) + '...' : formattedText;
        
        // Split into paragraphs and format
        const paragraphs = displayText.split('\n\n').map(para => 
            `<p>${this.escapeHtml(para.trim())}</p>`
        ).join('');
        
        return `
            <div class="content-text">
                ${paragraphs}
                ${truncated ? '<div class="content-truncated">Content truncated for preview</div>' : ''}
            </div>
        `;
    }

    toggleVisualization() {
        const visualization = document.getElementById('visualizationContent');
        const toggleBtn = document.getElementById('visualizationToggleBtn');
        
        this.isVisualizationVisible = !this.isVisualizationVisible;
        
        if (this.isVisualizationVisible) {
            visualization.style.display = 'flex';
            toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
            
            // D3.js is now loaded synchronously, so we can call updateVisualization immediately
            this.updateVisualization();
        } else {
            visualization.style.display = 'none';
            toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';
        }
    }

    updateVisualization() {
        console.log('updateVisualization called - isVisible:', this.isVisualizationVisible, 'documents:', this.documents.length);
        
        // Always update the visualization data, even if not visible
        // This ensures the visualization is ready when made visible
        if (this.documents.length === 0) {
            console.log('No documents to visualize');
            return;
        }

        const container = document.getElementById('visualizationContent');
        if (!container) {
            console.error('Visualization container not found');
            return;
        }

        // D3.js is now loaded synchronously, so it should always be available
        if (typeof d3 === 'undefined') {
            console.error('D3.js not available despite being loaded in HTML head');
            container.innerHTML = `
                <div style="text-align: center; color: #666; padding: 2rem;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; opacity: 0.5; margin-bottom: 1rem;"></i>
                    <p>Visualization Error</p>
                    <p style="font-size: 0.8rem; margin-top: 0.5rem;">D3.js library not loaded. Please refresh the page.</p>
                </div>
            `;
            return;
        }

        try {
            console.log('Creating D3.js visualization...');
            
            // Get container dimensions as they currently are (no forced resizing)
            const containerRect = container.getBoundingClientRect();
            const containerWidth = containerRect.width;
            const containerHeight = containerRect.height;
            
            // Ensure minimum dimensions but don't force larger sizes
            const minWidth = 200;
            const minHeight = 150;
            const finalWidth = Math.max(containerWidth, minWidth);
            const finalHeight = Math.max(containerHeight, minHeight);
            
            console.log('Container dimensions (current):', finalWidth, 'x', finalHeight);
            console.log('Container rect:', containerRect);
            
            // Prepare data based on visualization type
            let data;
            switch (this.currentVisualizationType) {
                case 'bar':
                    data = this.prepareBarChartData();
                    console.log('Bar chart data:', data);
                    this.createBarChart(container, data, finalWidth, finalHeight);
                    break;
                case 'pie':
                    data = this.preparePieChartData();
                    console.log('Pie chart data:', data);
                    this.createPieChart(container, data, finalWidth, finalHeight);
                    break;
                case 'graph':
                    data = this.prepareGraphData();
                    console.log('Graph data:', data);
                    this.createNetworkGraph(container, data, finalWidth, finalHeight);
                    break;
                default:
                    data = this.prepareBarChartData();
                    console.log('Default bar chart data:', data);
                    this.createBarChart(container, data, finalWidth, finalHeight);
            }
            
        } catch (error) {
            console.error('Error creating visualization:', error);
            container.innerHTML = `
                <div style="text-align: center; color: #666; padding: 2rem;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; opacity: 0.5; margin-bottom: 1rem;"></i>
                    <p>Visualization Error</p>
                    <p style="font-size: 0.8rem; margin-top: 0.5rem;">Could not create chart: ${error.message}</p>
                </div>
            `;
        }
    }

    prepareBarChartData() {
        // Group documents by type
        const typeCounts = {};
        this.documents.forEach(doc => {
            const type = doc.metadata?.type || 'unknown';
            typeCounts[type] = (typeCounts[type] || 0) + 1;
        });
        
        return Object.entries(typeCounts).map(([type, count]) => ({
            type: this.formatDocumentType(type),
            count: count
        }));
    }

    preparePieChartData() {
        // Group documents by type for pie chart
        const typeCounts = {};
        this.documents.forEach(doc => {
            const type = doc.metadata?.type || 'unknown';
            typeCounts[type] = (typeCounts[type] || 0) + 1;
        });
        
        return Object.entries(typeCounts).map(([type, count]) => ({
            type: this.formatDocumentType(type),
            count: count
        }));
    }

    prepareGraphData() {
        // Group documents first to handle existing chunked documents
        const groupedDocuments = this.groupDocumentsByBaseUrl(this.documents);
        
        // Create nodes for each grouped document
        const nodes = groupedDocuments.map((doc, index) => {
            // For chunked documents, use the original filename as the name
            let displayName = doc.url || `Document ${index + 1}`;
            
            if (doc.metadata?.is_chunked && doc.metadata?.original_filename) {
                displayName = doc.metadata.original_filename;
            } else if (doc.isGroupedChunks && doc.originalFilename) {
                displayName = doc.originalFilename;
            } else if (doc.metadata?.filename) {
                displayName = doc.metadata.filename;
            }
            
            return {
                id: doc.id || index,
                name: displayName,
                type: doc.metadata?.type || 'unknown',
                group: doc.metadata?.collection || 'default',
                isChunked: (doc.metadata?.is_chunked || doc.isGroupedChunks) || false,
                totalChunks: doc.metadata?.total_chunks || doc.totalChunks || 1
            };
        });
        
        const edges = [];
        // Create edges between documents with similar metadata
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const node1 = nodes[i];
                const node2 = nodes[j];
                
                // Create edge if they share the same type or collection
                if (node1.type === node2.type || node1.group === node2.group) {
                    edges.push({
                        source: node1.id,
                        target: node2.id,
                        value: node1.type === node2.type ? 2 : 1 // Higher weight for same type
                    });
                }
            }
        }
        
        return { nodes, edges };
    }

    createBarChart(container, data, width, height) {
        const margin = { top: 20, right: 20, bottom: 60, left: 60 };
        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;

        // Clear container
        container.innerHTML = '';

        // Create SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const chart = svg.append('g')
            .attr('transform', `translate(${margin.left}, ${margin.top})`);

        // Scales
        const xScale = d3.scaleBand()
            .domain(data.map(d => d.type))
            .range([0, chartWidth])
            .padding(0.1);

        const yScale = d3.scaleLinear()
            .domain([0, d3.max(data, d => d.count)])
            .range([chartHeight, 0]);

        // Color scale
        const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

        // Add bars
        chart.selectAll('.bar')
            .data(data)
            .enter()
            .append('rect')
            .attr('class', 'bar')
            .attr('x', d => xScale(d.type))
            .attr('y', d => yScale(d.count))
            .attr('width', xScale.bandwidth())
            .attr('height', d => chartHeight - yScale(d.count))
            .attr('fill', (d, i) => colorScale(i))
            .attr('rx', 4)
            .attr('ry', 4);

        // Add value labels on bars
        chart.selectAll('.bar-label')
            .data(data)
            .enter()
            .append('text')
            .attr('class', 'bar-label')
            .attr('x', d => xScale(d.type) + xScale.bandwidth() / 2)
            .attr('y', d => yScale(d.count) - 5)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#333')
            .text(d => d.count);

        // Add axes
        const xAxis = d3.axisBottom(xScale);
        const yAxis = d3.axisLeft(yScale);

        chart.append('g')
            .attr('transform', `translate(0, ${chartHeight})`)
            .call(xAxis)
            .selectAll('text')
            .attr('transform', 'rotate(-45)')
            .attr('text-anchor', 'end')
            .attr('font-size', '10px');

        chart.append('g')
            .call(yAxis)
            .attr('font-size', '10px');

        // Add axis labels
        chart.append('text')
            .attr('x', chartWidth / 2)
            .attr('y', chartHeight + margin.bottom - 10)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#666')
            .text('Document Type');

        chart.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -chartHeight / 2)
            .attr('y', -margin.left + 20)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#666')
            .text('Count');
    }

    createPieChart(container, data, width, height) {
        const radius = Math.min(width, height) / 2 - 40;
        const centerX = width / 2;
        const centerY = height / 2;

        // Clear container
        container.innerHTML = '';

        // Create SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const chart = svg.append('g')
            .attr('transform', `translate(${centerX}, ${centerY})`);

        // Create pie generator
        const pie = d3.pie()
            .value(d => d.count)
            .sort(null);

        const arc = d3.arc()
            .innerRadius(0)
            .outerRadius(radius);

        const outerArc = d3.arc()
            .innerRadius(radius * 0.9)
            .outerRadius(radius * 0.9);

        // Color scale
        const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

        // Create pie slices
        const slices = chart.selectAll('.slice')
            .data(pie(data))
            .enter()
            .append('g')
            .attr('class', 'slice');

        slices.append('path')
            .attr('d', arc)
            .attr('fill', (d, i) => colorScale(i))
            .attr('stroke', 'white')
            .attr('stroke-width', 2);

        // Add labels
        slices.append('text')
            .attr('transform', d => `translate(${arc.centroid(d)})`)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', 'white')
            .attr('font-weight', 'bold')
            .text(d => d.data.count);

        // Add legend
        const legend = svg.append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${width - 150}, 20)`);

        legend.selectAll('.legend-item')
            .data(data)
            .enter()
            .append('g')
            .attr('class', 'legend-item')
            .attr('transform', (d, i) => `translate(0, ${i * 20})`);

        legend.selectAll('.legend-item')
            .append('rect')
            .attr('width', 12)
            .attr('height', 12)
            .attr('fill', (d, i) => colorScale(i));

        legend.selectAll('.legend-item')
            .append('text')
            .attr('x', 20)
            .attr('y', 9)
            .attr('font-size', '11px')
            .attr('fill', '#333')
            .text(d => `${d.type} (${d.count})`);
    }

    createNetworkGraph(container, data, width, height) {
        const { nodes, edges } = data;

        // Clear container
        container.innerHTML = '';

        // Create SVG with full container dimensions
        const svg = d3.select(container)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .style('display', 'block');

        // Create force simulation with better parameters for the available space
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(edges).id(d => d.id).distance(Math.min(150, width / 4)))
            .force('charge', d3.forceManyBody().strength(-Math.min(500, width * 2)))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(Math.min(25, Math.min(width, height) / 10)));

        // Color scale for node types
        const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

        // Create links
        const links = svg.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(edges)
            .enter()
            .append('line')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.max(1, Math.sqrt(d.value || 1)));

        // Create nodes
        const node = svg.append('g')
            .attr('class', 'nodes')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', 'node')
            .style('cursor', 'pointer') // Add pointer cursor to indicate clickable
            .call(d3.drag()
                .on('start', this.dragstarted.bind(this))
                .on('drag', this.dragged.bind(this))
                .on('end', this.dragended.bind(this)))
            .on('click', (event, d) => {
                // Handle node click to scroll to document in list
                this.scrollToDocumentInList(d.id);
            });

        // Add circles to nodes with adaptive sizing
        const nodeRadius = Math.min(12, Math.min(width, height) / 20);
        node.append('circle')
            .attr('r', nodeRadius)
            .attr('fill', d => colorScale(d.type))
            .attr('stroke', 'white')
            .attr('stroke-width', 2);

        // Add labels to nodes with adaptive font sizing
        const fontSize = Math.max(8, Math.min(width, height) / 50);
        node.append('text')
            .attr('dx', nodeRadius + 4)
            .attr('dy', '.35em')
            .attr('font-size', `${fontSize}px`)
            .attr('fill', '#333')
            .text(d => {
                const maxLength = Math.max(10, width / 20);
                let displayText = d.name;
                
                // Add chunk information for chunked documents
                if (d.isChunked && d.totalChunks > 1) {
                    displayText += ` (${d.totalChunks} chunks)`;
                }
                
                return displayText.length > maxLength ? displayText.substring(0, maxLength) + '...' : displayText;
            });

        // Update positions on simulation tick
        simulation.on('tick', () => {
            links
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('transform', d => `translate(${d.x}, ${d.y})`);
        });

        // Add zoom behavior for better interaction
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                svg.selectAll('g').attr('transform', event.transform);
            });

        svg.call(zoom);

        // Add legend if there are multiple node types
        const nodeTypes = [...new Set(nodes.map(n => n.type))];
        if (nodeTypes.length > 1) {
            const legend = svg.append('g')
                .attr('class', 'legend')
                .attr('transform', `translate(20, 20)`);

            legend.selectAll('.legend-item')
                .data(nodeTypes)
                .enter()
                .append('g')
                .attr('class', 'legend-item')
                .attr('transform', (d, i) => `translate(0, ${i * 20})`);

            legend.selectAll('.legend-item')
                .append('circle')
                .attr('r', 6)
                .attr('fill', (d, i) => colorScale(i));

            legend.selectAll('.legend-item')
                .append('text')
                .attr('x', 15)
                .attr('y', 4)
                .attr('font-size', `${Math.max(10, fontSize)}px`)
                .attr('fill', '#333')
                .text(d => d);
        }
    }

    dragstarted(event, d) {
        if (!event.active) this.currentSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragended(event, d) {
        if (!event.active) this.currentSimulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    showNotification(type, message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 4000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            max-width: 300px;
        `;

        // Set background color based on type
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            info: '#3b82f6',
            warning: '#f59e0b'
        };
        notification.style.backgroundColor = colors[type] || colors.info;

        notification.textContent = message;
        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    loadVectorDbInfo() {
        this.socket.emit('get_vector_db_info');
    }

    updateVectorDbInfoDisplay() {
        const vectorDbInfoElement = document.getElementById('vectorDbInfo');
        const vectorDbTypeElement = document.getElementById('vectorDbType');
        const vectorDbCollectionElement = document.getElementById('vectorDbCollection');
        
        if (!this.settings.showVectorDbInfo) {
            vectorDbInfoElement.style.display = 'none';
            return;
        }
        
        if (this.vectorDbInfo) {
            vectorDbTypeElement.textContent = this.vectorDbInfo.dbType || 'Unknown';
            vectorDbCollectionElement.textContent = this.vectorDbInfo.collectionName || 'Unknown';
            vectorDbInfoElement.style.display = 'flex';
        } else {
            vectorDbTypeElement.textContent = 'Loading...';
            vectorDbCollectionElement.textContent = 'Loading...';
            vectorDbInfoElement.style.display = 'flex';
        }
    }

    deleteDocument(docIndex) {
        if (confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
            const doc = this.documents[docIndex];
            console.log('Deleting document:', docIndex, doc);
            
            // Check if this is a chunked document that needs special handling
            if (doc.isGroupedChunks && doc.totalChunks > 1) {
                // Delete all chunks of this document
                this.deleteChunkedDocument(doc);
            } else {
                // Delete single document
                this.deleteSingleDocument(docIndex, doc);
            }
        }
    }

    deleteChunkedDocument(groupedDoc) {
        console.log('Deleting chunked document:', groupedDoc);
        
        // Get all chunks that belong to this document
        const chunksToDelete = this.documents.filter(doc => {
            if (doc.metadata?.is_chunk && doc.metadata?.total_chunks) {
                // Extract base URL from chunk URL
                const chunkBaseUrl = doc.url.split('#')[0];
                const groupBaseUrl = groupedDoc.baseUrl;
                return chunkBaseUrl === groupBaseUrl;
            }
            return false;
        });
        
        console.log('Found chunks to delete:', chunksToDelete.length);
        
        // Delete all chunks
        const deletePromises = chunksToDelete.map(chunk => 
            fetch(`/delete-document/${chunk.id}`, { method: 'DELETE' })
                .then(response => response.json())
        );
        
        Promise.all(deletePromises)
            .then(results => {
                const successCount = results.filter(result => result.status === 'success').length;
                const totalCount = results.length;
                
                if (successCount === totalCount) {
                    // Remove all chunks from local array
                    chunksToDelete.forEach(chunk => {
                        const index = this.documents.findIndex(doc => doc.id === chunk.id);
                        if (index !== -1) {
                            this.documents.splice(index, 1);
                        }
                    });
                    
                    console.log(`Deleted ${successCount} chunks. New document count:`, this.documents.length);
                    
                    // Re-render the documents list
                    this.renderDocuments();
                    
                    // Update visualization to reflect the changes
                    this.updateVisualization();
                    
                    // Show success notification
                    this.showNotification('success', `Deleted document with ${successCount} chunks successfully`);
                } else {
                    this.showNotification('error', `Failed to delete some chunks. Deleted ${successCount}/${totalCount}`);
                }
            })
            .catch(error => {
                console.error('Error deleting chunked document:', error);
                this.showNotification('error', 'Failed to delete chunked document. Please try again.');
            });
    }

    deleteSingleDocument(docIndex, doc) {
        // Call backend API to delete the document using the document ID
        fetch(`/delete-document/${doc.id}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(result => {
            console.log('Delete result:', result);
            if (result.status === 'success') {
                // Remove from local array
                this.documents.splice(docIndex, 1);
                console.log('Document removed from local array. New count:', this.documents.length);
                
                // Re-render the documents list
                this.renderDocuments();
                
                // Update visualization to reflect the changes
                this.updateVisualization();
                
                // Show success notification
                this.showNotification('success', 'Document deleted successfully');
            } else {
                // Show error notification
                this.showNotification('error', result.message || 'Failed to delete document');
            }
        })
        .catch(error => {
            console.error('Error deleting document:', error);
            this.showNotification('error', 'Failed to delete document. Please try again.');
        });
    }

    deleteDocumentFromDetails() {
        const modal = document.getElementById('documentDetailsModal');
        const docIndex = parseInt(modal.dataset.docIndex);
        
        if (isNaN(docIndex) || docIndex < 0 || docIndex >= this.documents.length) {
            this.showNotification('error', 'Invalid document index');
            return;
        }

        const doc = this.documents[docIndex];
        
        if (confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
            // Check if this is a chunked document that needs special handling
            if (doc.isGroupedChunks && doc.totalChunks > 1) {
                // Delete all chunks of this document
                this.deleteChunkedDocument(doc);
            } else {
                // Delete single document
                this.deleteSingleDocument(docIndex, doc);
            }
            
            // Close the modal
            this.hideModal('documentDetailsModal');
        }
    }

    scrollToDocumentInList(documentId) {
        console.log('Scrolling to document in list:', documentId);
        
        // Find the document in the documents array
        const docIndex = this.documents.findIndex(doc => doc.id === documentId);
        if (docIndex === -1) {
            console.warn('Document not found in list:', documentId);
            return;
        }

        // Get the document list container
        const documentsContainer = document.querySelector('.documents-list-container');
        if (!documentsContainer) {
            console.error('Documents list container not found');
            return;
        }

        // Get all document cards
        const documentCards = documentsContainer.querySelectorAll('.document-card');
        if (docIndex >= documentCards.length) {
            console.warn('Document card not found at index:', docIndex);
            return;
        }

        // Remove any existing highlight
        documentCards.forEach(card => {
            card.classList.remove('highlighted');
        });

        // Get the target document card
        const targetCard = documentCards[docIndex];
        
        // Add highlight class
        targetCard.classList.add('highlighted');
        
        // Scroll to the card with smooth animation
        targetCard.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });

        // Remove highlight after a few seconds
        setTimeout(() => {
            targetCard.classList.remove('highlighted');
        }, 3000);

        // Show a brief notification
        const doc = this.documents[docIndex];
        const docName = doc.url || doc.metadata?.filename || `Document ${docIndex + 1}`;
        this.showNotification('info', `Scrolled to: ${docName}`);
    }

    groupDocumentsByBaseUrl(documents) {
        const groups = {};
        
        documents.forEach((doc, index) => {
            // Check if this is an existing chunked document (is_chunk) or new chunked document (is_chunked)
            if ((doc.metadata?.is_chunk && doc.metadata?.total_chunks) || 
                (doc.metadata?.is_chunked && doc.metadata?.total_chunks)) {
                
                // Extract base filename from URL like "file://ragme-ai.pdf#chunk-4"
                const url = doc.url || '';
                const baseUrl = url.split('#')[0]; // Remove chunk suffix
                
                if (!groups[baseUrl]) {
                    groups[baseUrl] = {
                        isGroupedChunks: true,
                        totalChunks: doc.metadata.total_chunks,
                        originalFilename: doc.metadata.filename,
                        baseUrl: baseUrl,
                        chunks: [],
                        metadata: { ...doc.metadata },
                        url: baseUrl,
                        id: doc.id,
                        docIndex: index
                    };
                }
                
                groups[baseUrl].chunks.push({
                    ...doc,
                    chunkIndex: doc.metadata.chunk_index
                });
                
                // Sort chunks by index
                groups[baseUrl].chunks.sort((a, b) => a.chunkIndex - b.chunkIndex);
                
                // Combine text from all chunks
                groups[baseUrl].combinedText = groups[baseUrl].chunks
                    .map(chunk => chunk.text)
                    .join('\n\n--- Chunk ---\n\n');
                
                // Use the earliest date
                if (!groups[baseUrl].metadata.date_added || 
                    doc.metadata.date_added < groups[baseUrl].metadata.date_added) {
                    groups[baseUrl].metadata.date_added = doc.metadata.date_added;
                }
            } else {
                // Regular document - use URL as key, but ensure unique keys for different document types
                let key = doc.url || `doc_${index}`;
                
                // For URLs, use the full URL as key
                if (doc.url && (doc.url.startsWith('http://') || doc.url.startsWith('https://'))) {
                    key = doc.url;
                }
                // For file documents, use the filename as key
                else if (doc.metadata?.filename) {
                    key = `file://${doc.metadata.filename}`;
                }
                // For other documents, use a unique key
                else {
                    key = `doc_${index}_${Date.now()}`;
                }
                
                groups[key] = {
                    ...doc,
                    docIndex: index
                };
            }
        });
        
        // Convert groups object to array
        return Object.values(groups);
    }

    retryQuery(query) {
        // Set the query in the input field
        const inputField = document.getElementById('chatInput');
        if (inputField) {
            inputField.value = query;
        }
        
        // Directly send the message
        this.sendMessage();
        
        // Show notification
        this.showNotification('info', 'Retrying query...');
    }

    saveMessageAsFile(message) {
        // Find the user message that generated this AI response
        const userMessage = this.findUserMessageForResponse(message);
        let filename = 'ragme-response.md';
        
        if (userMessage) {
            // Create filename from first three words of the query
            const words = userMessage.content.trim().split(/\s+/).slice(0, 3);
            if (words.length > 0) {
                filename = words.join('-').toLowerCase().replace(/[^a-z0-9-]/g, '') + '.md';
            }
        }
        
        // Create the file content
        const fileContent = `# RAGme.ai Response

${userMessage ? `**Query:** ${userMessage.content}

` : ''}**Response:**

${message.content}

---
*Generated by RAGme.ai Assistant on ${new Date().toLocaleString()}*
`;

        // Create and download the file
        const blob = new Blob([fileContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('success', `Response saved as ${filename}`);
    }

    findUserMessageForResponse(aiMessage) {
        // Find the most recent user message before this AI message
        const messageIndex = this.chatHistory.findIndex(m => m.id === aiMessage.id);
        if (messageIndex > 0) {
            for (let i = messageIndex - 1; i >= 0; i--) {
                if (this.chatHistory[i].type === 'user') {
                    return this.chatHistory[i];
                }
            }
        }
        return null;
    }

    showEmailModal(message) {
        // Find the user message that generated this AI response
        const userMessage = this.findUserMessageForResponse(message);
        
        // Set the subject and body
        const subjectInput = document.getElementById('emailSubject');
        const bodyInput = document.getElementById('emailBody');
        const toInput = document.getElementById('emailTo');
        
        if (userMessage) {
            subjectInput.value = userMessage.content.substring(0, 50) + (userMessage.content.length > 50 ? '...' : '');
        } else {
            subjectInput.value = 'RAGme.ai Response';
        }
        
        bodyInput.value = message.content;
        toInput.value = '';
        
        // Show the modal
        this.showModal('emailModal');
    }

    sendEmail() {
        const toInput = document.getElementById('emailTo');
        const subjectInput = document.getElementById('emailSubject');
        const bodyInput = document.getElementById('emailBody');
        
        const to = toInput.value.trim();
        const subject = subjectInput.value;
        const body = bodyInput.value;
        
        if (!to) {
            this.showNotification('error', 'Please enter a recipient email address');
            return;
        }
        
        // Create mailto link
        const mailtoLink = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        
        // Open default email client
        window.open(mailtoLink);
        
        // Hide modal and show success notification
        this.hideModal('emailModal');
        this.showNotification('success', 'Email client opened with your message');
    }

    saveChatAsFile(chat) {
        // Create filename from chat title
        let filename = 'ragme-chat.md';
        
        if (chat.title) {
            // Create filename from first three words of the title
            const words = chat.title.trim().split(/\s+/).slice(0, 3);
            if (words.length > 0) {
                filename = words.join('-').toLowerCase().replace(/[^a-z0-9-]/g, '') + '.md';
            }
        }
        
        // Create the file content with entire conversation
        let fileContent = `# RAGme.ai Chat: ${chat.title}

**Chat ID:** ${chat.id}  
**Created:** ${new Date(chat.createdAt).toLocaleString()}  
**Updated:** ${new Date(chat.updatedAt).toLocaleString()}

---

`;

        // Add all messages from the conversation
        if (chat.messages && chat.messages.length > 0) {
            chat.messages.forEach((message, index) => {
                const timestamp = message.timestamp ? new Date(message.timestamp).toLocaleString() : '';
                const role = message.type === 'user' ? '👤 User' : '🤖 AI';
                
                fileContent += `## ${role}${timestamp ? ` (${timestamp})` : ''}

${message.content}

---
`;
            });
        } else {
            fileContent += `*No messages in this conversation*

`;
        }

        fileContent += `---
*Generated by RAGme.ai Assistant on ${new Date().toLocaleString()}*
`;

        // Create and download the file
        const blob = new Blob([fileContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('success', `Chat saved as ${filename}`);
    }

    showChatEmailModal(chat) {
        // Set the subject and body
        const subjectInput = document.getElementById('emailSubject');
        const bodyInput = document.getElementById('emailBody');
        const toInput = document.getElementById('emailTo');
        
        // Use chat title as subject
        subjectInput.value = chat.title || 'RAGme.ai Chat';
        
        // Create email body with entire conversation
        let emailBody = `RAGme.ai Chat: ${chat.title}

Chat ID: ${chat.id}
Created: ${new Date(chat.createdAt).toLocaleString()}
Updated: ${new Date(chat.updatedAt).toLocaleString()}

---

`;

        // Add all messages from the conversation
        if (chat.messages && chat.messages.length > 0) {
            chat.messages.forEach((message, index) => {
                const timestamp = message.timestamp ? new Date(message.timestamp).toLocaleString() : '';
                const role = message.type === 'user' ? 'User' : 'AI';
                
                emailBody += `${role}${timestamp ? ` (${timestamp})` : ''}:
${message.content}

---
`;
            });
        } else {
            emailBody += `No messages in this conversation

`;
        }

        emailBody += `---
Generated by RAGme.ai Assistant on ${new Date().toLocaleString()}`;
        
        bodyInput.value = emailBody;
        toInput.value = '';
        
        // Show the modal
        this.showModal('emailModal');
    }

    // Function to detect if text is truncated and add tooltip if needed
    checkTextTruncation(element) {
        if (!element) return;
        
        // Force a reflow to get accurate measurements
        element.offsetHeight;
        
        // For document titles, check the document-title-text span
        if (element.classList.contains('document-title')) {
            const titleTextSpan = element.querySelector('.document-title-text');
            if (titleTextSpan) {
                const isTruncated = titleTextSpan.scrollWidth > titleTextSpan.clientWidth;
                if (isTruncated) {
                    element.classList.add('truncated');
                    // Clear any existing title attribute to prevent tooltip interference
                    element.title = '';
                    console.log('Document title truncated:', titleTextSpan.textContent || titleTextSpan.innerText);
                } else {
                    element.classList.remove('truncated');
                    element.title = '';
                }
            }
        } else {
            // For other elements like detail-value
            const isTruncated = element.scrollWidth > element.clientWidth;
            if (isTruncated) {
                element.classList.add('truncated');
                element.title = element.textContent || element.innerText;
                console.log('Element truncated:', element.textContent || element.innerText);
            } else {
                element.classList.remove('truncated');
                element.title = '';
            }
        }
    }

    // Function to check all document titles for truncation
    checkDocumentTitlesTruncation() {
        const documentTitles = document.querySelectorAll('.document-title');
        console.log('Checking', documentTitles.length, 'document titles for truncation');
        
        documentTitles.forEach((title, index) => {
            const titleTextSpan = title.querySelector('.document-title-text');
            console.log('Checking title', index, ':', titleTextSpan ? (titleTextSpan.textContent || titleTextSpan.innerText) : 'No title text span');
            this.checkTextTruncation(title);
        });
    }

    // Function to check all detail values for truncation
    checkDetailValuesTruncation() {
        const detailValues = document.querySelectorAll('.detail-value');
        console.log('Checking', detailValues.length, 'detail values for truncation');
        
        detailValues.forEach((value, index) => {
            console.log('Checking detail value', index, ':', value.textContent || value.innerText);
            this.checkTextTruncation(value);
        });
    }
}

// Simple markdown parser fallback if marked is not available
function simpleMarkdownParser(text) {
    if (typeof marked !== 'undefined') {
        return marked.parse(text);
    }
    
    // Fallback simple markdown parser
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
        .replace(/\n/g, '<br>');
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for external scripts to load
    setTimeout(() => {
        new RAGmeAssistant();
    }, 100);
}); 