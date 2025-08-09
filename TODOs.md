# TODOs

## **OPENED**

### bugs
* test: integration --agents falling with

```bash
ap_urls PASSED [100%]

=================================== FAILURES ===================================
_______________________________ test_ragme_init ________________________________

    def test_ragme_init():
        with (
            patch("src.ragme.ragme.create_vector_database") as mock_create_db,
            patch("llama_index.llms.openai.OpenAI") as mock_openai,
            patch("weaviate.agents.query.QueryAgent") as mock_query_agent,
            patch("llama_index.core.agent.workflow.FunctionAgent") as mock_function_agent,
            patch.dict(
                "os.environ",
                {"VECTOR_DB_TYPE": "weaviate", "VECTOR_DB_COLLECTION_NAME": "RagMeDocs"},
            ),
        ):
            # Setup mocks
            mock_db_instance = MagicMock()
            mock_create_db.return_value = mock_db_instance
            mock_query_agent.return_value = MagicMock()
            mock_function_agent.return_value = MagicMock()
            mock_openai.return_value = MagicMock()
    
            # Mock the vector database methods
            mock_db_instance.setup = MagicMock()
            mock_db_instance.create_query_agent = MagicMock(return_value=MagicMock())
    
            ragme = RagMe()
            # Collection name should come from config, which could be "Viewfinder", "RagMeDocs",
            # or "test_integration" if integration tests have been run
>           assert ragme.collection_name in ["RagMeDocs", "Viewfinder", "test_integration"]
E           AssertionError: assert '${VECTOR_DB_COLLECTION_NAME}' in ['RagMeDocs', 'Viewfinder', 'test_integration']
E            +  where '${VECTOR_DB_COLLECTION_NAME}' = <src.ragme.ragme.RagMe object at 0x7f0ee8002920>.collection_name

tests/test_ragme.py:63: AssertionError
=========================== short test summary info ============================
FAILED tests/test_ragme.py::test_ragme_init - AssertionError: assert '${VECTOR_DB_COLLECTION_NAME}' in ['RagMeDocs', 'Viewfinder', 'test_integration']
 +  where '${VECTOR_DB_COLLECTION_NAME}' = <src.ragme.ragme.RagMe object at 0x7f0ee8002920>.collection_name
============ 1 failed, 85 passed, 3 deselected, 2 warnings in 5.46s ============
Error: Process completed with exit code 1.
```

* a query for "detailed report on RDI conference" w/o RDI conference document results in query agent finding documents when it should not:
```bash
2025-08-07 15:48:02 - Dispatching to QueryAgent: 'RDI conference report'
2025-08-07 15:48:02 - QueryAgent received query: 'RDI conference report'
2025-08-07 15:48:02 - QueryAgent searching vector database with query: 'RDI conference report' (top_k=5)
2025-08-07 15:48:02 - QueryAgent found 5 documents
2025-08-07 15:48:02 - QueryAgent generating answer with LLM for query: 'RDI conference report'
2025-08-07 15:48:12 - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-08-07 15:48:12 - QueryAgent returning result for query: 'RDI conference report'
2025-08-07 15:48:13 - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-08-07 15:48:22 - RagMeAgent got response: <class 'llama_index.core.agent.workflow.workflow_events.AgentOutput'> - Here is a detailed report on the RDI (Retrieval-Augmented Document Intelligence) conference, highlig...
INFO:     127.0.0.1:52582 - "POST /query HTTP/1.1" 200 OK
```
But a query of: "who is maximilien"

results in:
```bash
🤖
The documents do not contain specific information about an individual named "Maximilien." If you are looking for information about a specific Maximilien (such as a historical figure or a character), please provide more context or 
specify which Maximilien you are referring to.
```

* URL link in chat responses is incorrect when fetching from URL documents
* add citations when query response results in more than one document

### bugs - mobile
* right pane shows as purple block when collapse on mobile (iPhone)
* the chat text input is hidden on mobile (iPhone). Need to flip to horizontal and touch bottom to be able to make text input visible and usable

### tests
* test with local weaviate 
* test with local milvus

### features

#### query accuracy
* queries about "RAGme" with research document about RAG paper but no RAGme doc results in hallucination -- correct result is no document on RAGme:

```bash
👤
what is ragme-ai

🤖
RAGme-AI, as referenced in the documents, is closely related to the concept of Retrieval-Augmented Generation (RAG) in the context of artificial intelligence, particularly for regulatory science and compliance concerning medical devices.

Overview of RAGme-AI:
Automated Compliance: RAGme-AI utilizes a modular AI system that automates the determination of applicable regulatory standards for medical devices based on their descriptions. It retrieves relevant standards from a curated database and classifies them as Mandatory, Recommended, or Not Applicable, providing traceable justifications for each classification.
Key Features:
Cross-Jurisdictional Reasoning: The system can analyze and reconcile regulatory standards from different countries, such as the U.S. and China, helping to resolve conflicts and providing clear justifications for applicable standards.

Performance Metrics: The system has demonstrated a classification accuracy of 73% and a Top-5 retrieval recall of 87%, indicating its effectiveness in identifying relevant regulatory standards.

End-to-End System: It is described as an end-to-end system designed for standard applicability reasoning, which enhances the scalability and interpretability of AI-supported regulatory processes.

In summary, RAGme-AI represents the application of RAG methodologies within AI systems to improve compliance and regulatory understanding, particularly in the medical device domain. If you are looking for a specific product or entity named "RAGme-AI" outside of this context, the documents do not provide that information.
```

#### agents
* implement OpenAI agents version of the current agents
* allow new OpenAI agents to be configurable vs LlamaIndex agents

#### frontend
* complete MCP authentication flow

* settings to enable / disable saving uploaded documents in doc server
* doc details card should allow viewing of doc and chunks

#### MCP servers
* mail - gmail support to read / write mails
* todos - google task read / write
* cloud drives - google drive / microsoft one drive/ dropbox
* twillio (phone messages) - add documents and links using messages with a phone number

#### backend
* add sqllite to store and retrieve user preferences

* MCP tool servers integration and authentication
* MCP agent to call and use MCP server tools depending on prompts

* gateway agent and prompt tuning to figure out if user prompt should be handled by Query / Function / MCP agent

* graph db - build knowledge graph of documents / content via Neo4J
* graph agent - queries graph db with text -> cypher query to complement query agent results

* document server - for documents added with "+ Add Content" upload keep copy on doc server. Add settings to enable / disable this

#### content types
* images - add images from URLs and upload
* support extracting metadata from images
* support extracting text from images and add to metadata, eg, image of a slide
* extract images from documents and upload to ImagesDocs collection with metadata to link back to document 

#### use cases
* support agent to collect images and docs for period of time and create report, e.g., conference slide photos

#### saas
* support multiple users 
* authorize and authenticate users with OAuth -- Google and Github
* store authenticated user's preferences
* allow non-authenticated users limited access: 10 documents and 10 queries per day

#### cloud deployment
* containerize different services: create Dockerfile
* create basic k8s deployment with services on kind
* test k8s deployment on cloud: AWS or GCP

#### more content types
* voice memos - `.wav` files and other formats
* podcasts - link to podcast files

* blogs (RSS) subscriptions - any RSS feed

* videos (YouTube) - link to youtube videos

#### insights
* daily summaries - create a summary of a particular day's activity
* daily insights - generate insight from documents added in a particular day
* monthly versions - monthly versions of summaries and insights

#### more MCP servers
* whatsapp integration (explore if possible)
* slack channels - add documents and links using slack messages
* X / Twitter - add documents and links from X account posts

### nice to have
* a2a support to discover and call other external agents to do work

---

## **COMPLETED**

* ✅ **COMPLETED** - make sure the VDB and collection name is showing correctly on top bar using the config [Fixed top bar vector database display to show correct collection name by implementing configuration-based vector DB info instead of environment variables. Root causes identified and resolved: (1) Frontend was using stale environment variables from Node.js startup instead of live configuration, (2) Backend config endpoint didn't include vector database information. Solution: Added vector_database field to backend /config endpoint with type and collection_name from active configuration, updated frontend TypeScript to read vector DB info from config instead of process.env, and added proper TypeScript interface for vector_database field. Result: Top bar now correctly displays "Vector DB: weaviate | Collection: Viewfinder" when using Viewfinder.ai environment, automatically updating when environment is switched]

* ✅ **COMPLETED** - bug: switching .env APPLICATION_* and other settings not taking effect [Fixed critical environment variable configuration issues that prevented proper application switching between different deployments (e.g., RAGme vs Viewfinder.ai). Root causes identified and resolved: (1) Wrong environment variable syntax in config.yaml - changed from `{$VAR_NAME}` to `${VAR_NAME}` throughout configuration files, (2) Missing dynamic VECTOR_DB_TYPE selection - added environment variable mapping in vector_db_factory.py to translate between environment values (weaviate) and config database names (weaviate-cloud), (3) Fixed config.yaml.example with same syntax corrections and proper formatting. Solution enables seamless switching between different application environments by simply changing .env file and restarting services. Verified with comprehensive testing: configuration validation passes, vector database connects to correct collections, API shows proper branding, environment variables are correctly substituted, and all linting checks pass. Now switching from RAGme (RagMeDocs collection) to Viewfinder.ai (Viewfinder collection) works perfectly with ./stop.sh && ./start.sh]

* ✅ **COMPLETED** - add agents and apis level integration tests [Implemented comprehensive integration tests for both API and Agent levels with complete scenario testing including empty collection verification, document addition/removal, and query validation. Created test files: tests/integration/test_apis.py, tests/integration/test_agents.py, tests/integration/run_integration_tests.py, tests/integration/config_manager.py, and tools/test-integration-agents.sh for easy test execution. Added configuration management to prevent test pollution by backing up config.yaml, modifying it to use test_integration collection, and restoring it after tests complete. Added bypass_delete_confirmation feature flag to skip confirmation prompts during tests, ensuring clean test execution without user interaction]

* ✅ **COMPLETED** - deleting non existing (or already deleted doc) should result in a message that doc is not in collection [Fixed URL-based document deletion by implementing proper find_document_by_url method that handles Weaviate API changes and URL fragments. Enhanced matching logic to support exact matches, base URL matches (without fragments), and filename-only matches for file:// URLs. Now properly finds and deletes documents by URL with accurate error messages when documents don't exist]

* ✅ **COMPLETED** - Enhanced delete operation detection with LLM-based approach [Replaced keyword-based detection with intelligent LLM-based analysis that can understand context and various phrasings. Features include: JSON-structured LLM responses for operation classification, fallback to keyword detection if LLM fails, support for abbreviated forms like "del", "rm", etc., comprehensive test coverage with mocked LLM responses, and robust error handling]

* ✅ **COMPLETED** - make sure to confirm with user before executing delete docs tools [Implemented comprehensive confirmation system for delete operations in RagMeAgent. Features include: confirmation tracking per chat session, different confirmation levels for single documents vs collections/multiple documents, automatic confirmation state reset on new chat sessions, clear warning messages with emoji indicators, and proper API integration with frontend chat management]

* ✅ **COMPLETED** - add memory to chat agent [Implemented LlamaIndex ReActAgent with ChatMemoryBuffer for intelligent query routing and conversation memory]

* ✅ **COMPLETED** - refactor: RagMeAgent to make tools, and agents explicit and separated from the RagMeAgent [Implemented three-agent architecture: RagMeAgent (dispatcher), FunctionalAgent (tool operations), QueryAgent (content queries)]

* ✅ **COMPLETED** - bug: queries for functional agent are not flowing to function / tool, e.g., "list", "list docs" not calling the list_documents tool [Fixed by implementing proper query routing in FunctionalAgent with LlamaIndex FunctionAgent]

* ✅ **COMPLETED** - Make RAGme work with configurable collection name(s) and LLMs, and MCP servers [Comprehensive configuration system implemented with config.yaml supporting multiple vector databases (Weaviate local/cloud, Milvus local/cloud), configurable LLM models for different agents, MCP server configurations, and complete environment variable support]

* ✅ **COMPLETED** - Make other active parts of RAGme that could be changed configurable (e.g., name, query agent) [Full application generalization implemented: configurable app name/title/description, network ports, frontend UI settings, client branding, feature flags, security settings, and all agent configurations. Includes config validation tool and comprehensive documentation]

* ✅ **COMPLETED** - Add compile-frontend command to start.sh script [Added `./start.sh compile-frontend` command to easily recompile frontend TypeScript after configuration or code changes, without needing to restart the server. Includes helpful usage documentation and examples.]

* ✅ **COMPLETED** - Move test-integration.sh to tools directory for better organization [Organizational improvement to consolidate all utility scripts in tools/ directory, updated all references in documentation and test scripts]

* ✅ **COMPLETED** - README and other docs seems to have repetitions

* ✅ **COMPLETED** - Adding large PDF doc via + Add Content seem to cause new doc to not be queryable. Implement semantic search

**Root Cause**: The querying mechanism was using simple keyword matching instead of proper vector similarity search, and the FunctionAgent was not properly executing function calls, returning function call text instead of actual results.

**Solution Implemented**:
1. **Added proper vector search method**: Implemented `search()` method in all vector database implementations (Weaviate, Weaviate Local, and Milvus) that uses proper vector similarity search
2. **Always use query_agent with fallback**: Modified `ragme_agent.py` to always use the query_agent function first, with fallback to direct vector search
3. **Fixed FunctionAgent execution**: Updated the `run` method to properly handle `ToolOutput` objects from LlamaIndex FunctionTools
4. **LLM summarization of chunks**: Added `_summarize_chunks_with_llm()` method that uses the LLM to generate coherent summaries of relevant chunks instead of showing raw text
5. **Enhanced response quality**: Now provides well-structured, contextual summaries that directly answer the user's query
6. **Added fallback mechanism**: If LLM summarization fails, falls back to raw content for robustness

**Key Improvements**:
- **Semantic search**: Uses proper vector similarity search instead of keyword matching
- **LLM summarization**: Chunks are summarized by the LLM in the context of the user's query
- **Better UX**: Responses are coherent, well-structured, and directly answer the question
- **Robust fallbacks**: Multiple fallback mechanisms ensure the system always works

**Testing**: Verified that large PDF files like `2506.18511v1.pdf` (83 chunks) now return excellent, coherent summaries for queries like "what do you know about RAG-based framework" and "what is Standard Applicability Judgment".

* ✅ **COMPLETED** - AI summary regeneration during periodic refresh when popup is open

**Root Cause**: When the document details popup was open and periodic document refresh occurred, the `renderDocuments()` method would recreate document cards with new click handlers, causing `showDocumentDetails()` to be called again, which triggered `fetchDocumentSummary()` again, leading to the stuck "Still generating summary..." message.

**Solution Implemented**:
1. **Modal State Tracking**: Added `documentDetailsModal` object to track modal state, current document ID, and summary generation status
2. **Duplicate Prevention**: Check if the same document is already open before generating AI summary
3. **Summary Generation Tracking**: Mark summary as generated to prevent regeneration for the same document
4. **Modal State Reset**: Reset modal state when popup is closed (via close button, overlay click, or escape key)
5. **Render Prevention**: Skip document rendering when modal is open to prevent interference
6. **Request Deduplication**: Added `summaryInProgress` flag to prevent multiple simultaneous summary requests

**Key Improvements**:
- **Prevents Duplicate Summaries**: AI summary is only generated once per document session
- **Better UX**: No more stuck "Still generating summary..." messages
- **State Management**: Proper tracking of modal state and document sessions
- **Clean Reset**: Modal state is properly reset when closed
- **Render Interference Prevention**: Document list rendering is skipped when modal is open
- **Timeout Management**: Proper timeout handling prevents conflicting messages

* ✅ **COMPLETED** - New frontend UI

Successfully created a new modern UI for RAGme.ai Assistant with the following features:

**Implementation Details**:
- **Three-pane layout** with resizable and collapsible sidebars
- **Right pane**: "Recent Documents" showing documents ordered by recency
- **Document details**: Click to view name, ID, metadata, summary, date added, and vector DB collection
- **App name**: 🤖 RAGme.ai Assistant
- **D3.js visualization**: Document type charts and analytics
- **Markdown formatting**: Chat results with copy functionality on hover
- **Modern UI**: Beautiful gradients, animations, and responsive design
- **Frontend directory**: `./frontend/` with TypeScript, Express, Socket.IO
- **Process management**: Updated `./start.sh` and `./stop.sh` to manage the new frontend
- **Port configuration**: New frontend on port 3020, legacy UI on port 8020
- **API integration**: WebSocket communication with RAGme.ai backend
- **Documentation**: Updated README and created frontend-specific docs
- All tests passing (`./test.sh`)
- All linting checks passing (`./tools/lint.sh`)
- TypeScript compilation successful
- Modern browser compatibility

* ✅ **COMPLETED** - Show Documents in different panes: recent, this week, this month, this year

Successfully implemented document date filtering in the Documents pane:

**Implementation Details**:
- **Date Filter Dropdown**: Added dropdown selector in Documents sidebar header with options: Current, This Month, This Year, All
- **Backend API Enhancement**: Updated `/list-documents` endpoint to support `date_filter` parameter
- **Date Filtering Logic**: Implemented server-side filtering based on document `date_added` metadata
- **Frontend Integration**: Updated frontend to send date filter parameter and handle filtered results
- **Persistent Preferences**: Date filter choice is saved in localStorage and restored on page reload
- **Visual Feedback**: Refresh button shows active filter in notifications
- **Smart Defaults**: Defaults to "Current" (this week) for better UX
- **Filter Options**: Current (last 7 days), This Month, This Year, All
- **Backend**: Added `filter_documents_by_date()` function in `api.py`
- **Frontend**: Updated `app.js` with date filter state management and event handlers
- **UI**: Added dropdown selector with CSS styling in `index.html` and `styles.css`
- **API**: Enhanced `/list-documents` endpoint with `date_filter` query parameter
- **Testing**: All unit and integration tests passing

* ✅ **COMPLETED** - Order document in document pane by order of their additions to the VDB

* ✅ **COMPLETED** - Add a "new" badge (upper right top) when a new document is added to make it stand out in list

* ✅ **COMPLETED** - Add a + to create New Chat easily as a shortcut to new Chat in hamburger menu

**Implementation Details**:
- **Quick New Chat Button**: Added "+" button between "Chat History" title and collapse button
- **Visual Design**: Dim by default (opacity 0.7), highlights in green on hover like save chat button
- **Tooltip**: "New chat" tooltip on hover for clear user guidance
- **Functionality**: Direct shortcut to createNewChat() function, same as hamburger menu
- **Responsive**: Works seamlessly with existing sidebar layout and mobile design
- **HTML**: Added button with FontAwesome plus icon in sidebar header
- **CSS**: Styled with hover effects matching existing save button design
- **JavaScript**: Connected to existing createNewChat() function via event listener
- **Testing**: All unit and integration tests passing
- **Linting**: All code quality checks passing

* ✅ **COMPLETED** - Show connection status in Vector DB info banner

Successfully implemented connection status monitoring for the Vector DB info banner:

**Implementation Details**:
- **Connection Status Tracking**: Monitors success/failure of periodic document refresh calls
- **Visual Error Indication**: Vector DB banner highlights in light red when connection fails
- **Pulsing Animation**: Subtle pulsing animation draws attention to connection issues
- **Automatic Recovery**: Banner returns to normal when connection is restored
- **Socket Event Handling**: Tracks both document refresh failures and socket disconnections
- **Real-time Updates**: Connection status updates immediately when issues occur
- **Connection Status Object**: Tracks `isConnected`, `lastSuccess`, `failureCount`, `lastFailure`
- **Event Monitoring**: Monitors `documents_listed` success/failure and socket connect/disconnect
- **CSS Styling**: Added `.connection-error` class with red highlighting and pulsing animation
- **Status Persistence**: Connection status maintained across auto-refresh cycles
- **Visual Feedback**: Red background, border, and text color for error state

* ✅ **COMPLETED** - Reorganize hamburger menu: Move chat management items into "Manage Chats" submenu

Successfully reorganized the hamburger menu to improve organization and prepare for future menu items:

**Implementation Details**:
- **Manage Chats Submenu**: Created a collapsible submenu containing all chat management items
- **Submenu Items**: New Chat, Clear Current Chat, Clear All History, Clear Everything
- **Visual Design**: Added chevron arrow that rotates when submenu is expanded
- **Settings Separation**: Kept Settings as a top-level menu item for easy access
- **Hover Functionality**: Submenu appears on hover with smooth transitions
- **Smart Timing**: 100ms delay prevents accidental submenu closure when moving mouse
- **Smooth Animations**: Added CSS transitions for submenu expand/collapse
- **Click Handling**: Proper event handling to prevent menu closure when clicking submenu items
- **HTML Structure**: Updated menu dropdown with submenu trigger and submenu container
- **CSS Styling**: Added styles for submenu trigger, submenu items, and arrow animations
- **JavaScript Logic**: Added hover event handlers with timeout management for smooth UX
- **Event Management**: Smart hover detection with delay to prevent accidental closure
- **Responsive Design**: Submenu works seamlessly on desktop and mobile

* ✅ **COMPLETED** - "recent / ideas" prompt popup button to give user quick way to start their first prompts

**Implementation Details**:
- Added button positioned to the left of chat input, using history icon
- Shows 5 sample prompts for new chats, shows 5 recent user prompts + 3 sample prompts for ongoing chats
- Popup positioned correctly and sized appropriately

* ✅ **COMPLETED** - "toolbox" button to pop checkable (selectable) list of enabled / disabled configured MCP tool servers

**Implementation Details**:
- Added toolbox button positioned to the left of the Recent Prompts button with toolbox icon
- Created MCP tools popup with similar styling to recent prompts popup
- Implemented 5 mock MCP servers: Google GDrive, Dropbox Drive, Google Mail, Twilio, and RAGme Test
- Each server has appropriate icon, name, and enable/disable toggle aligned to the right
- **Backend API Integration**: Added `/mcp-server-config` endpoint that accepts list of server configurations
- **Efficient Batching**: Frontend batches multiple server changes and sends them in a single API call (500ms delay)
- **Frontend-Backend Connection**: Toggle changes are batched and sent to API with success/error notifications
- **API URL Fix**: Fixed frontend to call correct API endpoint (http://localhost:8021) instead of relative URL
- **CSP Fix**: Updated Content Security Policy to allow connections to API server
- **Error Handling**: UI reverts all changes if API call fails
- **Multiple Server Support**: API can handle enabling/disabling multiple servers in one request
- All servers disabled by default when UI starts (non-authenticated servers)
- Added proper CSS styling matching existing design patterns
- Comprehensive test coverage including API endpoint tests for single and multiple servers
- All tests passing and linting clean

* ✅ **COMPLETED** - menu item for MCP servers integration and authentication process

**Implementation Details**:
- Added "MCP Servers" menu item to hamburger menu positioned before Settings
- Created MCP Servers modal with list of available servers showing enable/disable status and authentication status
- Added authentication modal with simple "Authenticate with <server>" confirmation dialog
- **Authentication Flow**: Click "Authenticate" → Confirmation popup → Server marked as authenticated and enabled
- **Backend Integration**: Updated API to include `authenticated` boolean field in MCP server configuration
- **UI Synchronization**: Authentication status reflected in both MCP Servers modal and toolbox popup (shows ✓ checkmark)
- **API Updates**: Authentication changes sent to backend with proper logging
- **Visual Indicators**: Authenticated servers show blue checkmark in toolbox, status badges in MCP Servers modal
- **Error Handling**: Proper error notifications and state management
- **Security Enhancement**: Non-authenticated servers are disabled in toolbox with visual feedback and warning notifications
- **Tooltip Guidance**: Added helpful tooltips for disabled servers directing users to authenticate via MCP Servers menu
- All tests passing and linting clean

* ✅ **COMPLETED** - Local Weaviate support for development

Successfully added local Weaviate support for development and testing:

**Implementation Details**:
- **Local Weaviate Implementation**: `WeaviateLocalVectorDatabase` class for local Podman-based Weaviate
- **Podman Compose Setup**: `tools/podman-compose.weaviate.yml` for easy local Weaviate deployment
- **Management Script**: `./tools/weaviate-local.sh` for starting, stopping, and monitoring local Weaviate
- **Available Commands**: start, stop, restart, status, logs
- **Configuration**: Environment Variable `VECTOR_DB_TYPE=weaviate-local`, Local URL `WEAVIATE_LOCAL_URL=http://localhost:8080`
- **No Authentication**: Local instance runs without API keys
- **Automatic Fallback**: Falls back to Milvus if local Weaviate is unavailable
- **Podman-based**: Uses official Weaviate Podman image
- **Health Checks**: Built-in readiness checks and status monitoring
- **Error Handling**: Graceful fallbacks and helpful error messages
- **Documentation**: Updated README with comprehensive setup guide

* ✅ **COMPLETED** - Individual service management commands

Successfully added individual service management capabilities to the process management scripts:

**Implementation Details**:
- **Individual Service Stopping**: `./stop.sh [frontend|api|mcp]` to stop specific services
- **Individual Service Starting**: `./start.sh [frontend|api|mcp]` to start specific services
- **Service-Specific Port Management**: Each service command handles its specific port cleanup
- **PID File Management**: Properly manages PID file entries for individual services
- **Error Handling**: Validates service names and provides helpful error messages
- **Seamless Integration**: Works alongside existing stop/start/restart commands
- **stop.sh Enhancements**: Added `stop_service()` function with service-specific logic
- **start.sh Enhancements**: Added `start_service()` function with service-specific startup
- **Port Management**: Each service command handles its specific port cleanup and startup
- **PID File Handling**: Properly manages PID file entries for individual services
- **Error Validation**: Validates service names and provides helpful error messages

* ✅ **COMPLETED** - Enhanced process status display with service identification

Successfully enhanced the process status display to provide better visibility into service management:

**Implementation Details**:
- **Service Identification**: Each PID now shows which service it belongs to (API, MCP, Agent, Frontend)
- **Automatic Stale PID Cleanup**: Automatically removes dead PIDs from the PID file
- **Enhanced Status Display**: Clear identification of running vs stale processes
- **Service Mapping**: Maps PIDs to their corresponding services using process command analysis
- **Real-time Cleanup**: Stale PIDs are cleaned up automatically when running status check
- **Service Identification Function**: `identify_service()` analyzes process commands to determine service type
- **Automatic Cleanup Function**: `cleanup_stale_pids()` removes dead PIDs from PID file
- **Enhanced Status Display**: Shows service names alongside PIDs for better clarity
- **Process Command Analysis**: Uses `ps -p $pid -o command=` to identify services
- **PID File Management**: Automatically maintains clean PID file without manual intervention

* ✅ **COMPLETED** - Debugging and log monitoring script

Successfully created `./tools/tail-logs.sh` for comprehensive debugging and log monitoring:

**Implementation Details**:
- **Real-time log tailing** using macOS `log stream` command
- **Service-specific monitoring**: API, MCP, Agent, Frontend, Legacy UI
- **System log monitoring**: Recent logs containing RAGme-related keywords
- **Service status checking**: Quick overview of running services
- **Color-coded output**: Easy-to-read service identification
- **Available Commands**: all, api, mcp, agent, frontend, legacy-ui, status, recent
- **macOS compatibility**: Uses `log stream` and `log show` commands
- **Process monitoring**: Tracks specific PIDs for each service
- **Error handling**: Graceful fallbacks and cleanup
- **Documentation**: Updated README with comprehensive usage guide

* ✅ **COMPLETED** - Add TypeScript linting

* ✅ **COMPLETED** - add subcommands to test.sh

Successfully improved `test.sh` with comprehensive subcommands for different test categories:

**Implementation Details**:
- **Subcommand Support**: Added `unit`, `api`, `mcp`, `integration`, `all`, and `help` commands
- **Colored Output**: Beautiful colored status messages with emojis for better UX
- **Comprehensive Help**: Detailed help system with examples and test category descriptions
- **Error Handling**: Proper error messages and help display for invalid commands
- **Test Categorization**: Organized tests into logical categories (unit, API, MCP, integration)
- **Default Behavior**: Runs unit tests by default when no command is specified
- **Bash Script Structure**: Clean, modular functions for each test type
- **Environment Setup**: Proper test environment variables for each category
- **Pytest Integration**: Uses pytest with appropriate filters and file selections
- **Integration Test Support**: Calls existing `tools/test-integration.sh` script
- **Error Handling**: Comprehensive error handling with helpful messages

* ✅ **COMPLETED** - `test.sh integration` still polluting the RagMeDocs collection with test_integration.pdf -- not cleaning up

**Root Cause**: The cleanup function in `tools/test-integration.sh` was only removing test files from the `watch_directory` but not cleaning up documents that were already added to the vector database collection.

**Solution Implemented**:
1. **Enhanced Cleanup Function**: Added `cleanup_test_documents()` function that uses the API to identify and delete test documents
2. **API Integration**: Uses the `/list-documents` endpoint to retrieve all documents and `/delete-document/{id}` to remove test documents
3. **Pattern Matching**: Identifies test documents by looking for patterns like "test_integration", "test.pdf", and "test.*integration" in document metadata
4. **Comprehensive Cleanup**: Now cleans up both file system (watch_directory) and vector database (RagMeDocs collection)
5. **Success Tracking**: Provides detailed feedback on cleanup operations with counts of deleted documents

**Key Improvements**:
- **Complete Cleanup**: Removes test documents from both file system and vector database
- **API-Based Deletion**: Uses proper API endpoints to delete documents from the collection
- **Pattern Recognition**: Intelligently identifies test documents based on filename patterns
- **Detailed Logging**: Shows exactly which documents are being deleted and provides success/failure feedback
- **Robust Error Handling**: Gracefully handles API failures and provides informative messages

**Testing**: Verified that integration tests now properly clean up all test documents, preventing pollution of the RagMeDocs collection.

* ✅ **COMPLETED** - refactor `src/ragme` code to organize code into modular structure

**Implementation Details**:
- **Modular Structure**: Created organized subdirectories with proper `__init__.py` files
- **Import Updates**: Updated all import statements throughout the codebase to use new module paths
- **Backward Compatibility**: Maintained backward compatibility through proper module exports
- **Test Updates**: Updated all test files to use new import paths and patch statements
- **Documentation Updates**: Updated documentation to reflect new module structure
- **Code Quality**: All tests passing and linting clean after refactor
- **Module Organization**:
  - `src/ragme/vdbs` for all vector database code
  - `src/ragme/agents` for all agents code
  - `src/ragme/apis` for all MCPs and APIs
  - `src/ragme/utils` for all utility code

* ✅ **COMPLETED** - only open the Manage Chats sub-menus when user clicks since otherwise hard to select the other menu items

**Implementation Details**:
- **Click-based Navigation**: Changed from hover-based to click-based submenu activation
- **Event Handling**: Replaced `mouseenter`/`mouseleave` events with `click` event
- **Toggle Functionality**: Uses existing `toggleSubmenu()` method for consistent behavior
- **Event Propagation**: Added `stopPropagation()` to prevent menu closure when clicking trigger
- **User Experience**: Submenu now only opens when user explicitly clicks "Manage Chats"
- **Accessibility**: Improved navigation for users who have difficulty with hover interactions

* ✅ **COMPLETED** - selecting a new Documents Overview drop down list the visualization does not refresh

**Implementation Details**:
- **Initialization Fix**: Added `isVisualizationVisible` property initialization in constructor (default: true)
- **Event Listener Fix**: Modified visualization type selector to always call `updateVisualization()` regardless of visibility state
- **State Persistence**: Added localStorage support for visualization visibility state (`ragme-visualization-visible`)
- **Settings Loading**: Enhanced `loadSettings()` to restore visualization visibility preference
- **Initialization**: Added visualization update call in `init()` method to ensure proper initialization
- **User Experience**: Visualization now refreshes immediately when dropdown selection changes
- **Data Preparation**: Visualization data is always prepared and ready when user makes it visible

* ✅ **COMPLETED** - nicer formating of chat answer header

**Implementation Details**:
- **Markdown**: added markdown to answer header including URL

* ✅ **COMPLETED** - add easy way to restart-backend from start.sh script

**Implementation Details**:
- **New Command**: Added `restart-backend` option to `start.sh` script
- **Backend Services**: Restarts API (port 8021), MCP (port 8022), and Local Agent
- **Frontend Preservation**: Keeps frontend running while restarting backend services
- **PID Management**: Properly manages process IDs to avoid conflicts
- **Port Cleanup**: Kills existing processes on backend ports before restarting
- **User Experience**: Provides clear feedback and service URLs after restart
- **Documentation**: Updated help text and usage examples
