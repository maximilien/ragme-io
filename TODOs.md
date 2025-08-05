# TODOs

## **OPEN**

### chore

### bugs
* query agent should perform user query (not necessarily summarize results from semantic search)
* queries for functional agent are not flowing to function / tool, e.g., "list", "list docs"

* make sure to confirm with user before executing delete docs tools 
* add memory to chat agent
* chat responses and document details card include file link but does not work (need doc backend)

* right pane shows as purple block when collapse on mobile (iPhone)
* the chat text input is hidden on mobile (iPhone). Need to flip to horizontal and touch bottom to be able to make text input visible and usable

### frontend
* "recent / ideas" prompt popup button to give user quick way to start their first prompts. Here are some details on implementation:
- align button to the right of the chat input
- use recent icon 
- when click led on empty (new) chat then include these five sample prompts:
- 1. list my recent document
- 2. summarize my documents added this week
- 3. give me a list of categories for my recent documents 
- 4. what do you know about [document title]
- 5. tell me about [document title]
- when clicked on ongoing chat then include the most recent five prompts from user (in order they were submitted) and these three sample prompts (at bottom)
- 1. give me a list of categories for my recent documents 
- 2. what do you know about [document title]
- 3. tell me about [document title]
- when user selects one of the pop up prompts item then fill the chat input with value. User can then edit and submit
- the size of the popup should be not more than 50% of chat input and height should be not more than 50% of the chat area
- popup should appear to be coming from the recent button so positioned accordingly

* "toolbox" button to pop checkable (selectable) list of enabled MCP tool servers 
* settings for MCP tools servers integration ans authentication process
* settingd to enable / disable saving uoloaded document in soc server
* doc details card should allow viewing of doc snd chunks

### backend
* document server - for docuemts added with “+ Add Content” upload keep copy on doc server. Add settings to enable / disable this
* MCP tool servers integration and authentication
* MCP agent to call and use MCP server tools depending on prompts
* gateway agent and prompt tuning to figure out if user promot should be handled by Query / Function / MCP agent
* graph db - build knowledge graph of documents / content via Neo4J
* graph agent - queries graph db with text -> cypher query to complement query agent results

### tests
* test with local weaviate 
* test with local milvus

### features

#### generalization 
* make RAGme work with configurable collection name
* make other parts of RAGme that could be changed, e.g., name, query agent configurable
* 

#### use cases
* support agent to collect images and docs for period of time and create report, e.g., conference slide photos

#### content types
* images - add images from URLs and upload
* support extracting metadata from images
* support extracting text from images and add to metadata, eg, image of a slide
* extract images from documents and upload to ImagesDocs collection with metadata to link back to document 

* voice memos - `.wav` files and other formats
* podcasts - link to podcast files
* blogs (RSS) subscriptions - any RSS feed
* videos (YouTube) - link to youtube videos

#### insights
* daily summaries - create a summary of a particular day's activity
* daily insights - generate insight from documents added in a particular day
* monthly versions - monthly versions of summaries and insights

#### services (MCP servers)
* mail - gmail suooort to read / write mails
* todos - google task read / write
* cloud drives - google drive / microsoft one drive/ dropbox
* twillio (phone messages) - add documents and links using messages with a phone number
* whatsapp integration (explore if possible)
* slack channels - add documents and links using slack messages
* X / Twitter - add documents and links from X account posts

### nice to have
* a2a support to discover and call other external agents to do work

---

## **COMPLETED**

### bugs
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

### frontend
* ✅ **COMPLETED** - New frontend UI

Successfully created a new modern UI for RAGme.ai Assistant with the following features:

### ✅ Implemented Features:
- **Three-pane layout** with resizable and collapsible sidebars
- **Right pane**: "Recent Documents" showing documents ordered by recency
- **Document details**: Click to view name, ID, metadata, summary, date added, and vector DB collection
- **App name**: 🤖 RAGme.ai Assistant
- **D3.js visualization**: Document type charts and analytics
- **Markdown formatting**: Chat results with copy functionality on hover
- **Modern UI**: Beautiful gradients, animations, and responsive design

### ✅ Technical Implementation:
- **Frontend directory**: `./frontend/` with TypeScript, Express, Socket.IO
- **Process management**: Updated `./start.sh` and `./stop.sh` to manage the new frontend
- **Port configuration**: New frontend on port 3020, legacy UI on port 8020
- **API integration**: WebSocket communication with RAGme.ai backend
- **Documentation**: Updated README and created frontend-specific docs

### ✅ Quality Assurance:
- All tests passing (`./test.sh`)
- All linting checks passing (`./tools/lint.sh`)
- TypeScript compilation successful
- Modern browser compatibility

### 🎯 Key Features:
1. **Real-time chat** with markdown support and copy functionality
2. **Document management** with visual D3.js charts
3. **Content addition** via URLs or JSON data
4. **Responsive design** that works on desktop and mobile
5. **WebSocket communication** for real-time updates
6. **Settings management** with localStorage persistence

The new frontend is now ready for use at `http://localhost:3020` when running `./start.sh`!

* ✅ **COMPLETED** - Show Documents in different panes: recent, this week, this month, this year

Successfully implemented document date filtering in the Documents pane:

### ✅ Implemented Features:
- **Date Filter Dropdown**: Added dropdown selector in Documents sidebar header with options: Current, This Month, This Year, All
- **Backend API Enhancement**: Updated `/list-documents` endpoint to support `date_filter` parameter
- **Date Filtering Logic**: Implemented server-side filtering based on document `date_added` metadata
- **Frontend Integration**: Updated frontend to send date filter parameter and handle filtered results
- **Persistent Preferences**: Date filter choice is saved in localStorage and restored on page reload
- **Visual Feedback**: Refresh button shows active filter in notifications
- **Smart Defaults**: Defaults to "Current" (this week) for better UX

### ✅ Filter Options:
- **Current**: Documents added in the last 7 days (this week)
- **This Month**: Documents added in the current month
- **This Year**: Documents added in the current year
- **All**: All documents (no date filtering)

### ✅ Technical Implementation:
- **Backend**: Added `filter_documents_by_date()` function in `api.py`
- **Frontend**: Updated `app.js` with date filter state management and event handlers
- **UI**: Added dropdown selector with CSS styling in `index.html` and `styles.css`
- **API**: Enhanced `/list-documents` endpoint with `date_filter` query parameter
- **Testing**: All unit and integration tests passing

### 🎯 Key Benefits:
1. **Better UX**: Users can focus on recent documents or explore specific time periods
2. **Performance**: Efficient server-side filtering for large document collections
3. **Persistence**: User preferences are saved and restored automatically
4. **Flexibility**: Multiple time period options to suit different use cases
5. **Integration**: Works seamlessly with existing document management features

The date filtering feature is now ready for use and documented in the README!

* ✅ **COMPLETED** - Order document in document pane by order of their additions to the VDB

* ✅ **COMPLETED** - Add a "new" badge (upper right top) when a new document is added to make it stand out in list

* ✅ **COMPLETED** - Add a + to create New Chat easily as a shortcut to new Chat in hamburger menu

### ✅ Implemented Features:
- **Quick New Chat Button**: Added "+" button between "Chat History" title and collapse button
- **Visual Design**: Dim by default (opacity 0.7), highlights in green on hover like save chat button
- **Tooltip**: "New chat" tooltip on hover for clear user guidance
- **Functionality**: Direct shortcut to createNewChat() function, same as hamburger menu
- **Responsive**: Works seamlessly with existing sidebar layout and mobile design

### ✅ Technical Implementation:
- **HTML**: Added button with FontAwesome plus icon in sidebar header
- **CSS**: Styled with hover effects matching existing save button design
- **JavaScript**: Connected to existing createNewChat() function via event listener
- **Testing**: All unit and integration tests passing
- **Linting**: All code quality checks passing

### 🎯 Key Benefits:
1. **Improved UX**: One-click access to new chat creation without menu navigation
2. **Visual Consistency**: Matches existing button styling and hover effects
3. **Accessibility**: Clear tooltip and intuitive placement
4. **Performance**: No additional overhead, reuses existing functionality

The quick new chat button is now ready for use and documented in the README!

* ✅ **COMPLETED** - Show connection status in Vector DB info banner

Successfully implemented connection status monitoring for the Vector DB info banner:

### ✅ Implemented Features:
- **Connection Status Tracking**: Monitors success/failure of periodic document refresh calls
- **Visual Error Indication**: Vector DB banner highlights in light red when connection fails
- **Pulsing Animation**: Subtle pulsing animation draws attention to connection issues
- **Automatic Recovery**: Banner returns to normal when connection is restored
- **Socket Event Handling**: Tracks both document refresh failures and socket disconnections
- **Real-time Updates**: Connection status updates immediately when issues occur

### ✅ Technical Implementation:
- **Connection Status Object**: Tracks `isConnected`, `lastSuccess`, `failureCount`, `lastFailure`
- **Event Monitoring**: Monitors `documents_listed` success/failure and socket connect/disconnect
- **CSS Styling**: Added `.connection-error` class with red highlighting and pulsing animation
- **Status Persistence**: Connection status maintained across auto-refresh cycles
- **Visual Feedback**: Red background, border, and text color for error state

### ✅ Error Detection:
- **Document Refresh Failures**: When `list_documents` calls fail
- **Socket Disconnections**: When WebSocket connection is lost
- **Auto-refresh Failures**: When periodic 30-second refresh calls fail
- **Manual Refresh Failures**: When user clicks refresh button and it fails

### 🎯 Key Benefits:
1. **Immediate Feedback**: Users see connection issues instantly in the header
2. **Non-intrusive**: Subtle red highlighting doesn't disrupt the interface
3. **Automatic Recovery**: No user action needed when connection is restored
4. **Clear Indication**: Pulsing animation makes connection issues obvious
5. **Comprehensive Monitoring**: Covers all types of connection failures

The connection status feature is now active and will highlight the Vector DB banner in light red whenever there are connection issues with the backend services!

* ✅ **COMPLETED** - Reorganize hamburger menu: Move chat management items into "Manage Chats" submenu

Successfully reorganized the hamburger menu to improve organization and prepare for future menu items:

### ✅ Implemented Features:
- **Manage Chats Submenu**: Created a collapsible submenu containing all chat management items
- **Submenu Items**: New Chat, Clear Current Chat, Clear All History, Clear Everything
- **Visual Design**: Added chevron arrow that rotates when submenu is expanded
- **Settings Separation**: Kept Settings as a top-level menu item for easy access
- **Hover Functionality**: Submenu appears on hover with smooth transitions
- **Smart Timing**: 100ms delay prevents accidental submenu closure when moving mouse
- **Smooth Animations**: Added CSS transitions for submenu expand/collapse
- **Click Handling**: Proper event handling to prevent menu closure when clicking submenu items

### ✅ Technical Implementation:
- **HTML Structure**: Updated menu dropdown with submenu trigger and submenu container
- **CSS Styling**: Added styles for submenu trigger, submenu items, and arrow animations
- **JavaScript Logic**: Added hover event handlers with timeout management for smooth UX
- **Event Management**: Smart hover detection with delay to prevent accidental closure
- **Responsive Design**: Submenu works seamlessly on desktop and mobile

### ✅ Menu Structure:
```
🤖 RAGme.ai Assistant
├── Manage Chats ▼
│   ├── New Chat
│   ├── Clear Current Chat
│   ├── Clear All History
│   └── Clear Everything
└── Settings
```

### 🎯 Key Benefits:
1. **Better Organization**: Chat management items are logically grouped
2. **Future-Ready**: Menu structure supports adding new top-level items
3. **Improved UX**: Cleaner, more organized menu interface
4. **Accessibility**: Clear visual hierarchy and intuitive navigation
5. **Mobile Friendly**: Works well on touch devices

The hamburger menu reorganization is now complete and ready for use!

### backend
* ✅ **COMPLETED** - Local Weaviate support for development

Successfully added local Weaviate support for development and testing:

### ✅ Implemented Features:
- **Local Weaviate Implementation**: `WeaviateLocalVectorDatabase` class for local Podman-based Weaviate
- **Podman Compose Setup**: `tools/podman-compose.weaviate.yml` for easy local Weaviate deployment
- **Management Script**: `./tools/weaviate-local.sh` for starting, stopping, and monitoring local Weaviate
- **Factory Integration**: Updated `vector_db_factory.py` to support `weaviate-local` type
- **Example Script**: `examples/weaviate_local_example.py` demonstrating local Weaviate usage

### ✅ Available Commands:
- `./tools/weaviate-local.sh start` - Start local Weaviate container
- `./tools/weaviate-local.sh stop` - Stop local Weaviate container
- `./tools/weaviate-local.sh restart` - Restart local Weaviate container
- `./tools/weaviate-local.sh status` - Check Weaviate status
- `./tools/weaviate-local.sh logs` - View Weaviate logs

### ✅ Configuration:
- **Environment Variable**: `VECTOR_DB_TYPE=weaviate-local`
- **Local URL**: `WEAVIATE_LOCAL_URL=http://localhost:8080`
- **No Authentication**: Local instance runs without API keys
- **Automatic Fallback**: Falls back to Milvus if local Weaviate is unavailable

### ✅ Technical Implementation:
- **Podman-based**: Uses official Weaviate Podman image
- **Health Checks**: Built-in readiness checks and status monitoring
- **Error Handling**: Graceful fallbacks and helpful error messages
- **Documentation**: Updated README with comprehensive setup guide

### 🎯 Key Benefits:
1. **No Cloud Dependencies**: Run Weaviate locally without cloud credentials
2. **Full Weaviate Features**: Access to all Weaviate capabilities locally
3. **Easy Setup**: Simple Podman-based deployment
4. **Development Friendly**: Perfect for testing and development
5. **Reliable**: No dependency on external cloud services

The local Weaviate setup is now ready for use and documented in the README!

* ✅ **COMPLETED** - Individual service management commands

Successfully added individual service management capabilities to the process management scripts:

### ✅ Implemented Features:
- **Individual Service Stopping**: `./stop.sh [frontend|api|mcp]` to stop specific services
- **Individual Service Starting**: `./start.sh [frontend|api|mcp]` to start specific services
- **Service-Specific Port Management**: Each service command handles its specific port cleanup
- **PID File Management**: Properly manages PID file entries for individual services
- **Error Handling**: Validates service names and provides helpful error messages
- **Seamless Integration**: Works alongside existing stop/start/restart commands

### ✅ Available Commands:
**Stop Individual Services:**
- `./stop.sh frontend` - Stop only the frontend service (port 3020)
- `./stop.sh api` - Stop only the API service (port 8021)
- `./stop.sh mcp` - Stop only the MCP service (port 8022)

**Start Individual Services:**
- `./start.sh frontend` - Start only the frontend service
- `./start.sh api` - Start only the API service
- `./start.sh mcp` - Start only the MCP service

### ✅ Technical Implementation:
- **stop.sh Enhancements**: Added `stop_service()` function with service-specific logic
- **start.sh Enhancements**: Added `start_service()` function with service-specific startup
- **Port Management**: Each service command handles its specific port cleanup and startup
- **PID File Handling**: Properly manages PID file entries for individual services
- **Error Validation**: Validates service names and provides helpful error messages

### 🎯 Key Benefits:
1. **Granular Control**: Stop/start individual services without affecting others
2. **Testing Flexibility**: Easily test connection status features by stopping specific services
3. **Debugging Support**: Isolate issues by managing services independently
4. **Development Workflow**: Restart only the service you're working on
5. **Service Isolation**: Test service dependencies and failure scenarios

The individual service management commands are now available for better service control and testing!

* ✅ **COMPLETED** - Enhanced process status display with service identification

Successfully enhanced the process status display to provide better visibility into service management:

### ✅ Implemented Features:
- **Service Identification**: Each PID now shows which service it belongs to (API, MCP, Agent, Frontend)
- **Automatic Stale PID Cleanup**: Automatically removes dead PIDs from the PID file
- **Enhanced Status Display**: Clear identification of running vs stale processes
- **Service Mapping**: Maps PIDs to their corresponding services using process command analysis
- **Real-time Cleanup**: Stale PIDs are cleaned up automatically when running status check

### ✅ Technical Implementation:
- **Service Identification Function**: `identify_service()` analyzes process commands to determine service type
- **Automatic Cleanup Function**: `cleanup_stale_pids()` removes dead PIDs from PID file
- **Enhanced Status Display**: Shows service names alongside PIDs for better clarity
- **Process Command Analysis**: Uses `ps -p $pid -o command=` to identify services
- **PID File Management**: Automatically maintains clean PID file without manual intervention

### ✅ Service Detection:
- **API**: Detects `src.ragme.api` processes
- **MCP**: Detects `src.ragme.mcp` processes  
- **Agent**: Detects `src.ragme.local_agent` processes
- **Frontend**: Detects `npm start` processes
- **Unknown**: Handles unrecognized processes gracefully

### 🎯 Key Benefits:
1. **Clear Service Visibility**: Immediately see which service each PID belongs to
2. **Automatic Cleanup**: No more manual stale PID removal
3. **Better Debugging**: Quickly identify which service has issues
4. **Clean PID Files**: PID file stays clean and accurate automatically
5. **Service Isolation**: Easy to see which services are running vs dead

The enhanced status display now provides clear service identification and automatic stale PID cleanup!

### tests
* [No completed test items]

### features
* [No completed feature items]

### nice to have
* ✅ **COMPLETED** - Debugging and log monitoring script

Successfully created `./tools/tail-logs.sh` for comprehensive debugging and log monitoring:

### ✅ Implemented Features:
- **Real-time log tailing** using macOS `log stream` command
- **Service-specific monitoring**: API, MCP, Agent, Frontend, Legacy UI
- **System log monitoring**: Recent logs containing RAGme-related keywords
- **Service status checking**: Quick overview of running services
- **Color-coded output**: Easy-to-read service identification

### ✅ Available Commands:
- `./tools/tail-logs.sh all` - Monitor all running services
- `./tools/tail-logs.sh api` - Monitor API logs (port 8021)
- `./tools/tail-logs.sh mcp` - Monitor MCP logs (port 8022)
- `./tools/tail-logs.sh agent` - Monitor Agent logs
- `./tools/tail-logs.sh frontend` - Monitor Frontend logs (port 3020)
- `./tools/tail-logs.sh legacy-ui` - Monitor Legacy UI logs (port 8020)
- `./tools/tail-logs.sh status` - Check service status
- `./tools/tail-logs.sh recent` - View recent system logs

### ✅ Technical Implementation:
- **macOS compatibility**: Uses `log stream` and `log show` commands
- **Process monitoring**: Tracks specific PIDs for each service
- **Error handling**: Graceful fallbacks and cleanup
- **Documentation**: Updated README with comprehensive usage guide

### 🎯 Key Benefits:
1. **Vector database debugging**: Monitor connection issues and errors
2. **Service troubleshooting**: Real-time visibility into all RAGme processes
3. **Performance monitoring**: Track service activity and responsiveness
4. **Error tracking**: Catch and debug issues as they happen

The debugging script is now ready for use and documented in the README!

* ✅ **COMPLETED** - Add TypeScript linting

* ✅ **COMPLETED** - add subcommands to test.sh

Successfully improved `test.sh` with comprehensive subcommands for different test categories:

### ✅ Implemented Features:
- **Subcommand Support**: Added `unit`, `api`, `mcp`, `integration`, `all`, and `help` commands
- **Colored Output**: Beautiful colored status messages with emojis for better UX
- **Comprehensive Help**: Detailed help system with examples and test category descriptions
- **Error Handling**: Proper error messages and help display for invalid commands
- **Test Categorization**: Organized tests into logical categories (unit, API, MCP, integration)
- **Default Behavior**: Runs unit tests by default when no command is specified

### ✅ Available Commands:
- `./test.sh unit` - Run only unit tests (Python pytest)
- `./test.sh api` - Run only API tests (FastAPI endpoints)
- `./test.sh mcp` - Run only MCP server tests (Model Context Protocol)
- `./test.sh integration` - Run only integration tests (end-to-end system tests)
- `./test.sh all` - Run all tests (unit + api + mcp + integration)
- `./test.sh help` - Show detailed help message
- `./test.sh` - Run unit tests (default behavior)

### ✅ Test Categories:
- **Unit Tests**: Core functionality, vector databases, agents, utilities
- **API Tests**: FastAPI endpoints, response validation, request handling
- **MCP Tests**: Model Context Protocol server, endpoint validation, protocol compliance
- **Integration Tests**: End-to-end system testing, service communication, file monitoring

### ✅ Technical Implementation:
- **Bash Script Structure**: Clean, modular functions for each test type
- **Environment Setup**: Proper test environment variables for each category
- **Pytest Integration**: Uses pytest with appropriate filters and file selections
- **Integration Test Support**: Calls existing `test-integration.sh` script
- **Error Handling**: Comprehensive error handling with helpful messages

### 🎯 Key Benefits:
1. **Selective Testing**: Run only the tests you need for faster development
2. **Better Organization**: Clear separation of test types and purposes
3. **Improved UX**: Colored output and helpful error messages
4. **Development Efficiency**: Quick feedback on specific components
5. **CI/CD Ready**: Easy to integrate into automated testing pipelines

The improved test.sh script is now ready for use with comprehensive subcommand support!

* ✅ **COMPLETED** - `test.sh integration` still poluting the RagMeDocs collection with test_integration.pdf -- not cleaning up

**Root Cause**: The cleanup function in `test-integration.sh` was only removing test files from the `watch_directory` but not cleaning up documents that were already added to the vector database collection.

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

* ✅ **COMPLETED** - refactor `src/ragme` code to organize code into:
    - `src/ragme/vdbs` for all vector database code
    - `src/ragme/agents` for all agents code
    - `src/ragme/apis` for all MCPs and APIs
    - `src/ragme/utils` for all utility code

**Implementation Details**:
- **Modular Structure**: Created organized subdirectories with proper `__init__.py` files
- **Import Updates**: Updated all import statements throughout the codebase to use new module paths
- **Backward Compatibility**: Maintained backward compatibility through proper module exports
- **Test Updates**: Updated all test files to use new import paths and patch statements
- **Documentation Updates**: Updated documentation to reflect new module structure
- **Code Quality**: All tests passing and linting clean after refactor

### integrations
* [No completed integration items]