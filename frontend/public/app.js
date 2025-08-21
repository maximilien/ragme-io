// RAGme.io Assistant Frontend JavaScript
class RAGmeAssistant {
    constructor() {
        this.socket = null;
        this.documents = [];
        this.chatHistory = [];
        this.chatSessions = [];
        this.currentChatId = null;
        // Default settings - will be overridden by configuration
        this.settings = {
            maxDocuments: 50,
            autoRefresh: true,
            refreshInterval: 30000, // 30 seconds
            maxTokens: 4000,
            temperature: 0.7,
            showVectorDbInfo: true,
            documentOverviewEnabled: true,
            documentOverviewVisible: true,
            documentListCollapsed: false,
            documentListWidth: 35,
            chatHistoryCollapsed: false,
            chatHistoryWidth: 10,
            maxDisplayDocuments: 100,
            paginationSize: 20,
            chatHistoryLimit: 50,
            autoSaveChats: true
        };
        this.currentDateFilter = 'current';
        this.currentContentFilter = 'both'; // Default to show both documents and images
        this.currentVisualizationType = 'graph'; // Default to Network Graph
        this.isVisualizationVisible = true; // Default to visible
        this.vectorDbInfo = null;
        this.autoRefreshInterval = null;
        this.lastDocumentCount = 0;
        this.connectionStatus = {
            isConnected: true,
            lastSuccess: Date.now(),
            failureCount: 0,
            lastFailure: null
        };
        this.documentDetailsModal = {
            isOpen: false,
            currentDocId: null,
            summaryGenerated: false,
            summaryInProgress: false
        };
        
        // Default MCP Tools configuration - will be overridden by configuration
        this.mcpServers = [
            { name: 'Google GDrive', icon: 'fab fa-google-drive', enabled: false, authenticated: false },
            { name: 'Dropbox Drive', icon: 'fab fa-dropbox', enabled: false, authenticated: false },
            { name: 'Google Mail', icon: 'fas fa-envelope', enabled: false, authenticated: false },
            { name: 'Twilio', icon: 'fas fa-phone', enabled: false, authenticated: false },
            { name: 'RAGme Test', icon: 'fas fa-flask', enabled: false, authenticated: false }
        ];
        
        // Configuration loaded from backend
        this.config = null;
        
        // Track pending MCP server changes for batching
        this.pendingMcpChanges = [];
        this.mcpChangeTimeout = null;
        
        // Vector DB info retry timeout
        this.vectorDbInfoRetryTimeout = null;
        
        // Voice-to-text functionality
        this.speechRecognition = null;
        this.isRecording = false;
        this.speechSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        
        this.init();
    }

    async init() {
        // Load configuration first
        await this.loadConfiguration();
        
        this.connectSocket();
        this.setupEventListeners();
        this.setupResizeDivider();
        this.setupVisualizationResize();
        this.loadSettings();
        
        // Apply UI configuration after loading both config and localStorage settings
        // Use a small delay to ensure DOM elements are ready
        setTimeout(() => {
            console.log('Applying UI configuration...');
            this.applyUIConfiguration();
        }, 50);
        
        this.loadChatSessions();
        this.renderChatHistory(); // Render chat history after loading
        this.loadVectorDbInfo();
        this.startAutoRefresh();
        
        // Initialize visualization after settings are loaded
        // This ensures the visualization type selector reflects the saved preference
        setTimeout(() => {
            this.updateVisualization();
        }, 100);
    }

    async loadConfiguration() {
        try {
            const response = await fetch('/api/config');
            if (response.ok) {
                this.config = await response.json();
                console.log('Configuration loaded:', this.config);
                
                // Update settings from configuration
                if (this.config.frontend && this.config.frontend.settings) {
                    const configSettings = this.config.frontend.settings;
                    this.settings = {
                        maxDocuments: configSettings.max_documents || this.settings.maxDocuments,
                        autoRefresh: configSettings.auto_refresh !== undefined ? configSettings.auto_refresh : this.settings.autoRefresh,
                        refreshInterval: configSettings.refresh_interval_ms || this.settings.refreshInterval,
                        maxTokens: configSettings.max_tokens || this.settings.maxTokens,
                        temperature: configSettings.temperature || this.settings.temperature
                    };
                }
                
                // Update MCP servers from configuration
                if (this.config.mcp_servers && this.config.mcp_servers.length > 0) {
                    this.mcpServers = this.config.mcp_servers.map(server => ({
                        name: server.name,
                        icon: server.icon || 'fas fa-server',
                        enabled: server.enabled || false,
                        authenticated: false // Will be updated based on actual status
                    }));
                }
                
                // Update UI settings
                if (this.config.frontend && this.config.frontend.ui) {
                    const uiConfig = this.config.frontend.ui;
                    
                    // Basic UI settings
                    this.currentDateFilter = uiConfig.default_date_filter || this.currentDateFilter;
                    this.currentVisualizationType = uiConfig.default_visualization || this.currentVisualizationType;
                    this.isVisualizationVisible = uiConfig.visualization_visible !== undefined ? uiConfig.visualization_visible : this.isVisualizationVisible;
                    
                    // Vector DB info display
                    this.settings.showVectorDbInfo = uiConfig.show_vector_db_info !== undefined ? uiConfig.show_vector_db_info : this.settings.showVectorDbInfo;
                    
                    // Document list settings
                    this.settings.maxDocuments = uiConfig.max_documents || 10;
                    this.settings.documentOverviewEnabled = uiConfig.document_overview_enabled !== undefined ? uiConfig.document_overview_enabled : true;
                    this.settings.documentOverviewVisible = uiConfig.document_overview_visible !== undefined ? uiConfig.document_overview_visible : true;
                    this.settings.documentListCollapsed = uiConfig.document_list_collapsed !== undefined ? uiConfig.document_list_collapsed : false;
                    this.settings.documentListWidth = uiConfig.document_list_width || 35;
                    
                    console.log('Loaded UI settings from config:', {
                        maxDocuments: this.settings.maxDocuments,
                        documentOverviewEnabled: this.settings.documentOverviewEnabled,
                        documentOverviewVisible: this.settings.documentOverviewVisible,
                        documentListCollapsed: this.settings.documentListCollapsed,
                        chatHistoryCollapsed: this.settings.chatHistoryCollapsed
                    });
                    
                    // Chat History settings
                    this.settings.chatHistoryCollapsed = uiConfig.chat_history_collapsed !== undefined ? uiConfig.chat_history_collapsed : false;
                    this.settings.chatHistoryWidth = uiConfig.chat_history_width || 10;
                }
                
                // Update page title and branding
                if (this.config.application && this.config.application.title) {
                    document.title = this.config.application.title;
                    
                    // Update header title as well
                    const headerTitle = document.querySelector('.header .title');
                    if (headerTitle) {
                        headerTitle.textContent = this.config.application.title;
                    }
                }
                
                // Load vector DB info from backend
                this.loadVectorDbInfoFromBackend();
                
            } else {
                console.warn('Could not load configuration from server, using defaults');
            }
        } catch (error) {
            console.warn('Failed to load configuration:', error);
        }
    }

    applyUIConfiguration() {
        // Apply Vector DB info display setting
        this.updateVectorDbInfoDisplay();
        
        // Apply document list settings
        this.applyDocumentListSettings();
        
        // Apply chat history settings
        this.applyChatHistorySettings();
        
        // Apply document overview settings
        this.applyDocumentOverviewSettings();
    }

    applyDocumentListSettings() {
        const documentsSidebar = document.getElementById('documentsSidebar');
        if (!documentsSidebar) {
            console.warn('Documents sidebar element not found');
            return;
        }
        
        console.log('Applying document list settings:', {
            width: this.settings.documentListWidth,
            collapsed: this.settings.documentListCollapsed
        });
        
        // Apply width
        documentsSidebar.style.width = `${this.settings.documentListWidth}%`;
        console.log('Set documents sidebar width to:', `${this.settings.documentListWidth}%`);
        
        // Apply collapsed state
        if (this.settings.documentListCollapsed) {
            documentsSidebar.classList.add('collapsed');
            console.log('Documents sidebar collapsed');
            // Show restore button
            const restoreBtn = document.getElementById('restoreDocumentsBtn');
            if (restoreBtn) {
                restoreBtn.style.display = 'block';
            }
        } else {
            documentsSidebar.classList.remove('collapsed');
            console.log('Documents sidebar expanded');
            // Hide restore button
            const restoreBtn = document.getElementById('restoreDocumentsBtn');
            if (restoreBtn) {
                restoreBtn.style.display = 'none';
            }
        }
        
        // Ensure main content area fills the space when documents sidebar is collapsed
        const chatMainArea = document.querySelector('.chat-main-area');
        if (chatMainArea) {
            if (this.settings.documentListCollapsed) {
                chatMainArea.style.marginRight = '0';
            } else {
                chatMainArea.style.marginRight = '';
            }
        }
    }

    applyChatHistorySettings() {
        const chatHistorySidebar = document.getElementById('chatHistorySidebar');
        if (!chatHistorySidebar) {
            console.warn('Chat history sidebar element not found');
            return;
        }
        
        console.log('Applying chat history settings:', {
            width: this.settings.chatHistoryWidth,
            collapsed: this.settings.chatHistoryCollapsed
        });
        
        // Apply width
        chatHistorySidebar.style.width = `${this.settings.chatHistoryWidth}%`;
        console.log('Set chat history sidebar width to:', `${this.settings.chatHistoryWidth}%`);
        
        // Apply collapsed state
        if (this.settings.chatHistoryCollapsed) {
            chatHistorySidebar.classList.add('collapsed');
            console.log('Chat history sidebar collapsed');
            // Show restore button
            const restoreBtn = document.getElementById('restoreSidebarBtn');
            if (restoreBtn) {
                restoreBtn.style.display = 'block';
            }
        } else {
            chatHistorySidebar.classList.remove('collapsed');
            console.log('Chat history sidebar expanded');
            // Hide restore button
            const restoreBtn = document.getElementById('restoreSidebarBtn');
            if (restoreBtn) {
                restoreBtn.style.display = 'none';
            }
        }
        
        // Ensure chat main area fills the space when sidebar is collapsed
        const chatMainArea = document.querySelector('.chat-main-area');
        if (chatMainArea) {
            if (this.settings.chatHistoryCollapsed) {
                chatMainArea.style.marginLeft = '0';
            } else {
                chatMainArea.style.marginLeft = '';
            }
        }
    }

    applyDocumentOverviewSettings() {
        const visualization = document.getElementById('documentsVisualization');
        if (!visualization) {
            console.warn('Document visualization element not found');
            return;
        }
        
        console.log('Applying document overview settings:', {
            enabled: this.settings.documentOverviewEnabled,
            visible: this.settings.documentOverviewVisible
        });
        
        // Apply enabled/disabled state
        if (!this.settings.documentOverviewEnabled) {
            visualization.style.display = 'none';
            console.log('Document overview disabled - hiding completely');
            return;
        }
        
        visualization.style.display = 'block';
        
        // Apply visible/hidden state
        if (!this.settings.documentOverviewVisible) {
            visualization.classList.add('hidden');
            console.log('Document overview hidden - adding hidden class');
            // Update toggle button
            const toggleBtn = document.getElementById('visualizationToggleBtn');
            if (toggleBtn) {
                const icon = toggleBtn.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-eye';
                }
            }
        } else {
            visualization.classList.remove('hidden');
            console.log('Document overview visible - removing hidden class');
            // Update toggle button
            const toggleBtn = document.getElementById('visualizationToggleBtn');
            if (toggleBtn) {
                const icon = toggleBtn.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-eye-slash';
                }
            }
        }
    }

    // Debug method to clear localStorage settings
    clearLocalStorageSettings() {
        localStorage.removeItem('ragme-document-overview-visible');
        localStorage.removeItem('ragme-document-overview-enabled');
        localStorage.removeItem('ragme-document-list-collapsed');
        localStorage.removeItem('ragme-chat-history-collapsed');
        console.log('Cleared localStorage settings');
    }

    connectSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to RAGme.io Assistant server');
            // Update connection status
            this.connectionStatus.isConnected = true;
            this.connectionStatus.lastSuccess = Date.now();
            this.connectionStatus.failureCount = 0;
            this.connectionStatus.lastFailure = null;
            this.updateVectorDbInfoDisplay();
            
            // Load documents after connection is established
            this.loadDocuments();
            // Start auto-refresh every 30 seconds
            this.startAutoRefresh();
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from RAGme.io Assistant server');
            // Update connection status
            this.connectionStatus.isConnected = false;
            this.connectionStatus.lastFailure = Date.now();
            this.updateVectorDbInfoDisplay();
            
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
            console.log('Current date filter:', this.currentDateFilter);
            if (result.success) {
                this.documents = result.documents;
                console.log('Loaded documents:', this.documents.length);
                this.renderDocuments();
                this.updateVisualization();
                
                // Update connection status on success
                this.connectionStatus.isConnected = true;
                this.connectionStatus.lastSuccess = Date.now();
                this.connectionStatus.failureCount = 0;
                this.connectionStatus.lastFailure = null;
                this.updateVectorDbInfoDisplay();
            } else {
                console.error('Failed to list documents:', result.message);
                
                // Update connection status on failure
                this.connectionStatus.isConnected = false;
                this.connectionStatus.failureCount++;
                this.connectionStatus.lastFailure = Date.now();
                this.updateVectorDbInfoDisplay();
            }
        });

        this.socket.on('content_listed', (result) => {
            console.log('Content listed result:', result);
            console.log('Current filters - date:', this.currentDateFilter, 'content:', this.currentContentFilter);
            if (result.success) {
                console.log('Previous documents count:', this.documents.length);
                this.documents = result.items;
                console.log('New documents count:', this.documents.length);
                console.log('Documents after update:', this.documents.map(d => ({ id: d.id, url: d.url, content_type: d.content_type })));
                this.renderDocuments();
                this.updateVisualization();
                
                // Update connection status on success
                this.connectionStatus.isConnected = true;
                this.connectionStatus.lastSuccess = Date.now();
                this.connectionStatus.failureCount = 0;
                this.connectionStatus.lastFailure = null;
                this.updateVectorDbInfoDisplay();
            } else {
                console.error('Failed to list content:', result.message);
                
                // Update connection status on failure
                this.connectionStatus.isConnected = false;
                this.connectionStatus.failureCount++;
                this.connectionStatus.lastFailure = Date.now();
                this.updateVectorDbInfoDisplay();
            }
        });

        this.socket.on('vector_db_info', (result) => {
            if (result.success) {
                this.vectorDbInfo = result.info;
                // Clear any pending retry timeout
                if (this.vectorDbInfoRetryTimeout) {
                    clearTimeout(this.vectorDbInfoRetryTimeout);
                    this.vectorDbInfoRetryTimeout = null;
                }
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
            // Also close any open submenus
            const submenus = document.querySelectorAll('.submenu');
            const triggers = document.querySelectorAll('.submenu-trigger');
            submenus.forEach(submenu => submenu.classList.remove('show'));
            triggers.forEach(trigger => trigger.classList.remove('active'));
        });

        // Prevent submenu clicks from closing the main menu
        document.getElementById('manageChatsSubmenu').addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Menu items
        const manageChatsTrigger = document.getElementById('manageChatsTrigger');
        const manageChatsSubmenu = document.getElementById('manageChatsSubmenu');
        
        // Show/hide submenu on click
        manageChatsTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleSubmenu('manageChatsSubmenu', 'manageChatsTrigger');
        });

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

        // New chat button
        document.getElementById('newChatBtn').addEventListener('click', () => {
            this.createNewChat();
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

        // Content filter selector
        document.getElementById('contentFilterSelector').addEventListener('change', (e) => {
            console.log('Content filter changed to:', e.target.value);
            this.currentContentFilter = e.target.value;
            localStorage.setItem('ragme-content-filter', this.currentContentFilter);
            this.loadDocuments();
        });

        // Date filter selector
        document.getElementById('dateFilterSelector').addEventListener('change', (e) => {
            console.log('Date filter changed to:', e.target.value);
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

        // Microphone button
        const microphoneBtn = document.getElementById('microphoneBtn');
        microphoneBtn.addEventListener('click', () => {
            this.toggleVoiceInput();
        });

        // MCP Tools button
        const mcpToolsBtn = document.getElementById('mcpToolsBtn');
        
        mcpToolsBtn.addEventListener('click', (e) => {
            console.log('MCP Tools button clicked!');
            
            // Prevent the click from bubbling up to the document
            e.stopPropagation();
            
            this.toggleMcpToolsPopup();
        });

        // MCP Tools popup close handlers
        const mcpBackdrop = document.getElementById('mcpToolsBackdrop');
        const mcpCloseBtn = document.getElementById('mcpToolsClose');
        
        mcpBackdrop.addEventListener('click', () => {
            this.hideMcpToolsPopup();
        });
        
        mcpCloseBtn.addEventListener('click', () => {
            this.hideMcpToolsPopup();
        });

        // Recent prompts button
        const recentPromptsBtn = document.getElementById('recentPromptsBtn');
        const recentPromptsPopup = document.getElementById('recentPromptsPopup');
        
        recentPromptsBtn.addEventListener('click', (e) => {
            console.log('Recent prompts button clicked!');
            console.log('Button element:', recentPromptsBtn);
            console.log('Button visible:', recentPromptsBtn.offsetParent !== null);
            console.log('Button disabled:', recentPromptsBtn.disabled);
            
            // Prevent the click from bubbling up to the document
            e.stopPropagation();
            
            this.toggleRecentPromptsPopup();
        });

        // Close popup when clicking backdrop or close button
        const backdrop = document.getElementById('recentPromptsBackdrop');
        const closeBtn = document.getElementById('recentPromptsClose');
        
        backdrop.addEventListener('click', () => {
            this.hideRecentPromptsPopup();
        });
        
        closeBtn.addEventListener('click', () => {
            this.hideRecentPromptsPopup();
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
            // Reset modal state when closed
            this.documentDetailsModal.isOpen = false;
            this.documentDetailsModal.currentDocId = null;
            this.documentDetailsModal.summaryGenerated = false;
            this.documentDetailsModal.summaryInProgress = false;
        });

        // Add content modal
        document.getElementById('submitAddContent').addEventListener('click', () => {
            this.submitAddContent();
        });

        document.getElementById('cancelAddContent').addEventListener('click', () => {
            this.hideModal('addContentModal');
        });

        // MCP Servers menu item
        document.getElementById('mcpServers').addEventListener('click', () => {
            this.showMcpServersModal();
        });

        // MCP Servers modal
        document.getElementById('closeMcpServers').addEventListener('click', () => {
            this.hideModal('mcpServersModal');
        });

        document.getElementById('cancelMcpServers').addEventListener('click', () => {
            this.hideModal('mcpServersModal');
        });

        // Authentication modal
        document.getElementById('closeAuth').addEventListener('click', () => {
            this.hideModal('authModal');
        });

        document.getElementById('cancelAuth').addEventListener('click', () => {
            this.hideModal('authModal');
        });

        document.getElementById('confirmAuth').addEventListener('click', () => {
            this.confirmAuthentication();
        });

        // Settings modal
        document.getElementById('saveSettings').addEventListener('click', () => {
            this.saveSettings();
        });

        document.getElementById('cancelSettings').addEventListener('click', () => {
            this.hideModal('settingsModal');
        });

        document.getElementById('resetSettings').addEventListener('click', () => {
            this.resetSettings();
        });

        // Settings tabs
        document.querySelectorAll('.settings-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const tabName = e.target.closest('.settings-tab-btn').dataset.settingsTab;
                this.switchSettingsTab(tabName);
            });
        });

        // Range input updates
        document.getElementById('documentListWidth').addEventListener('input', (e) => {
            document.getElementById('documentListWidthValue').textContent = e.target.value + '%';
        });

        document.getElementById('chatHistoryWidth').addEventListener('input', (e) => {
            document.getElementById('chatHistoryWidthValue').textContent = e.target.value + '%';
        });

        document.getElementById('temperature').addEventListener('input', (e) => {
            document.getElementById('temperatureValue').textContent = e.target.value;
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
            localStorage.setItem('ragme-visualization-type', this.currentVisualizationType);
            // Always update visualization when type changes, regardless of visibility
            // This ensures the visualization is ready when made visible
            this.updateVisualization();
        });

        // Resize divider
        this.setupResizeDivider();

        // Document details modal close
        document.getElementById('closeDocumentDetailsBtn').addEventListener('click', () => {
            this.hideModal('documentDetailsModal');
            // Reset modal state when closed
            this.documentDetailsModal.isOpen = false;
            this.documentDetailsModal.currentDocId = null;
            this.documentDetailsModal.summaryGenerated = false;
            this.documentDetailsModal.summaryInProgress = false;
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
                    
                    // Reset document details modal state if it was closed
                    if (modalId === 'documentDetailsModal') {
                        this.documentDetailsModal.isOpen = false;
                        this.documentDetailsModal.currentDocId = null;
                        this.documentDetailsModal.summaryGenerated = false;
                        this.documentDetailsModal.summaryInProgress = false;
                    }
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

        toggleRecentPromptsPopup() {
        console.log('toggleRecentPromptsPopup called');
        const popup = document.getElementById('recentPromptsPopup');
        const button = document.getElementById('recentPromptsBtn');
        
        console.log('Popup element:', popup);
        console.log('Popup has show class:', popup.classList.contains('show'));
        console.log('Popup display style before toggle:', window.getComputedStyle(popup).display);
        console.log('Popup visibility before toggle:', window.getComputedStyle(popup).visibility);
        console.log('Popup opacity before toggle:', window.getComputedStyle(popup).opacity);
        
        if (popup.classList.contains('show')) {
            console.log('Hiding popup...');
            this.hideRecentPromptsPopup();
        } else {
            console.log('Showing popup...');
            this.showRecentPromptsPopup();
        }
    }

    showRecentPromptsPopup() {
        const popup = document.getElementById('recentPromptsPopup');
        const backdrop = document.getElementById('recentPromptsBackdrop');
        const button = document.getElementById('recentPromptsBtn');
        const list = document.getElementById('recentPromptsList');
        
        // Check if list element exists
        if (!list) {
            console.error('recentPromptsList element not found!');
            return;
        }
        
        // Clear previous content
        list.innerHTML = '';
        
        // Get current chat messages to determine if it's a new chat or ongoing
        const chatMessages = document.getElementById('chatMessages');
        const userMessages = chatMessages.querySelectorAll('.message.user .message-content');
        const isNewChat = userMessages.length === 0;
        
        if (isNewChat) {
            // Show sample prompts for new chat
            this.addSamplePrompts(list);
        } else {
            // Show recent user prompts + sample prompts for ongoing chat
            this.addRecentPrompts(list, userMessages);
            this.addSamplePrompts(list);
        }
        
        // Show backdrop and popup
        backdrop.classList.add('show');
        popup.classList.add('show');
        button.classList.add('active');
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    hideRecentPromptsPopup() {
        const popup = document.getElementById('recentPromptsPopup');
        const backdrop = document.getElementById('recentPromptsBackdrop');
        const button = document.getElementById('recentPromptsBtn');
        
        // Hide backdrop and popup
        backdrop.classList.remove('show');
        popup.classList.remove('show');
        button.classList.remove('active');
        
        // Restore body scroll
        document.body.style.overflow = '';
    }

    addSamplePrompts(list) {
        const samplePrompts = [
            { text: 'list my recent documents', icon: 'fas fa-list' },
            { text: 'summarize my documents added this week', icon: 'fas fa-calendar-week' },
            { text: 'give me a list of categories for my recent documents', icon: 'fas fa-tags' },
            { text: 'what do you know about [document title]', icon: 'fas fa-question-circle' },
            { text: 'tell me about [document title]', icon: 'fas fa-info-circle' }
        ];
        
        samplePrompts.forEach(prompt => {
            const item = document.createElement('div');
            item.className = 'recent-prompts-item sample';
            item.innerHTML = `<i class="${prompt.icon}"></i>${prompt.text}`;
            item.addEventListener('click', () => {
                this.selectPrompt(prompt.text);
            });
            list.appendChild(item);
        });
    }

    addRecentPrompts(list, userMessages) {
        // Get the 5 most recent user prompts
        const recentPrompts = [];
        for (let i = userMessages.length - 1; i >= 0 && recentPrompts.length < 5; i--) {
            const prompt = userMessages[i].textContent.trim();
            if (prompt && !recentPrompts.includes(prompt)) {
                recentPrompts.unshift(prompt);
            }
        }
        
        recentPrompts.forEach(prompt => {
            const item = document.createElement('div');
            item.className = 'recent-prompts-item recent';
            item.innerHTML = `<i class="fas fa-history"></i>${prompt}`;
            item.addEventListener('click', () => {
                this.selectPrompt(prompt);
            });
            list.appendChild(item);
        });
    }

    // MCP Tools popup methods
    toggleMcpToolsPopup() {
        console.log('toggleMcpToolsPopup called');
        const popup = document.getElementById('mcpToolsPopup');
        
        if (popup.classList.contains('show')) {
            console.log('Hiding MCP tools popup...');
            this.hideMcpToolsPopup();
        } else {
            console.log('Showing MCP tools popup...');
            this.showMcpToolsPopup();
        }
    }

    showMcpToolsPopup() {
        const popup = document.getElementById('mcpToolsPopup');
        const backdrop = document.getElementById('mcpToolsBackdrop');
        const button = document.getElementById('mcpToolsBtn');
        const list = document.getElementById('mcpToolsList');
        
        // Check if list element exists
        if (!list) {
            console.error('mcpToolsList element not found!');
            return;
        }
        
        // Clear previous content
        list.innerHTML = '';
        
        // Populate MCP servers list
        this.renderMcpServers(list);
        
        // Show backdrop and popup
        backdrop.classList.add('show');
        popup.classList.add('show');
        button.classList.add('active');
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    hideMcpToolsPopup() {
        const popup = document.getElementById('mcpToolsPopup');
        const backdrop = document.getElementById('mcpToolsBackdrop');
        const button = document.getElementById('mcpToolsBtn');
        
        // Hide backdrop and popup
        backdrop.classList.remove('show');
        popup.classList.remove('show');
        button.classList.remove('active');
        
        // Restore body scroll
        document.body.style.overflow = '';
    }

    renderMcpServers(list) {
        this.mcpServers.forEach(server => {
            const item = document.createElement('div');
            item.className = 'mcp-tools-item';
            
            // Disable non-authenticated servers
            const isDisabled = !server.authenticated;
            const disabledClass = isDisabled ? 'disabled' : '';
            
            item.innerHTML = `
                <div class="mcp-tools-item-info" title="${isDisabled ? 'Authenticate with MCP Servers menu to enable this server' : ''}">
                    <div class="mcp-tools-item-icon">
                        <i class="${server.icon}"></i>
                    </div>
                    <div class="mcp-tools-item-name">
                        ${server.name}
                        ${server.authenticated ? '<span style="color: #2563eb; font-size: 0.8em; margin-left: 0.5rem;">✓</span>' : ''}
                    </div>
                </div>
                <div class="mcp-tools-toggle ${server.enabled ? 'enabled' : ''} ${disabledClass}" data-server="${server.name}" title="${isDisabled ? 'Authenticate with MCP Servers menu to enable this server' : ''}"></div>
            `;
            
            // Add click handler for toggle (only for authenticated servers)
            const toggle = item.querySelector('.mcp-tools-toggle');
            if (!isDisabled) {
                toggle.addEventListener('click', () => {
                    this.toggleMcpServer(server.name);
                });
            }
            
            list.appendChild(item);
        });
    }

    toggleMcpServer(serverName) {
        const server = this.mcpServers.find(s => s.name === serverName);
        if (!server) {
            console.error('Server not found:', serverName);
            return;
        }
        
        // Prevent toggling non-authenticated servers
        if (!server.authenticated) {
            this.showNotification('warning', `${serverName} must be authenticated before it can be enabled/disabled`);
            return;
        }
        
        // Toggle the enabled state
        server.enabled = !server.enabled;
        
        // Update the UI
        const toggle = document.querySelector(`[data-server="${serverName}"]`);
        if (toggle) {
            toggle.classList.toggle('enabled', server.enabled);
        }
        
        // Log the change
        console.log(`MCP Server ${serverName} ${server.enabled ? 'enabled' : 'disabled'}`);
        
        // Add to pending changes for batching
        this.addToPendingChanges(serverName, server.enabled);
    }

    addToPendingChanges(serverName, enabled) {
        console.log('Adding to pending changes:', serverName, enabled);
        
        // Remove any existing change for this server
        this.pendingMcpChanges = this.pendingMcpChanges.filter(change => change.server !== serverName);
        
        // Add the new change
        this.pendingMcpChanges.push({
            server: serverName,
            enabled: enabled
        });
        
        console.log('Current pending changes:', this.pendingMcpChanges);
        
        // Clear existing timeout and set new one
        if (this.mcpChangeTimeout) {
            clearTimeout(this.mcpChangeTimeout);
        }
        
        // Send changes after a short delay (batching)
        this.mcpChangeTimeout = setTimeout(() => {
            console.log('Timeout triggered, sending changes...');
            this.sendPendingMcpChanges();
        }, 500); // 500ms delay for batching
    }
    
    sendPendingMcpChanges() {
        if (this.pendingMcpChanges.length === 0) {
            return;
        }
        
        const changes = [...this.pendingMcpChanges];
        this.pendingMcpChanges = []; // Clear pending changes
        
        console.log('Sending MCP server changes:', changes);
        
        // Call the backend API to update MCP server configurations
        fetch('http://localhost:8021/mcp-server-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                servers: changes
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('MCP Server configurations updated:', data);
            // Show success notification
            this.showNotification('success', data.message);
        })
        .catch(error => {
            console.error('Error updating MCP server configurations:', error);
            // Show error notification
            this.showNotification('error', `Failed to update MCP server configurations: ${error.message}`);
            
            // Revert all changes on error
            changes.forEach(change => {
                const server = this.mcpServers.find(s => s.name === change.server);
                if (server) {
                    server.enabled = !change.enabled; // Revert to previous state
                    const toggle = document.querySelector(`[data-server="${change.server}"]`);
                    if (toggle) {
                        toggle.classList.toggle('enabled', server.enabled);
                    }
                }
            });
        });
    }
    
    updateMcpServerStatus(serverName, enabled) {
        // Legacy method - now uses batching instead
        this.addToPendingChanges(serverName, enabled);
    }

    // MCP Servers Modal methods
    showMcpServersModal() {
        this.showModal('mcpServersModal');
        this.renderMcpServersList();
    }

    renderMcpServersList() {
        const list = document.getElementById('mcpServersList');
        if (!list) return;

        list.innerHTML = '';
        
        this.mcpServers.forEach(server => {
            const item = document.createElement('div');
            item.className = 'mcp-server-item';
            
            item.innerHTML = `
                <div class="mcp-server-info">
                    <div class="mcp-server-icon">
                        <i class="${server.icon}"></i>
                    </div>
                    <div class="mcp-server-name">${server.name}</div>
                </div>
                <div class="mcp-server-status">
                    <div class="mcp-server-enabled ${server.enabled ? 'enabled' : 'disabled'}">
                        ${server.enabled ? 'Enabled' : 'Disabled'}
                    </div>
                    <div class="mcp-server-authenticated ${server.authenticated ? 'authenticated' : 'not-authenticated'}">
                        ${server.authenticated ? 'Authenticated' : 'Not Authenticated'}
                    </div>
                    <button class="authenticate-btn" data-server="${server.name}" ${server.authenticated ? 'disabled' : ''}>
                        ${server.authenticated ? 'Authenticated' : 'Authenticate'}
                    </button>
                </div>
            `;
            
            // Add click handler for authenticate button
            const authBtn = item.querySelector('.authenticate-btn');
            if (!server.authenticated) {
                authBtn.addEventListener('click', () => {
                    this.showAuthenticationModal(server.name);
                });
            }
            
            list.appendChild(item);
        });
    }

    showAuthenticationModal(serverName) {
        const title = document.getElementById('authModalTitle');
        const message = document.getElementById('authModalMessage');
        
        title.textContent = 'Authenticate';
        message.textContent = `Authenticate with ${serverName}`;
        
        // Store the server name for the confirmation
        this.currentAuthServer = serverName;
        
        this.showModal('authModal');
    }

    confirmAuthentication() {
        if (!this.currentAuthServer) return;
        
        const server = this.mcpServers.find(s => s.name === this.currentAuthServer);
        if (!server) return;
        
        // Mark as authenticated and enabled
        server.authenticated = true;
        server.enabled = true;
        
        // Update the API
        this.updateMcpServerWithAuth(this.currentAuthServer, true, true);
        
        // Hide the auth modal
        this.hideModal('authModal');
        
        // Re-render the MCP servers list
        this.renderMcpServersList();
        
        // Show success notification
        this.showNotification('success', `Successfully authenticated with ${this.currentAuthServer}`);
        
        this.currentAuthServer = null;
    }

    updateMcpServerWithAuth(serverName, enabled, authenticated) {
        // Call the backend API to update MCP server configuration with authentication
        fetch('http://localhost:8021/mcp-server-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                servers: [{
                    server: serverName,
                    enabled: enabled,
                    authenticated: authenticated
                }]
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('MCP Server authentication updated:', data);
        })
        .catch(error => {
            console.error('Error updating MCP server authentication:', error);
            this.showNotification('error', `Failed to update MCP server authentication: ${error.message}`);
        });
    }

    selectPrompt(prompt) {
        const chatInput = document.getElementById('chatInput');
        chatInput.value = prompt;
        chatInput.focus();
        
        // Auto-resize the textarea
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        
        // Hide the popup
        this.hideRecentPromptsPopup();
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
        const appTitle = this.config?.application?.title || '🤖 RAGme.io Assistant';
        const welcomeMessage = `Welcome to **${appTitle}**! 

I can help you with:

• **Adding URLs** - Tell me URLs to crawl and add to your knowledge base
• **Adding documents (Text, PDF, DOCX, etc.)** - Use the "Add Content" button to add files and structured data
• **Adding images (JPG, PNG, GIF, etc.)** - Use the "Add Content" button to upload and analyze images with AI
• **Answering questions** - Ask me anything about your documents and images
• **Document management** - View and explore your documents and images in the right panel

Try asking me to add some URLs, documents, or images, or ask questions about your existing content!`;

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
        
        // Load any images in AI messages
        if (message.type === 'ai') {
            this.loadAgentImages(contentDiv);
        }

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
            
            // Use configuration-based limits
            const minWidth = 200;
            const maxWidth = window.innerWidth * (this.settings.documentListWidth / 100);
            
            if (newWidth > minWidth && newWidth < maxWidth) {
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
        this.switchTab('urlTab');
    }

    showSettingsModal() {
        this.showModal('settingsModal');
        
        // Populate application information
        if (this.config && this.config.application) {
            document.getElementById('appName').textContent = this.config.application.name || 'RAGme';
            document.getElementById('appVersion').textContent = this.config.application.version || '1.0.0';
        }
        
        // Load and set vector DB info with a delay to ensure it runs after other functions
        setTimeout(() => {
            this.loadVectorDbInfoForSettings();
        }, 100);
        
        // Populate general settings
        document.getElementById('maxDocuments').value = this.settings.maxDocuments;
        document.getElementById('showVectorDbInfo').checked = this.settings.showVectorDbInfo;
        document.getElementById('autoRefresh').checked = this.settings.autoRefresh;
        document.getElementById('refreshInterval').value = this.settings.refreshInterval / 1000; // Convert to seconds
        
        // Populate interface settings
        document.getElementById('documentListWidth').value = this.settings.documentListWidth;
        document.getElementById('documentListWidthValue').textContent = this.settings.documentListWidth + '%';
        document.getElementById('chatHistoryWidth').value = this.settings.chatHistoryWidth;
        document.getElementById('chatHistoryWidthValue').textContent = this.settings.chatHistoryWidth + '%';
        document.getElementById('documentListCollapsed').checked = this.settings.documentListCollapsed;
        document.getElementById('chatHistoryCollapsed').checked = this.settings.chatHistoryCollapsed;
        document.getElementById('documentOverviewVisible').checked = this.settings.documentOverviewVisible;
        
        // Populate visualization settings
        document.getElementById('defaultVisualization').value = this.currentVisualizationType;
        document.getElementById('defaultDateFilter').value = this.currentDateFilter;
        
        // Populate document settings
        document.getElementById('documentOverviewEnabled').checked = this.settings.documentOverviewEnabled;
        document.getElementById('maxDisplayDocuments').value = this.settings.maxDisplayDocuments || 100;
        document.getElementById('paginationSize').value = this.settings.paginationSize || 20;
        document.getElementById('defaultContentFilter').value = this.currentContentFilter;
        
        // Populate chat settings
        document.getElementById('maxTokens').value = this.settings.maxTokens;
        document.getElementById('temperature').value = this.settings.temperature;
        document.getElementById('temperatureValue').textContent = this.settings.temperature;
        document.getElementById('chatHistoryLimit').value = this.settings.chatHistoryLimit || 50;
        document.getElementById('autoSaveChats').checked = this.settings.autoSaveChats !== false;
    }

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('show');
    }

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('show');
    }

    toggleSubmenu(submenuId, triggerId) {
        const submenu = document.getElementById(submenuId);
        const trigger = document.getElementById(triggerId);
        
        if (submenu.classList.contains('show')) {
            submenu.classList.remove('show');
            trigger.classList.remove('active');
        } else {
            submenu.classList.add('show');
            trigger.classList.add('active');
        }
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
        document.getElementById(tabName).classList.add('active');
    }

    submitAddContent() {
        const activeTab = document.querySelector('.tab-btn.active').dataset.tab;
        
        if (activeTab === 'urlTab') {
            const urlsInput = document.getElementById('urlsInput');
            const urls = urlsInput.value.trim().split('\n').filter(url => url.trim());
            
            if (urls.length === 0) {
                this.showNotification('error', 'Please enter at least one URL');
                return;
            }

            this.socket.emit('add_urls', { urls });
            urlsInput.value = '';
        } else if (activeTab === 'filesTab') {
            const fileInput = document.getElementById('fileInput');
            const files = fileInput.files;
            
            if (files.length === 0) {
                this.showNotification('error', 'Please select at least one file');
                return;
            }

            // Handle file uploads
            this.uploadFiles(files);
        } else if (activeTab === 'imagesTab') {
            const imageInput = document.getElementById('imageInput');
            const images = imageInput.files;
            
            if (images.length === 0) {
                this.showNotification('error', 'Please select at least one image');
                return;
            }

            // Handle image uploads
            this.uploadImages(images);
        } else if (activeTab === 'jsonTab') {
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

    uploadImages(files) {
        console.log('Uploading images:', files);
        const formData = new FormData();
        
        for (let i = 0; i < files.length; i++) {
            console.log('Adding file to FormData:', files[i].name, files[i].type, files[i].size);
            formData.append('files', files[i]);
        }

        // Show loading notification
        this.showNotification('info', `Processing ${files.length} image(s)...`);

        // Send images to backend via API
        console.log('Sending request to /upload-images');
        fetch('/upload-images', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.showNotification('success', `Successfully processed ${files.length} image(s) with AI classification`);
                // Refresh documents list to show images
                this.loadDocuments();
            } else {
                this.showNotification('error', data.message || 'Image upload failed');
            }
        })
        .catch(error => {
            console.error('Image upload error:', error);
            this.showNotification('error', 'Image upload failed. Please try again.');
        });
    }

    setupFileUpload() {
        const fileUploadArea = document.getElementById('fileUploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        
        const imageUploadArea = document.getElementById('imageUploadArea');
        const imageInput = document.getElementById('imageInput');
        const imageList = document.getElementById('imageList');

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

        // Click to select images
        imageUploadArea.addEventListener('click', () => {
            imageInput.click();
        });

        // Handle image selection
        imageInput.addEventListener('change', (e) => {
            this.updateImageList(e.target.files);
        });

        // Drag and drop functionality
        imageUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            imageUploadArea.classList.add('dragover');
        });

        imageUploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            imageUploadArea.classList.remove('dragover');
        });

        imageUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            imageUploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            imageInput.files = files;
            this.updateImageList(files);
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

    updateImageList(files) {
        const imageList = document.getElementById('imageList');
        imageList.innerHTML = '';

        Array.from(files).forEach((file, index) => {
            const imageItem = document.createElement('div');
            imageItem.className = 'image-item';
            
            const imageIcon = this.getImageIcon(file.name);
            const imageSize = this.formatImageSize(file.size);
            
            imageItem.innerHTML = `
                <div class="image-item-info">
                    <i class="${imageIcon} image-item-icon"></i>
                    <div>
                        <div class="image-item-name">${this.escapeHtml(file.name)}</div>
                        <div class="image-item-size">${imageSize}</div>
                    </div>
                </div>
                <button class="image-item-remove" onclick="this.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            imageList.appendChild(imageItem);
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

    getImageIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const iconMap = {
            'jpg': 'fa-file-image',
            'jpeg': 'fa-file-image',
            'png': 'fa-file-image',
            'gif': 'fa-file-image',
            'heic': 'fa-file-image',
            'heif': 'fa-file-image'
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

    formatImageSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    saveSettings() {
        // General settings
        const maxDocuments = parseInt(document.getElementById('maxDocuments').value);
        const showVectorDbInfo = document.getElementById('showVectorDbInfo').checked;
        const autoRefresh = document.getElementById('autoRefresh').checked;
        const refreshInterval = parseInt(document.getElementById('refreshInterval').value) * 1000; // Convert to milliseconds
        
        // Interface settings
        const documentListWidth = parseInt(document.getElementById('documentListWidth').value);
        const chatHistoryWidth = parseInt(document.getElementById('chatHistoryWidth').value);
        const documentListCollapsed = document.getElementById('documentListCollapsed').checked;
        const chatHistoryCollapsed = document.getElementById('chatHistoryCollapsed').checked;
        const documentOverviewVisible = document.getElementById('documentOverviewVisible').checked;
        
        // Visualization settings
        const defaultVisualization = document.getElementById('defaultVisualization').value;
        const defaultDateFilter = document.getElementById('defaultDateFilter').value;
        
        // Document settings
        const documentOverviewEnabled = document.getElementById('documentOverviewEnabled').checked;
        const maxDisplayDocuments = parseInt(document.getElementById('maxDisplayDocuments').value);
        const paginationSize = parseInt(document.getElementById('paginationSize').value);
        const defaultContentFilter = document.getElementById('defaultContentFilter').value;
        
        // Chat settings
        const maxTokens = parseInt(document.getElementById('maxTokens').value);
        const temperature = parseFloat(document.getElementById('temperature').value);
        const chatHistoryLimit = parseInt(document.getElementById('chatHistoryLimit').value);
        const autoSaveChats = document.getElementById('autoSaveChats').checked;
        
        // Validation
        if (maxDocuments < 1 || maxDocuments > 100) {
            this.showNotification('error', 'Max documents must be between 1 and 100');
            return;
        }
        
        if (documentListWidth < 20 || documentListWidth > 60) {
            this.showNotification('error', 'Document list width must be between 20% and 60%');
            return;
        }
        
        if (chatHistoryWidth < 5 || chatHistoryWidth > 30) {
            this.showNotification('error', 'Chat history width must be between 5% and 30%');
            return;
        }
        
        if (maxTokens < 1000 || maxTokens > 16000) {
            this.showNotification('error', 'Max tokens must be between 1000 and 16000');
            return;
        }
        
        if (temperature < 0 || temperature > 2) {
            this.showNotification('error', 'Temperature must be between 0 and 2');
            return;
        }

        // Update settings
        this.settings.maxDocuments = maxDocuments;
        this.settings.showVectorDbInfo = showVectorDbInfo;
        this.settings.autoRefresh = autoRefresh;
        this.settings.refreshInterval = refreshInterval;
        this.settings.documentListWidth = documentListWidth;
        this.settings.chatHistoryWidth = chatHistoryWidth;
        this.settings.documentListCollapsed = documentListCollapsed;
        this.settings.chatHistoryCollapsed = chatHistoryCollapsed;
        this.settings.documentOverviewVisible = documentOverviewVisible;
        this.settings.documentOverviewEnabled = documentOverviewEnabled;
        this.settings.maxDisplayDocuments = maxDisplayDocuments;
        this.settings.paginationSize = paginationSize;
        this.settings.maxTokens = maxTokens;
        this.settings.temperature = temperature;
        this.settings.chatHistoryLimit = chatHistoryLimit;
        this.settings.autoSaveChats = autoSaveChats;
        
        // Update global settings
        this.currentVisualizationType = defaultVisualization;
        this.currentDateFilter = defaultDateFilter;
        this.currentContentFilter = defaultContentFilter;
        
        // Save to localStorage
        localStorage.setItem('ragme-settings', JSON.stringify(this.settings));
        localStorage.setItem('ragme-date-filter', this.currentDateFilter);
        localStorage.setItem('ragme-visualization-type', this.currentVisualizationType);
        localStorage.setItem('ragme-content-filter', this.currentContentFilter);
        localStorage.setItem('ragme-max-documents', maxDocuments.toString());
        localStorage.setItem('ragme-document-overview-enabled', documentOverviewEnabled.toString());
        localStorage.setItem('ragme-document-overview-visible', documentOverviewVisible.toString());
        localStorage.setItem('ragme-document-list-collapsed', documentListCollapsed.toString());
        localStorage.setItem('ragme-document-list-width', documentListWidth.toString());
        localStorage.setItem('ragme-chat-history-collapsed', chatHistoryCollapsed.toString());
        localStorage.setItem('ragme-chat-history-width', chatHistoryWidth.toString());
        
        this.hideModal('settingsModal');
        this.showNotification('success', 'Settings saved successfully');
        
        // Apply UI changes
        this.applyUIConfiguration();
        
        // Update auto-refresh if changed
        if (autoRefresh !== this.settings.autoRefresh) {
            if (autoRefresh) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        }
        
        // Reload documents with new settings
        this.loadDocuments();
    }

    loadSettings() {
        const saved = localStorage.getItem('ragme-settings');
        if (saved) {
            this.settings = { ...this.settings, ...JSON.parse(saved) };
        }
        
        // Load content filter preference
        const savedContentFilter = localStorage.getItem('ragme-content-filter');
        if (savedContentFilter) {
            this.currentContentFilter = savedContentFilter;
            // Update the dropdown to reflect the saved preference
            const contentFilterSelector = document.getElementById('contentFilterSelector');
            if (contentFilterSelector) {
                contentFilterSelector.value = this.currentContentFilter;
            }
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
        
        // Load visualization type preference
        const savedVisualizationType = localStorage.getItem('ragme-visualization-type');
        if (savedVisualizationType) {
            this.currentVisualizationType = savedVisualizationType;
        }
        
        // Load visualization visibility preference
        const savedVisualizationVisible = localStorage.getItem('ragme-visualization-visible');
        if (savedVisualizationVisible !== null) {
            this.isVisualizationVisible = savedVisualizationVisible === 'true';
        }
        
        // Load individual settings from localStorage for backward compatibility
        const savedMaxDocuments = localStorage.getItem('ragme-max-documents');
        if (savedMaxDocuments) {
            this.settings.maxDocuments = parseInt(savedMaxDocuments);
        }
        
        const savedDocumentOverviewEnabled = localStorage.getItem('ragme-document-overview-enabled');
        if (savedDocumentOverviewEnabled !== null) {
            this.settings.documentOverviewEnabled = savedDocumentOverviewEnabled === 'true';
        }
        
        const savedDocumentOverviewVisible = localStorage.getItem('ragme-document-overview-visible');
        if (savedDocumentOverviewVisible !== null) {
            // Only override if not explicitly set by configuration
            if (this.settings.documentOverviewVisible === undefined) {
                this.settings.documentOverviewVisible = savedDocumentOverviewVisible === 'true';
                console.log('Loaded document overview visible from localStorage:', this.settings.documentOverviewVisible);
            } else {
                console.log('Keeping document overview visible from configuration:', this.settings.documentOverviewVisible);
            }
        }
        
        const savedDocumentListCollapsed = localStorage.getItem('ragme-document-list-collapsed');
        if (savedDocumentListCollapsed !== null) {
            this.settings.documentListCollapsed = savedDocumentListCollapsed === 'true';
        }
        
        const savedDocumentListWidth = localStorage.getItem('ragme-document-list-width');
        if (savedDocumentListWidth) {
            this.settings.documentListWidth = parseInt(savedDocumentListWidth);
        }
        
        const savedChatHistoryCollapsed = localStorage.getItem('ragme-chat-history-collapsed');
        if (savedChatHistoryCollapsed !== null) {
            this.settings.chatHistoryCollapsed = savedChatHistoryCollapsed === 'true';
        }
        
        const savedChatHistoryWidth = localStorage.getItem('ragme-chat-history-width');
        if (savedChatHistoryWidth) {
            this.settings.chatHistoryWidth = parseInt(savedChatHistoryWidth);
        }
        
        // Update the visualization type selector to reflect the saved preference
        const visualizationTypeSelector = document.getElementById('visualizationTypeSelector');
        if (visualizationTypeSelector) {
            visualizationTypeSelector.value = this.currentVisualizationType;
        }
    }

    loadDocuments() {
        console.log('Loading content with filters - date:', this.currentDateFilter, 'content:', this.currentContentFilter);
        console.log('Socket connected:', this.socket?.connected);
        console.log('Emitting list_content event...');
        this.socket.emit('list_content', {
            limit: this.settings.maxDocuments,
            offset: 0,
            dateFilter: this.currentDateFilter,
            contentType: this.currentContentFilter
        });
        console.log('list_content event emitted');
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
        this.autoRefreshInterval = setInterval(() => {
            console.log('Auto-refreshing documents and vector DB info...');
            this.loadDocuments();
            this.loadVectorDbInfoFromBackend();
        }, 30000); // 30 seconds
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    fetchDocumentSummary(doc) {
        console.log('fetchDocumentSummary called for doc:', doc.id || doc.url);
        
        // Prevent multiple simultaneous summary requests
        if (this.documentDetailsModal.summaryInProgress) {
            console.log('Summary already in progress, skipping request');
            return;
        }
        
        // Mark summary as in progress
        this.documentDetailsModal.summaryInProgress = true;
        
        // Find the document in the original documents array
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
            // For regular documents, find by ID first, then by URL
            docIndex = this.documents.findIndex(d => d.id === doc.id);
            if (docIndex === -1) {
                docIndex = this.documents.findIndex(d => d.url === doc.url);
            }
        }
        
        if (docIndex === -1) {
            this.updateDocumentSummary('Document not found for summarization.');
            return;
        }
        
        console.log('Found document at index:', docIndex, 'in documents array');
        console.log('Sending document ID for summarization:', doc.id || docIndex.toString());
        
        // Set a timeout to show a message if summarization takes too long
        const timeoutId = setTimeout(() => {
            this.updateDocumentSummary('<div class="summary-loading">Still generating summary... This may take a moment for large documents.</div>');
        }, 10000); // 10 seconds
        
        // Request summary from backend - send the actual document ID
        this.socket.emit('summarize_document', {
            documentId: doc.id || docIndex.toString()
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
        
        // Find the AI summary section specifically (not the image preview section)
        const aiSummarySection = document.querySelector('#documentDetailsModal .document-details-section h4 i.fas.fa-robot');
        const contentPreview = aiSummarySection ? 
            aiSummarySection.closest('.document-details-section').querySelector('.content-preview') :
            document.querySelector('#documentDetailsModal .content-preview');
            
        if (contentPreview) {
            // Parse markdown and format the summary
            const formattedSummary = this.formatMarkdownSummary(summary);
            contentPreview.innerHTML = formattedSummary;
            
            // Mark summary as generated for the current document
            this.documentDetailsModal.summaryGenerated = true;
        }
        
        // Reset the in-progress flag
        this.documentDetailsModal.summaryInProgress = false;
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
        // Skip rendering if document details modal is open to prevent interference
        if (this.documentDetailsModal.isOpen) {
            console.log('Skipping document rendering - modal is open, currentDocId:', this.documentDetailsModal.currentDocId);
            return;
        }
        
        console.log('Rendering documents, modal state:', this.documentDetailsModal);

        const container = document.getElementById('documentsListContainer');
        container.innerHTML = '';

        if (this.documents.length === 0) {
            const icon = this.currentContentFilter === 'images' ? 'fas fa-images' : 'fas fa-file-alt';
            const message = this.currentContentFilter === 'images' ? 'No images found' : 
                           this.currentContentFilter === 'documents' ? 'No documents found' : 'No content found';
            const subMessage = this.currentContentFilter === 'images' ? 'Add some images to get started' :
                              this.currentContentFilter === 'documents' ? 'Add some URLs or files to get started' :
                              'Add some URLs, files, or images to get started';
            
            container.innerHTML = `
                <div style="text-align: center; color: #666; padding: 2rem;">
                    <i class="${icon}" style="font-size: 3rem; opacity: 0.5; margin-bottom: 1rem;"></i>
                    <p>${message}</p>
                    <p style="font-size: 0.8rem; margin-top: 0.5rem;">${subMessage}</p>
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
            const isNew = this.isDocumentNew(date);
            const contentType = group.content_type || 'document';
            
            // Handle chunked documents (both new and existing)
            let summary = '';
            let chunkInfo = '';
            let newBadge = isNew ? '<span class="new-badge">NEW</span>' : '';
            
            // Handle images
            if (contentType === 'image') {
                const imageTitle = group.metadata?.filename || title;
                const imageClassification = group.metadata?.classification || 'Unknown';
                const imageSize = group.metadata?.file_size || 'Unknown size';
                
                card.innerHTML = `
                    <div class="document-content">
                        <div class="document-title">
                            <span class="document-title-text">${this.escapeHtml(imageTitle)}</span>
                            <span class="image-badge"><i class="fas fa-image"></i> Image</span>
                            ${newBadge}
                        </div>
                        <div class="document-meta">
                            <i class="fas fa-calendar"></i> ${date} | 
                            <i class="fas fa-database"></i> ${group.metadata?.collection || 'Images'} |
                            <i class="fas fa-tag"></i> ${imageClassification} |
                            <i class="fas fa-weight-hanging"></i> ${imageSize}
                        </div>
                        <div class="document-summary">
                            <i class="fas fa-image" style="color: #6b7280; margin-right: 0.5rem;"></i>
                            Image file with AI classification: ${imageClassification}
                        </div>
                    </div>
                    <button class="document-delete-btn" data-doc-index="${index}" title="Delete image">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
            } else
            
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
                            ${newBadge}
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
                            ${newBadge}
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
                            ${newBadge}
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

        // Generate a unique document ID for tracking
        const docId = doc.id || doc.url || `doc_${Date.now()}`;
        
        // Check if this is the same document already open
        const isSameDocument = this.documentDetailsModal.isOpen && 
                              this.documentDetailsModal.currentDocId === docId;
        
        console.log('showDocumentDetails called:', {
            docId,
            isOpen: this.documentDetailsModal.isOpen,
            currentDocId: this.documentDetailsModal.currentDocId,
            isSameDocument,
            summaryGenerated: this.documentDetailsModal.summaryGenerated
        });
        
        // Find the document index in the grouped documents array
        const groupedDocuments = this.groupDocumentsByBaseUrl(this.documents);
        const docIndex = groupedDocuments.findIndex(d => d.url === doc.url || d.id === doc.id);
        
        console.log('Document details - found index:', docIndex, 'for doc:', { id: doc.id, url: doc.url, contentType: doc.content_type });
        console.log('Grouped documents count:', groupedDocuments.length);
        
        // Store the document index for deletion
        modal.dataset.docIndex = docIndex;

        let displayTitle = doc.url || doc.metadata?.filename || 'Document Details';
        
        // Use original filename for chunked documents
        if (doc.isGroupedChunks && doc.originalFilename) {
            displayTitle = doc.originalFilename;
        } else if (doc.metadata?.is_chunked && doc.metadata?.original_filename) {
            displayTitle = doc.metadata.original_filename;
        }

        // Add NEW badge if document is new
        const isNew = this.isDocumentNew(doc.metadata?.date_added);
        const newBadge = isNew ? '<span class="new-badge-modal">NEW</span>' : '';
        
        title.innerHTML = `${displayTitle}${newBadge}`;

        // Check if this is an image
        const isImage = doc.content_type === 'image';
        
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
                <div class="detail-value">${this.escapeHtml(doc.url || doc.metadata?.filename || doc.metadata?.source || 'N/A')}</div>
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
            
            ${isImage ? `
                <div class="document-details-section">
                    <h4><i class="fas fa-image"></i> Image Preview</h4>
                    <div class="content-preview">
                        <div class="content-loading">
                            <i class="fas fa-spinner fa-spin"></i>
                            <p>Loading image preview...</p>
                        </div>
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
        
        // Update modal state
        this.documentDetailsModal.isOpen = true;
        this.documentDetailsModal.currentDocId = docId;
        
        // Check for text truncation in modal details
        setTimeout(() => {
            this.checkDetailValuesTruncation();
        }, 100);
        
        // For images, show the image preview
        if (isImage) {
            console.log('Showing image preview for image document');
            this.showImageInModal(doc);
        }
        
        // Fetch AI summary for all document types (including images) if not already generated
        if (!isSameDocument || !this.documentDetailsModal.summaryGenerated) {
            console.log('Calling fetchDocumentSummary - conditions met');
            this.fetchDocumentSummary(doc);
        } else {
            console.log('Skipping fetchDocumentSummary - same document and summary already generated');
        }
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
        
        // Special handling for image metadata - check for various image-related types
        if (metadata.type === 'image' || metadata.type === 'image_classification' || metadata.format === 'image') {
            return this.createImageMetadataTags(metadata);
        }
        
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

    createImageMetadataTags(metadata) {
        if (!metadata) return '';
        
        const sections = [];
        
        // Basic Info Section
        const basicInfo = [];
        if (metadata.source) {
            basicInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">Source</span>
                    <span class="tag-value">${this.escapeHtml(metadata.source)}</span>
                </div>
            `);
        }
        if (metadata.url) {
            basicInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">URL</span>
                    <span class="tag-value">${this.escapeHtml(metadata.url)}</span>
                </div>
            `);
        }
        if (metadata.collection) {
            basicInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">Collection</span>
                    <span class="tag-value">${this.escapeHtml(metadata.collection)}</span>
                </div>
            `);
        }
        if (metadata.filename) {
            basicInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">Filename</span>
                    <span class="tag-value">${this.escapeHtml(metadata.filename)}</span>
                </div>
            `);
        }
        if (metadata.file_size) {
            const sizeKB = Math.round(metadata.file_size / 1024);
            basicInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">File Size</span>
                    <span class="tag-value">${sizeKB} KB</span>
                </div>
            `);
        }
        
        if (basicInfo.length > 0) {
            sections.push(`
                <div class="metadata-section">
                    <h5 class="section-title">Basic Info</h5>
                    ${basicInfo.join('')}
                </div>
            `);
        }
        
        // EXIF Data Section
        if (metadata.exif && Object.keys(metadata.exif).length > 0) {
            const exifTags = [];
            const importantExifKeys = [
                'make', 'model', 'datetime', 'exposure_time', 'f_number', 
                'iso_speed_ratings', 'focal_length', 'gps_latitude', 'gps_longitude'
            ];
            
            // Show important EXIF data first
            importantExifKeys.forEach(key => {
                if (metadata.exif[key]) {
                    exifTags.push(`
                        <div class="metadata-tag">
                            <span class="tag-key">${this.formatExifKey(key)}</span>
                            <span class="tag-value">${this.escapeHtml(metadata.exif[key])}</span>
                        </div>
                    `);
                }
            });
            
            // Show other EXIF data in a collapsible section
            const otherExifKeys = Object.keys(metadata.exif).filter(key => !importantExifKeys.includes(key));
            if (otherExifKeys.length > 0) {
                const otherExifTags = otherExifKeys.map(key => `
                    <div class="metadata-tag">
                        <span class="tag-key">${this.formatExifKey(key)}</span>
                        <span class="tag-value">${this.escapeHtml(metadata.exif[key])}</span>
                    </div>
                `).join('');
                
                exifTags.push(`
                    <div class="metadata-collapsible">
                        <button class="collapsible-btn" data-action="toggle-collapse">
                            <i class="fas fa-chevron-down"></i> Show ${otherExifKeys.length} more EXIF fields
                        </button>
                        <div class="collapsible-content">
                            ${otherExifTags}
                        </div>
                    </div>
                `);
            }
            
            sections.push(`
                <div class="metadata-section">
                    <h5 class="section-title">EXIF Data</h5>
                    <div class="metadata-scrollable">
                        ${exifTags.join('')}
                    </div>
                </div>
            `);
        }
        
        // Classification Section
        if (metadata.classifications || metadata.classification) {
            const classifications = metadata.classifications || metadata.classification?.classifications || [];
            const topPred = metadata.top_prediction || metadata.classification?.top_prediction;
            
            const classificationTags = [];
            
            // Model and Dataset info
            if (metadata.model) {
                classificationTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">Model</span>
                        <span class="tag-value">${this.escapeHtml(metadata.model)}</span>
                    </div>
                `);
            }
            if (metadata.dataset) {
                classificationTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">Dataset</span>
                        <span class="tag-value">${this.escapeHtml(metadata.dataset)}</span>
                    </div>
                `);
            }
            if (metadata.top_k) {
                classificationTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">Top K</span>
                        <span class="tag-value">${metadata.top_k}</span>
                    </div>
                `);
            }
            
            if (topPred && topPred.label) {
                classificationTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">Primary Label</span>
                        <span class="tag-value">${this.escapeHtml(topPred.label)}</span>
                    </div>
                `);
            }
            if (topPred && topPred.confidence) {
                const confidencePercent = (topPred.confidence * 100).toFixed(1);
                classificationTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">Confidence</span>
                        <span class="tag-value">${confidencePercent}%</span>
                    </div>
                `);
            }
            
            // Show all predictions if available
            if (classifications && classifications.length > 0) {
                const predictionTags = classifications.map((pred, index) => `
                    <div class="metadata-tag">
                        <span class="tag-key">${pred.rank || index + 1}. ${this.escapeHtml(pred.label || 'Unknown')}</span>
                        <span class="tag-value">${((pred.confidence || 0) * 100).toFixed(1)}%</span>
                    </div>
                `).join('');
                
                classificationTags.push(`
                    <div class="metadata-collapsible">
                        <button class="collapsible-btn" data-action="toggle-collapse">
                            <i class="fas fa-chevron-down"></i> Show all ${classifications.length} predictions
                        </button>
                        <div class="collapsible-content">
                            ${predictionTags}
                        </div>
                    </div>
                `);
            }
            
            sections.push(`
                <div class="metadata-section">
                    <h5 class="section-title">AI Classification</h5>
                    ${classificationTags.join('')}
                </div>
            `);
        }
        
        // Processing Info Section
        const processingInfo = [];
        if (metadata.processing_timestamp) {
            processingInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">Processed</span>
                    <span class="tag-value">${this.formatDate(metadata.processing_timestamp)}</span>
                </div>
            `);
        }
        if (metadata.pytorch_processing !== undefined) {
            processingInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">PyTorch</span>
                    <span class="tag-value">${metadata.pytorch_processing ? 'Enabled' : 'Disabled'}</span>
                </div>
            `);
        }
        if (metadata.daft_processing !== undefined) {
            processingInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">Daft Processing</span>
                    <span class="tag-value">${metadata.daft_processing ? 'Enabled' : 'Disabled'}</span>
                </div>
            `);
        }
        if (metadata.format) {
            processingInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">Format</span>
                    <span class="tag-value">${this.escapeHtml(metadata.format)}</span>
                </div>
            `);
        }
        if (metadata.size_bytes) {
            const sizeKB = Math.round(metadata.size_bytes / 1024);
            processingInfo.push(`
                <div class="metadata-tag">
                    <span class="tag-key">Size (bytes)</span>
                    <span class="tag-value">${metadata.size_bytes} (${sizeKB} KB)</span>
                </div>
            `);
        }
        
        if (processingInfo.length > 0) {
            sections.push(`
                <div class="metadata-section">
                    <h5 class="section-title">Processing Info</h5>
                    ${processingInfo.join('')}
                </div>
            `);
        }
        
        // OCR Content Section
        if (metadata.ocr_content && typeof metadata.ocr_content === 'object') {
            const ocrContent = metadata.ocr_content;
            const ocrTags = [];
            
            // Show useful OCR metadata first
            if (ocrContent.ocr_processing !== undefined) {
                ocrTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">OCR Processing</span>
                        <span class="tag-value">${ocrContent.ocr_processing ? 'Enabled' : 'Disabled'}</span>
                    </div>
                `);
            }
            if (ocrContent.text_length !== undefined) {
                ocrTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">Text Length</span>
                        <span class="tag-value">${ocrContent.text_length} characters</span>
                    </div>
                `);
            }
            if (ocrContent.block_count !== undefined) {
                ocrTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">Text Blocks</span>
                        <span class="tag-value">${ocrContent.block_count} blocks</span>
                    </div>
                `);
            }
            if (ocrContent.extracted_text) {
                ocrTags.push(`
                    <div class="metadata-tag">
                        <span class="tag-key">Extracted Text</span>
                        <span class="tag-value ocr-text-content">${this.escapeHtml(ocrContent.extracted_text)}</span>
                    </div>
                `);
            }
            
            // Show text_blocks in a collapsible section if available
            if (ocrContent.text_blocks && ocrContent.text_blocks.length > 0) {
                const textBlocksContent = ocrContent.text_blocks.map((block, index) => {
                    const confidence = block.confidence ? ` (${(block.confidence * 100).toFixed(1)}%)` : '';
                    return `
                        <div class="metadata-tag">
                            <span class="tag-key">Block ${index + 1}${confidence}</span>
                            <span class="tag-value">${this.escapeHtml(block.text || 'No text')}</span>
                        </div>
                    `;
                }).join('');
                
                ocrTags.push(`
                    <div class="metadata-collapsible">
                        <button class="collapsible-btn" data-action="toggle-collapse">
                            <i class="fas fa-chevron-down"></i> Show ${ocrContent.text_blocks.length} text blocks
                        </button>
                        <div class="collapsible-content">
                            ${textBlocksContent}
                        </div>
                    </div>
                `);
            }
            
            if (ocrTags.length > 0) {
                sections.push(`
                    <div class="metadata-section">
                        <h5 class="section-title">OCR Content</h5>
                        ${ocrTags.join('')}
                    </div>
                `);
            }
        }
        
        // Raw Metadata Section (for any other fields, excluding ocr_content)
        const otherKeys = Object.keys(metadata).filter(key => 
            !['source', 'collection', 'exif', 'classification', 'processing_timestamp', 'pytorch_processing', 'date_added', 'url', 'filename', 'file_size', 'model', 'dataset', 'top_k', 'format', 'size_bytes', 'daft_processing', 'daft_dataframe_shape', 'schema', 'ocr_content'].includes(key)
        );
        
        if (otherKeys.length > 0) {
            const otherTags = otherKeys.map(key => {
                let value = metadata[key];
                
                // Special handling for base64 data
                if (key === 'image_data' || key === 'base64_data' || key === 'image') {
                    if (typeof value === 'string' && value.length > 50) {
                        const byteEstimate = Math.round(value.length * 0.75); // Base64 is ~75% of original size
                        return `
                            <div class="metadata-tag">
                                <span class="tag-key">${this.escapeHtml(this.formatMetadataKey(key))}</span>
                                <span class="tag-value">
                                    <span class="base64-preview">${byteEstimate} bytes</span>
                                    <button class="expand-btn" data-action="expand-base64" data-key="${key}" data-value="${this.escapeHtml(value)}">
                                        <i class="fas fa-expand-alt"></i> Show content
                                    </button>
                                </span>
                            </div>
                        `;
                    }
                }
                
                if (typeof value === 'object') {
                    value = JSON.stringify(value, null, 2);
                } else {
                    value = String(value);
                }
                return `
                    <div class="metadata-tag">
                        <span class="tag-key">${this.escapeHtml(this.formatMetadataKey(key))}</span>
                        <span class="tag-value">${this.escapeHtml(value)}</span>
                    </div>
                `;
            }).join('');
            
            sections.push(`
                <div class="metadata-section">
                    <h5 class="section-title">Other Metadata</h5>
                    <div class="metadata-scrollable">
                        ${otherTags}
                    </div>
                </div>
            `);
        }
        
        return sections.join('');
    }

    formatExifKey(key) {
        const exifKeyMap = {
            'make': 'Camera Make',
            'model': 'Camera Model',
            'datetime': 'Date Taken',
            'exposure_time': 'Exposure Time',
            'f_number': 'F-Number',
            'iso_speed_ratings': 'ISO',
            'focal_length': 'Focal Length',
            'gps_latitude': 'GPS Latitude',
            'gps_longitude': 'GPS Longitude',
            'software': 'Software',
            'artist': 'Artist',
            'copyright': 'Copyright'
        };
        
        return exifKeyMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
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

    showImageInModal(doc) {
        console.log('showImageInModal called with doc:', doc);
        // For images, we want to update the image preview section specifically
        const imagePreviewSection = document.querySelector('#documentDetailsModal .document-details-section h4 i.fas.fa-image');
        const contentPreview = imagePreviewSection ? 
            imagePreviewSection.closest('.document-details-section').querySelector('.content-preview') :
            document.querySelector('#documentDetailsModal .content-preview');
            
        if (contentPreview) {
            // Get image data from the document - check multiple possible locations
            // Check for image_data in various locations including the root level and metadata
            const imageData = doc.image_data || 
                            doc.metadata?.image_data || 
                            doc.metadata?.base64_data ||
                            doc.metadata?.image ||
                            doc.image;
            
            // Check for image URL in various locations
            const imageUrl = doc.url || 
                           doc.metadata?.url || 
                           doc.metadata?.source ||
                           doc.metadata?.filename;
            
            console.log('Image data found:', !!imageData);
            console.log('Image URL found:', imageUrl);
            console.log('Available doc keys:', Object.keys(doc));
            console.log('Available metadata keys:', doc.metadata ? Object.keys(doc.metadata) : 'No metadata');
            console.log('Full metadata object:', doc.metadata);
            console.log('Content type:', doc.content_type);
            console.log('Document type:', doc.metadata?.type);
            console.log('Image data length:', imageData ? imageData.length : 0);
            
            if (imageData) {
                // If we have base64 image data, display it
                // Determine the correct MIME type based on metadata or default to jpeg
                const mimeType = doc.metadata?.format || 
                                doc.metadata?.mime_type || 
                                doc.metadata?.content_type || 
                                'image/jpeg';
                
                contentPreview.innerHTML = `
                    <div class="image-preview">
                        <img src="data:${mimeType};base64,${imageData}" alt="Image preview" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                    </div>
                `;
            } else if (imageUrl && (imageUrl.startsWith('http://') || imageUrl.startsWith('https://') || imageUrl.startsWith('data:'))) {
                // If we have a valid URL, display it
                contentPreview.innerHTML = `
                    <div class="image-preview">
                        <img src="${imageUrl}" alt="Image preview" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                    </div>
                `;
            } else {
                // No image data available - try to fetch from backend
                console.log('No image data found, attempting to fetch from backend...');
                this.fetchImageFromBackend(doc.id, contentPreview);
            }
            
            // Mark summary as generated for images
            this.documentDetailsModal.summaryGenerated = true;
            
            // Set up event listeners for collapsible sections
            this.setupCollapsibleSections();
        }
    }

    fetchImageFromBackend(docId, contentPreview) {
        // Show loading state
        contentPreview.innerHTML = `
            <div class="no-content">
                <i class="fas fa-spinner fa-spin" style="font-size: 2rem; color: #6b7280; margin-bottom: 1rem;"></i>
                <p>Loading image from backend...</p>
            </div>
        `;
        
        // Try to fetch the image from backend using the dedicated image endpoint
        fetch(`/image/${docId}`)
            .then(response => response.json())
            .then(result => {
                if (result.image_data) {
                    const mimeType = result.metadata?.format || 
                                    result.metadata?.mime_type || 
                                    result.metadata?.content_type || 
                                    'image/jpeg';
                    
                    contentPreview.innerHTML = `
                        <div class="image-preview">
                            <img src="data:${mimeType};base64,${result.image_data}" alt="Image preview" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                        </div>
                    `;
                } else {
                    contentPreview.innerHTML = `
                        <div class="no-content">
                            <i class="fas fa-image" style="font-size: 2rem; color: #6b7280; margin-bottom: 1rem;"></i>
                            <p>Image preview not available</p>
                            <p style="font-size: 0.9rem; color: #6b7280;">No image data found in backend</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error fetching image from backend:', error);
                contentPreview.innerHTML = `
                    <div class="no-content">
                        <i class="fas fa-image" style="font-size: 2rem; color: #6b7280; margin-bottom: 1rem;"></i>
                        <p>Image preview not available</p>
                        <p style="font-size: 0.9rem; color: #6b7280;">Error: ${error.message}</p>
                    </div>
                `;
            });
    }

    loadAgentImages(container) {
        const imageContainers = container.querySelectorAll('.agent-image-container');
        imageContainers.forEach(container => {
            const imageId = container.getAttribute('data-image-id');
            const filename = container.getAttribute('data-filename');
            
            if (imageId) {
                this.loadAgentImage(container, imageId, filename);
            }
        });
    }

    loadAgentImage(container, imageId, filename) {
        // Show loading state
        container.innerHTML = `
            <div class="image-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Loading ${filename}...</p>
            </div>
        `;
        
        // Fetch image from backend
        fetch(`/image/${imageId}`)
            .then(response => response.json())
            .then(result => {
                if (result.image_data) {
                    const mimeType = result.metadata?.format || 
                                    result.metadata?.mime_type || 
                                    result.metadata?.content_type || 
                                    'image/jpeg';
                    
                    container.innerHTML = `
                        <div class="agent-image-preview">
                            <img src="data:${mimeType};base64,${result.image_data}" 
                                 alt="${filename}" 
                                 style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                            <div class="image-caption">${filename}</div>
                        </div>
                    `;
                } else {
                    container.innerHTML = `
                        <div class="image-error">
                            <i class="fas fa-image" style="font-size: 2rem; color: #6b7280; margin-bottom: 1rem;"></i>
                            <p>Image not available</p>
                            <p style="font-size: 0.9rem; color: #6b7280;">${filename}</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error loading agent image:', error);
                container.innerHTML = `
                    <div class="image-error">
                        <i class="fas fa-exclamation-triangle" style="font-size: 2rem; color: #dc2626; margin-bottom: 1rem;"></i>
                        <p>Error loading image</p>
                        <p style="font-size: 0.9rem; color: #6b7280;">${filename}</p>
                    </div>
                `;
            });
    }

    setupCollapsibleSections() {
        // Find all collapsible buttons and add event listeners
        const collapsibleButtons = document.querySelectorAll('.collapsible-btn[data-action="toggle-collapse"]');
        collapsibleButtons.forEach(button => {
            button.addEventListener('click', function() {
                const parent = this.parentElement;
                parent.classList.toggle('expanded');
            });
        });
        
        // Find all expand buttons for base64 data and add event listeners
        const expandButtons = document.querySelectorAll('.expand-btn[data-action="expand-base64"]');
        expandButtons.forEach(button => {
            button.addEventListener('click', () => {
                const key = button.getAttribute('data-key');
                const value = button.getAttribute('data-value');
                const parent = button.closest('.metadata-tag');
                const tagValue = parent.querySelector('.tag-value');
                
                // Replace the preview and button with the full content
                tagValue.innerHTML = `
                    <div class="base64-content">
                        <pre>${this.escapeHtml(value)}</pre>
                        <button class="collapse-btn" data-action="collapse-base64" data-key="${key}" data-value="${this.escapeHtml(value)}">
                            <i class="fas fa-compress-alt"></i> Hide content
                        </button>
                    </div>
                `;
                
                // Add event listener to the new collapse button
                const collapseBtn = tagValue.querySelector('.collapse-btn');
                collapseBtn.addEventListener('click', () => {
                    const byteEstimate = Math.round(value.length * 0.75);
                    tagValue.innerHTML = `
                        <span class="base64-preview">${byteEstimate} bytes</span>
                        <button class="expand-btn" data-action="expand-base64" data-key="${key}" data-value="${this.escapeHtml(value)}">
                            <i class="fas fa-expand-alt"></i> Show content
                        </button>
                    `;
                    
                    // Re-add event listener to the new expand button
                    const newExpandBtn = tagValue.querySelector('.expand-btn');
                    newExpandBtn.addEventListener('click', arguments.callee);
                });
            });
        });
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
        const visualizationContent = document.getElementById('visualizationContent');
        const visualizationResizeHandle = document.getElementById('visualizationResizeHandle');
        const documentsVisualization = document.getElementById('documentsVisualization');
        const toggleBtn = document.getElementById('visualizationToggleBtn');
        
        this.isVisualizationVisible = !this.isVisualizationVisible;
        localStorage.setItem('ragme-visualization-visible', this.isVisualizationVisible.toString());
        
        if (this.isVisualizationVisible) {
            visualizationContent.style.display = 'block';
            visualizationResizeHandle.style.display = 'flex';
            documentsVisualization.style.height = '20vh'; // Restore original height
            documentsVisualization.style.minHeight = '200px';
            toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
            
            // D3.js is now loaded synchronously, so we can call updateVisualization immediately
            this.updateVisualization();
        } else {
            visualizationContent.style.display = 'none';
            visualizationResizeHandle.style.display = 'none';
            documentsVisualization.style.height = 'auto'; // Collapse to header height only
            documentsVisualization.style.minHeight = 'auto';
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
        // Ensure socket is connected before requesting vector DB info
        if (this.socket && this.socket.connected) {
            this.socket.emit('get_vector_db_info');
        } else {
            // If socket is not connected, retry after a short delay
            setTimeout(() => {
                this.loadVectorDbInfo();
            }, 1000);
        }
    }

    async loadVectorDbInfoFromBackend() {
        try {
            const response = await fetch('http://localhost:8021/config');
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success' && data.config.vector_database) {
                    this.vectorDbInfo = {
                        dbType: data.config.vector_database.type,
                        type: data.config.vector_database.type,
                        collections: data.config.vector_database.collections || []
                    };
                    this.updateVectorDbInfoDisplay();
                    
                    // Update Settings modal if it's open - but don't override if we just set it
                    const settingsModal = document.getElementById('settingsModal');
                    if (settingsModal && settingsModal.classList.contains('show')) {
                        const vectorDbElement = document.getElementById('settingsVectorDbType');
                        // Only update if it's not already set to a valid value
                        if (vectorDbElement && (vectorDbElement.textContent === '-' || vectorDbElement.textContent === 'Loading...')) {
                            vectorDbElement.textContent = this.vectorDbInfo.type || '-';
                        }
                    }
                }
            }
        } catch (error) {
            console.warn('Failed to load vector DB info from backend:', error);
        }
    }

    async loadVectorDbInfoForSettings() {
        const vectorDbElement = document.getElementById('settingsVectorDbType');
        if (!vectorDbElement) return;
        
        // Show loading state
        vectorDbElement.textContent = 'Loading...';
        
        try {
            const response = await fetch('http://localhost:8021/config');
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success' && data.config.vector_database && data.config.vector_database.type) {
                    const dbType = data.config.vector_database.type;
                    vectorDbElement.textContent = dbType;
                    
                    // Also update the global vectorDbInfo
                    this.vectorDbInfo = {
                        dbType: dbType,
                        type: dbType,
                        collections: data.config.vector_database.collections || []
                    };
                } else {
                    vectorDbElement.textContent = 'Not configured';
                }
            } else {
                vectorDbElement.textContent = 'Error loading';
            }
        } catch (error) {
            vectorDbElement.textContent = 'Error loading';
        }
    }

    updateVectorDbInfoDisplay() {
        const vectorDbInfoElement = document.getElementById('vectorDbInfo');
        const vectorDbTypeElement = document.getElementById('vectorDbType');
        const vectorDbCollectionElement = document.getElementById('vectorDbCollection');
        
        if (!this.settings.showVectorDbInfo) {
            vectorDbInfoElement.style.display = 'none';
            return;
        }
        
        // Update connection status styling
        if (this.connectionStatus && !this.connectionStatus.isConnected) {
            vectorDbInfoElement.classList.add('connection-error');
        } else {
            vectorDbInfoElement.classList.remove('connection-error');
        }
        
        if (this.vectorDbInfo) {
            vectorDbTypeElement.textContent = this.vectorDbInfo.dbType || this.vectorDbInfo.type || 'Unknown';

            // Render collections with icons
            const collections = this.vectorDbInfo.collections || [];
            if (Array.isArray(collections) && collections.length > 0) {
                const parts = collections.map(col => {
                    const type = (col && col.type) || 'text';
                    const name = (col && col.name) || 'Unknown';
                    const iconClass = type === 'image' ? 'fas fa-image' : 'fas fa-file-alt';
                    return `<span class="collection-item"><i class="${iconClass}"></i> ${this.escapeHtml(name)}</span>`;
                });
                vectorDbCollectionElement.innerHTML = parts.join(' ');
            } else {
                // Backward compatibility: single collectionName
                const single = this.vectorDbInfo.collectionName || 'Unknown';
                vectorDbCollectionElement.textContent = single;
            }
            vectorDbInfoElement.style.display = 'flex';
        } else {
            // Show loading state with better visual feedback
            vectorDbTypeElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            vectorDbCollectionElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            vectorDbInfoElement.style.display = 'flex';
            
            // Retry loading vector DB info if not available after a delay
            if (!this.vectorDbInfoRetryTimeout) {
                this.vectorDbInfoRetryTimeout = setTimeout(() => {
                    this.vectorDbInfoRetryTimeout = null;
                    if (!this.vectorDbInfo) {
                        console.log('Retrying vector DB info load...');
                        this.loadVectorDbInfo();
                    }
                }, 3000); // Retry after 3 seconds
            }
        }
    }

    deleteDocument(docIndex) {
        // Get the grouped documents to find the correct document
        const groupedDocuments = this.groupDocumentsByBaseUrl(this.documents);
        const groupedDoc = groupedDocuments[docIndex];
        
        if (!groupedDoc) {
            this.showNotification('error', 'Document not found');
            return;
        }
        
        const isImage = groupedDoc.content_type === 'image';
        const contentType = isImage ? 'image' : 'document';
        
        if (confirm(`Are you sure you want to delete this ${contentType}? This action cannot be undone.`)) {
            console.log('Deleting document:', docIndex, groupedDoc);
            
            // Check if this is a chunked document that needs special handling
            if (groupedDoc.isGroupedChunks && groupedDoc.totalChunks > 1) {
                // Delete all chunks of this document
                this.deleteChunkedDocument(groupedDoc);
            } else {
                // Delete single document - find the actual document index in the original array
                const actualDocIndex = groupedDoc.docIndex !== undefined ? groupedDoc.docIndex : 
                                     this.documents.findIndex(doc => doc.id === groupedDoc.id);
                this.deleteSingleDocument(actualDocIndex, groupedDoc);
            }
        }
    }

    deleteChunkedDocument(groupedDoc) {
        console.log('Deleting chunked document:', groupedDoc);
        
        // Get all chunks that belong to this document
        let chunksToDelete;
        
        if (groupedDoc.chunks && groupedDoc.chunks.length > 0) {
            // Use the chunks from the grouped document
            chunksToDelete = groupedDoc.chunks;
        } else {
            // Fallback: find chunks in the original documents array
            chunksToDelete = this.documents.filter(doc => {
                if (doc.metadata?.is_chunk && doc.metadata?.total_chunks) {
                    // Extract base URL from chunk URL
                    const chunkBaseUrl = doc.url.split('#')[0];
                    const groupBaseUrl = groupedDoc.baseUrl;
                    return chunkBaseUrl === groupBaseUrl;
                }
                return false;
            });
        }
        
        console.log('Found chunks to delete:', chunksToDelete.length);
        
        // Delete all chunks
        const deletePromises = chunksToDelete.map(chunk => {
            const endpoint = chunk.content_type === 'image' ? `/delete-image/${chunk.id}` : `/delete-document/${chunk.id}`;
            return fetch(endpoint, { method: 'DELETE' })
                .then(response => response.json());
        });
        
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
                    
                    // Also remove any remaining documents that might be related to this grouped document
                    // This handles cases where the grouping might not have captured all related documents
                    const remainingRelatedDocs = this.documents.filter(doc => {
                        if (doc.metadata?.is_chunk && doc.metadata?.total_chunks) {
                            const chunkBaseUrl = doc.url.split('#')[0];
                            const groupBaseUrl = groupedDoc.baseUrl;
                            return chunkBaseUrl === groupBaseUrl;
                        }
                        return false;
                    });
                    
                    remainingRelatedDocs.forEach(doc => {
                        const index = this.documents.findIndex(d => d.id === doc.id);
                        if (index !== -1) {
                            this.documents.splice(index, 1);
                        }
                    });
                    
                    console.log(`Deleted ${successCount} chunks. New document count:`, this.documents.length);
                    
                    // Re-render the documents list
                    this.renderDocuments();
                    
                    // Update visualization to reflect the changes
                    this.updateVisualization();
                    
                    // Force a refresh of the documents list to ensure everything is in sync
                    setTimeout(() => {
                        this.loadDocuments();
                    }, 500);
                    
                                    // Show success notification
                const contentType = groupedDoc.content_type === 'image' ? 'image' : 'document';
                this.showNotification('success', `Deleted ${contentType} with ${successCount} chunks successfully`);
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
        console.log('deleteSingleDocument called with:', { docIndex, docId: doc.id, docType: doc.content_type });
        
        // Determine the appropriate endpoint based on content type
        const endpoint = doc.content_type === 'image' ? `/delete-image/${doc.id}` : `/delete-document/${doc.id}`;
        
        // Call backend API to delete the document/image using the appropriate endpoint
        fetch(endpoint, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(result => {
            console.log('Delete result:', result);
            if (result.status === 'success') {
                // Don't remove from local array immediately - let the server refresh handle it
                console.log('Delete successful, refreshing data from server...');
                console.log('About to call loadDocuments()...');
                
                // Force a refresh of the documents list to ensure everything is in sync
                this.loadDocuments();
                console.log('loadDocuments() called');
                
                // Show success notification
                const contentType = doc.content_type === 'image' ? 'image' : 'document';
                this.showNotification('success', `${contentType.charAt(0).toUpperCase() + contentType.slice(1)} deleted successfully`);
            } else {
                // Show error notification
                const contentType = doc.content_type === 'image' ? 'image' : 'document';
                this.showNotification('error', result.message || `Failed to delete ${contentType}`);
            }
        })
        .catch(error => {
            console.error('Error deleting document:', error);
            const contentType = doc.content_type === 'image' ? 'image' : 'document';
            this.showNotification('error', `Failed to delete ${contentType}. Please try again.`);
        });
    }

    deleteDocumentFromDetails() {
        const modal = document.getElementById('documentDetailsModal');
        const docIndex = parseInt(modal.dataset.docIndex);
        
        // Get the grouped documents to find the correct document
        const groupedDocuments = this.groupDocumentsByBaseUrl(this.documents);
        
        if (isNaN(docIndex) || docIndex < 0 || docIndex >= groupedDocuments.length) {
            this.showNotification('error', 'Invalid document index');
            return;
        }

        const groupedDoc = groupedDocuments[docIndex];
        const isImage = groupedDoc.content_type === 'image';
        const contentType = isImage ? 'image' : 'document';
        
        if (confirm(`Are you sure you want to delete this ${contentType}? This action cannot be undone.`)) {
            // Check if this is a chunked document that needs special handling
            if (groupedDoc.isGroupedChunks && groupedDoc.totalChunks > 1) {
                // Delete all chunks of this document
                this.deleteChunkedDocument(groupedDoc);
            } else {
                // Delete single document - find the actual document index in the original array
                const actualDocIndex = groupedDoc.docIndex !== undefined ? groupedDoc.docIndex : 
                                     this.documents.findIndex(doc => doc.id === groupedDoc.id);
                this.deleteSingleDocument(actualDocIndex, groupedDoc);
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
                
                // Extract base filename from URL like "file://ragme-io.pdf#chunk-4"
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
        const fileContent = `# RAGme.io Response

${userMessage ? `**Query:** ${userMessage.content}

` : ''}**Response:**

${message.content}

---
*Generated by ${this.config?.application?.title || 'RAGme.io Assistant'} on ${new Date().toLocaleString()}*
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
            subjectInput.value = 'RAGme.io Response';
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
        let fileContent = `# RAGme.io Chat: ${chat.title}

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
*Generated by ${this.config?.application?.title || 'RAGme.io Assistant'} on ${new Date().toLocaleString()}*
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
        subjectInput.value = chat.title || 'RAGme.io Chat';
        
        // Create email body with entire conversation
        let emailBody = `RAGme.io Chat: ${chat.title}

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
Generated by ${this.config?.application?.title || 'RAGme.io Assistant'} on ${new Date().toLocaleString()}`;
        
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

    isDocumentNew(dateAdded) {
        if (!dateAdded) return false;
        
        try {
            const addedDate = new Date(dateAdded);
            const now = new Date();
            const timeDiff = now.getTime() - addedDate.getTime();
            const hoursDiff = timeDiff / (1000 * 60 * 60);
            
            return hoursDiff <= 24;
        } catch (error) {
            console.error('Error parsing date:', error);
            return false;
        }
    }

    // Voice-to-text functionality
    toggleVoiceInput() {
        if (!this.speechSupported) {
            this.showNotification('Voice input is not supported in your browser', 'error');
            return;
        }

        if (this.isRecording) {
            this.stopVoiceInput();
        } else {
            this.startVoiceInput();
        }
    }

    startVoiceInput() {
        if (!this.speechRecognition) {
            this.initializeSpeechRecognition();
        }

        try {
            this.speechRecognition.start();
            this.isRecording = true;
            this.updateMicrophoneButton(true);
            this.showNotification('Listening... Speak now', 'info');
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            this.showNotification('Error starting voice input', 'error');
        }
    }

    stopVoiceInput() {
        if (this.speechRecognition) {
            this.speechRecognition.stop();
        }
        this.isRecording = false;
        this.updateMicrophoneButton(false);
    }

    initializeSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.speechRecognition = new SpeechRecognition();
        
        this.speechRecognition.continuous = false;
        this.speechRecognition.interimResults = false;
        this.speechRecognition.lang = 'en-US';

        this.speechRecognition.onstart = () => {
            console.log('Speech recognition started');
            this.isRecording = true;
            this.updateMicrophoneButton(true);
        };

        this.speechRecognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('Speech recognition result:', transcript);
            
            const chatInput = document.getElementById('chatInput');
            chatInput.value = transcript;
            
            // Trigger the input event to resize the textarea
            chatInput.dispatchEvent(new Event('input'));
            
            this.showNotification('Voice input received', 'success');
        };

        this.speechRecognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.isRecording = false;
            this.updateMicrophoneButton(false);
            
            let errorMessage = 'Voice input error';
            if (event.error === 'no-speech') {
                errorMessage = 'No speech detected. Please try again.';
            } else if (event.error === 'audio-capture') {
                errorMessage = 'Microphone access denied. Please check permissions.';
            } else if (event.error === 'not-allowed') {
                errorMessage = 'Microphone access denied. Please allow microphone access.';
            }
            
            this.showNotification(errorMessage, 'error');
        };

        this.speechRecognition.onend = () => {
            console.log('Speech recognition ended');
            this.isRecording = false;
            this.updateMicrophoneButton(false);
        };
    }

    updateMicrophoneButton(isRecording) {
        const microphoneBtn = document.getElementById('microphoneBtn');
        const icon = microphoneBtn.querySelector('i');
        
        if (isRecording) {
            microphoneBtn.classList.add('recording');
            icon.className = 'fas fa-microphone-slash';
            microphoneBtn.title = 'Stop recording';
        } else {
            microphoneBtn.classList.remove('recording');
            icon.className = 'fas fa-microphone';
            microphoneBtn.title = 'Voice input';
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            max-width: 300px;
            word-wrap: break-word;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            animation: slideIn 0.3s ease-out;
        `;
        
        // Set background color based on type
        switch (type) {
            case 'success':
                notification.style.backgroundColor = '#28a745';
                break;
            case 'error':
                notification.style.backgroundColor = '#dc3545';
                break;
            case 'warning':
                notification.style.backgroundColor = '#ffc107';
                notification.style.color = '#212529';
                break;
            default:
                notification.style.backgroundColor = '#17a2b8';
        }
        
        // Add to page
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, 3000);
    }

    resetSettings() {
        // Reset settings to default values
        this.settings = {
            maxDocuments: 50,
            autoRefresh: true,
            refreshInterval: 30000, // 30 seconds
            maxTokens: 4000,
            temperature: 0.7,
            showVectorDbInfo: true,
            maxDocuments: 10,
            documentOverviewEnabled: true,
            documentOverviewVisible: true,
            documentListCollapsed: false,
            documentListWidth: 35,
            chatHistoryCollapsed: false,
            chatHistoryWidth: 10
        };
        
        // Save to localStorage
        localStorage.setItem('ragme-settings', JSON.stringify(this.settings));
        localStorage.setItem('ragme-date-filter', this.currentDateFilter);
        localStorage.setItem('ragme-max-documents', this.settings.maxDocuments.toString());
        localStorage.setItem('ragme-document-overview-enabled', this.settings.documentOverviewEnabled.toString());
        localStorage.setItem('ragme-document-overview-visible', this.settings.documentOverviewVisible.toString());
        localStorage.setItem('ragme-document-list-collapsed', this.settings.documentListCollapsed.toString());
        localStorage.setItem('ragme-document-list-width', this.settings.documentListWidth.toString());
        localStorage.setItem('ragme-chat-history-collapsed', this.settings.chatHistoryCollapsed.toString());
        localStorage.setItem('ragme-chat-history-width', this.settings.chatHistoryWidth.toString());
        
        this.hideModal('settingsModal');
        this.showNotification('success', 'Settings reset to default');
        
        // Apply UI changes
        this.applyUIConfiguration();
        
        // Reload documents with new settings
        this.loadDocuments();
    }

    switchSettingsTab(tab) {
        // Remove active class from all tabs
        document.querySelectorAll('.settings-tab-btn').forEach(btn => btn.classList.remove('active'));
        
        // Add active class to the clicked tab
        const tabButton = document.querySelector(`[data-settings-tab="${tab}"]`);
        if (tabButton) {
            tabButton.classList.add('active');
        }
        
        // Update tab content
        document.querySelectorAll('.settings-tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const tabContent = document.getElementById(tab);
        if (tabContent) {
            tabContent.classList.add('active');
        }
    }
}

// Simple markdown parser fallback if marked is not available
function simpleMarkdownParser(text) {
    if (typeof marked !== 'undefined') {
        // First handle our custom image format
        text = text.replace(/\[IMAGE:([^:]+):([^\]]+)\]/g, function(match, imageId, filename) {
            return `<div class="agent-image-container" data-image-id="${imageId}" data-filename="${filename}">
                <div class="image-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading image...</p>
                </div>
            </div>`;
        });
        
        return marked.parse(text);
    }
    
    // Fallback simple markdown parser
    return text
        .replace(/\[IMAGE:([^:]+):([^\]]+)\]/g, function(match, imageId, filename) {
            return `<div class="agent-image-container" data-image-id="${imageId}" data-filename="${filename}">
                <div class="image-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading image...</p>
                </div>
            </div>`;
        })
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