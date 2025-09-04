# 📖 RAGme User Guide

This comprehensive user guide covers everything you need to know to get started with RAGme, from installation to advanced usage patterns.

## 🚀 Quick Start

### Requirements

Install and/or update the following if needed:

1. Install [Python 3.12](https://www.python.org/downloads/) or later
2. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) 
3. Install [`gh`](https://cli.github.com/) from GitHub
4. Install [Node.js 18+](https://nodejs.org/) (for new frontend)
5. Vector Database setup (**Weaviate recommended**, or Milvus Lite)

### 🛠️ Quick Setup (Recommended)

For the fastest setup experience, use our automated setup script:

```bash
# Clone the repository
gh repo clone maximilien/ragme-io
cd ragme-io

# Run the automated setup script
./setup.sh
```

The setup script will:
- ✅ Install system dependencies (Homebrew, Node.js, Python)
- ✅ Install Python dependencies using uv
- ✅ Install Node.js dependencies for the frontend
- ✅ Create .env file from template
- ✅ Run initial tests to verify setup
- ✅ Provide next steps and useful commands

**Options:**
```bash
./setup.sh --help              # Show all options
./setup.sh --skip-python       # Skip Python setup
./setup.sh --skip-node         # Skip Node.js setup
./setup.sh --force             # Force reinstall everything
```

### Manual Setup (Alternative)

```bash
gh repo clone maximilien/ragme-io
cd ragme-io

# Setup virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync --extra dev
```

## 🎛️ Configuration

### Environment Setup

Create a `.env` file with your API keys:

```bash
# Copy the example configuration
cp env.example .env

# Edit .env with your values:
OPENAI_API_KEY=sk-proj-*****-**
VECTOR_DB_TYPE=weaviate-local  # Recommended for local development
# VECTOR_DB_TYPE=weaviate  # For cloud Weaviate
# VECTOR_DB_TYPE=milvus  # For Milvus Lite

# For Local Weaviate (only if VECTOR_DB_TYPE=weaviate-local):
WEAVIATE_LOCAL_URL=http://localhost:8080

# For Weaviate Cloud (only if VECTOR_DB_TYPE=weaviate):
WEAVIATE_API_KEY=*****
WEAVIATE_URL=*****.weaviate.cloud

RAGME_API_URL=http://localhost:8021
RAGME_MCP_URL=http://localhost:8022

# Optional: Custom ports for services
RAGME_API_PORT=8021
RAGME_MCP_PORT=8022
RAGME_FRONTEND_PORT=8020
```

### Advanced Configuration

RAGme supports comprehensive configuration management through `config.yaml` for easy customization and client deployment:

```bash
# Copy the example configuration to project root
cp config.yaml.example config.yaml

# Edit the configuration file (located in project root)
nano config.yaml
```

> **📁 Developer Note:** The `config.yaml` file is located in the project root and is automatically ignored by git (added to `.gitignore`), allowing each developer to maintain their own local configuration without affecting the repository.

The configuration system allows you to customize:

- **🌐 Network settings** (ports, CORS, hosts)
- **🗄️ Vector database configurations** (multiple databases, connection settings)
- **🤖 LLM settings** (models, temperature, tokens)
- **🔧 MCP server configurations** (authentication, enabled services)
- **🎨 Frontend customization** (UI settings, branding, colors)
- **🚩 Feature flags** (enable/disable functionality)
- **🔒 Security settings** (file upload limits, CSP)
- **📊 Client branding** (logos, colors, welcome messages)

**📚 Complete Configuration Guide:** See **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** for detailed configuration options, examples, and best practices.

### 🔐 OAuth Authentication Setup ⭐ **NEW!**

RAGme supports OAuth authentication with Google, GitHub, and Apple providers for secure user authentication in production deployments.

#### OAuth Provider Setup

1. **Google OAuth Setup**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URI: `http://localhost:3020/auth/google/callback` (or your domain)

2. **GitHub OAuth Setup**:
   - Go to GitHub Settings → Developer settings → OAuth Apps
   - Create a new OAuth App
   - Set Authorization callback URL: `http://localhost:3020/auth/github/callback` (or your domain)

3. **Apple OAuth Setup**:
   - Go to [Apple Developer Console](https://developer.apple.com/)
   - Create a new App ID and Service ID
   - Configure Sign in with Apple
   - Set redirect URI: `http://localhost:3020/auth/apple/callback` (or your domain)

#### Environment Configuration

Add OAuth credentials to your `.env` file:

```bash
# OAuth Authentication
GOOGLE_OAUTH_CLIENT_ID=your-google-oauth-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3020/auth/google/callback

GITHUB_OAUTH_CLIENT_ID=your-github-oauth-client-id
GITHUB_OAUTH_CLIENT_SECRET=your-github-oauth-client-secret
GITHUB_OAUTH_REDIRECT_URI=http://localhost:3020/auth/github/callback

APPLE_OAUTH_CLIENT_ID=your-apple-oauth-client-id
APPLE_OAUTH_CLIENT_SECRET=your-apple-oauth-client-secret
APPLE_OAUTH_REDIRECT_URI=http://localhost:3020/auth/apple/callback

SESSION_SECRET_KEY=your-session-secret-key-change-in-production
```

#### Configuration File

Configure OAuth providers in `config.yaml`:

```yaml
authentication:
  # Bypass login for development/testing (default: false)
  bypass_login: false
  
  # OAuth providers configuration
  oauth:
    providers:
      google:
        enabled: true
        client_id: "${GOOGLE_OAUTH_CLIENT_ID}"
        client_secret: "${GOOGLE_OAUTH_CLIENT_SECRET}"
        redirect_uri: "${GOOGLE_OAUTH_REDIRECT_URI:-http://localhost:3020/auth/google/callback}"
        scope: "openid email profile"
        
      github:
        enabled: true
        client_id: "${GITHUB_OAUTH_CLIENT_ID}"
        client_secret: "${GITHUB_OAUTH_CLIENT_SECRET}"
        redirect_uri: "${GITHUB_OAUTH_REDIRECT_URI:-http://localhost:3020/auth/github/callback}"
        scope: "user:email"
        
      apple:
        enabled: true
        client_id: "${APPLE_OAUTH_CLIENT_ID}"
        client_secret: "${APPLE_OAUTH_CLIENT_SECRET}"
        redirect_uri: "${APPLE_OAUTH_REDIRECT_URI:-http://localhost:3020/auth/apple/callback}"
        scope: "name email"
        
  # Session configuration
  session:
    secret_key: "${SESSION_SECRET_KEY:-your-secret-key-change-in-production}"
    max_age_seconds: 86400  # 24 hours
    secure: false  # Set to true in production with HTTPS
    httponly: true
    samesite: "lax"
```

#### Usage

- **Development**: Set `bypass_login: true` in `config.yaml` to skip authentication
- **Production**: Configure OAuth providers and set `bypass_login: false`
- **User Experience**: Users see a login modal on first visit, then seamless access
- **Logout**: Users can logout via the hamburger menu

## 🏃‍♂️ Running RAGme

### Quick Start (All Services)

Use the provided startup script to launch all services:

```bash
chmod +x start.sh
./start.sh
```

This will start all services and you can access the **new frontend** at `http://localhost:8020`

### Process Management

```bash
# Stop all services
./stop.sh

# Restart all services
./stop.sh restart

# Check service status
./stop.sh status

# Stop specific services
./stop.sh frontend    # Stop frontend only
./stop.sh api         # Stop API only
./stop.sh mcp         # Stop MCP only
./stop.sh minio       # Stop MinIO only
```

### Frontend Development

```bash
# Compile frontend after configuration or code changes
./start.sh compile-frontend

# Restart only the frontend server
./start.sh restart-frontend

# Restart only backend services (API, MCP, Agent)
./start.sh restart-backend
```

**Use Cases:**
- **Configuration Changes**: After modifying `config.yaml`, run `./start.sh compile-frontend` to rebuild the frontend
- **Frontend Development**: Use `compile-frontend` for faster iteration when working on UI changes
- **Selective Restarts**: Restart only the services you need without affecting others

## 🎨 User Interface

### Modern Three-Pane Layout

RAGme features a modern, responsive web interface with three-pane layout:

- **Left Sidebar**: Chat history (collapsible)
- **Center**: Main chat area with input
- **Right Sidebar**: Recent documents with D3.js visualization (resizable)

**Key Features**:
- **Real-time chat** with markdown support and copy functionality
- **🎤 Voice-to-Text Input**: Microphone button for voice input using browser's Web Speech API
- **🔧 MCP Server Tools**: Configure and enable/disable MCP tool servers (Google Drive, Dropbox, Gmail, Twilio, RAGme Test)
- **💡 Recent Prompts & Ideas**: Quick access to sample prompts and recent chat history
- **Quick New Chat**: "+" button in chat history sidebar for instant new chat creation
- **Save and Email**: Save individual responses as markdown files or send via email
- **Smart document management** with automatic chunking and grouped display
- **Date filtering**: Filter documents by Current, This Month, This Year, or All
- **Interactive visualizations** with D3.js charts (bar, pie, network graphs)
- **Click-to-scroll functionality** - click on visualization nodes to scroll to documents
- **Responsive design** with collapsible sidebars and smooth animations
- **Content addition** via URLs, file uploads, or JSON data
- **WebSocket communication** for real-time updates

### Enhanced Settings Interface

RAGme now features a completely redesigned Settings interface with organized tabbed layout and comprehensive configuration options from `config.yaml`:

#### 📋 Enhanced Settings Interface

**⚙️ Tabbed Organization:**
- **General Tab**: Application info, auto-refresh settings, display preferences
- **Interface Tab**: Layout settings, panel visibility, visualization preferences  
- **Documents Tab**: Document processing, search & filtering options
- **Chat Tab**: AI model settings, chat history management

**🔧 General Settings:**
- **Application Information**: View app name, version, and vector database type
- **Auto-Refresh**: Enable/disable automatic content refresh with configurable intervals
- **Max Documents**: Maximum number of documents to display (1-100)
- **Show Vector DB Info**: Display vector database type and collection information in the header

**📱 Interface Settings:**
- **Layout Controls**: Adjustable panel widths with live preview sliders
- **Panel Visibility**: Configure which panels start collapsed/expanded
- **Visualization Options**: Default chart types (graph/chart/table) and date filters
- **Document List Width**: Width of the document list pane (20-60%, default: 35%)
- **Chat History Width**: Width of the chat history pane (5-30%, default: 10%)

**📄 Document Settings:**
- **Document Overview**: Enable/disable document visualization features
- **Display Limits**: Configure max documents and pagination size
- **Content Filtering**: Default content type filters (documents/images/both)

**🤖 Chat Settings:**
- **AI Model Parameters**: Max tokens (1000-16000) and temperature (0-2) with live sliders
- **Chat History Management**: History limits and auto-save preferences

## 📚 Content Management

### Adding Content

RAGme supports multiple ways to add content to your collection:

#### 1. **Web Pages via Chat**
```
User: "Add this URL to my collection: https://example.com"
Agent: Processes the webpage and adds it to your collection
```

#### 2. **File Upload**
- **Frontend**: Drag and drop files or use the file upload interface
- **Supported Formats**: PDF, DOCX, TXT, MD, JSON, CSV
- **Automatic Processing**: Files are automatically chunked and indexed

#### 3. **Watch Directory**
```bash
# Copy files to the watch directory
cp document.pdf watch_directory/

# Files are automatically processed and added to your collection
```

#### 4. **Chrome Extension**
1. Load the extension in Chrome (`chrome://extensions/` → Developer mode → Load unpacked → select `chrome_ext/`)
2. Navigate to any webpage
3. Click the RAGme extension icon
4. Click "Capture Page" to add the current page

#### 5. **JSON Data**
```json
{
  "url": "https://example.com",
  "title": "Example Page",
  "content": "This is the content of the page..."
}
```

### Document Processing

#### Smart Chunking
Large documents are automatically split into manageable chunks while preserving readability:
- **Sentence Boundary Splitting**: Documents split at natural sentence boundaries
- **Configurable Chunk Size**: Adjustable via configuration
- **Overlap Management**: Configurable overlap between chunks for better context

#### Document Management
- **Grouped Display**: Documents with multiple chunks are grouped together
- **Chunk Counts**: Shows the number of chunks per document
- **Bulk Operations**: Delete entire chunked documents with a single click
- **Pattern-Based Deletion**: Delete documents matching regex patterns

### Image Support

RAGme includes comprehensive image support with AI-powered analysis:

#### Image Upload
- Support for JPG, PNG, GIF, WebP, BMP, HEIC, and HEIF formats
- Frontend drag-and-drop image upload interface
- Dedicated `/upload-images` API endpoint

#### AI-Powered Processing
- **PyTorch Classification**: Uses ResNet50 trained on ImageNet to classify image content
- **OCR Text Extraction**: Automatically extracts text from images containing text (websites, documents, slides, etc.)
- **EXIF Metadata Extraction**: Extracts camera settings, GPS data, and other technical metadata
- **Smart Storage**: Images stored as base64 BLOB data in Weaviate with rich metadata including OCR content

#### PDF Image Extraction
RAGme automatically extracts and processes images from PDF documents:

**🔍 Automatic Extraction:**
- **PyMuPDF Integration**: Uses PyMuPDF (fitz) to extract embedded images from PDF pages as 8-bit/color RGB PNG
- **Smart Filtering**: Configurable size and format constraints to filter relevant images
- **Page-Level Tracking**: Each extracted image includes page number and PDF source information
- **Caption Detection**: Attempts to extract captions from OCR content when available
- **Web-Compatible Format**: Extracts images in proper color format (no more "black rectangle" display issues)

**📊 Metadata Structure:**
```json
{
  "source_type": "pdf_extracted_image",
  "pdf_filename": "document.pdf",
  "pdf_page_number": 3,
  "pdf_image_name": "X39.png",
  "pdf_storage_path": "documents/20250826_123456_document.pdf",
  "extraction_timestamp": "2025-08-26T14:21:22",
  "extracted_caption": "Figure 1: System Architecture",
  "classification": {
    "top_prediction": {
      "label": "diagram",
      "confidence": 0.95
    }
  },
  "ocr_content": {
    "text": "System Architecture Diagram",
    "confidence": 0.88
  }
}
```

**📚 Image Stacking Interface:**
When PDFs contain many images, RAGme groups them into a single stack item in the document list for better user experience:

- **Stack Badge**: Purple badge showing total image count (e.g., "4 images")
- **Dropdown Selection**: Easy navigation between individual images with page numbers and classifications
- **Dynamic Updates**: All content updates when selecting different images:
  - Image preview
  - File download details
  - OCR text content
  - AI summary
  - All metadata
- **Bulk Operations**: Delete entire image stacks with one action

## 🔍 Querying Your Content

### Natural Language Queries

Ask questions about your collected content using natural language:

```
User: "What is the main topic of the documents I've added?"
User: "Summarize the key points from the technical documentation"
User: "Find information about API endpoints in my collection"
User: "What are the recent updates mentioned in the documents?"
```

### AI Summary Caching

RAGme includes an intelligent caching system that stores AI-generated summaries in document metadata:

- **Automatic Cache Checking**: System checks for existing summaries before generating new ones
- **Visual Indicators**: "Cached Summary" indicators show when summaries are from cache
- **Force Refresh**: Button next to AI Summary titles allows regeneration on demand
- **Seamless Integration**: Works with both document and image collections

### Advanced Querying

#### Content-Specific Queries
```
User: "Show me images from document.pdf"
User: "Find images from page 5 of the report"
User: "Find diagrams or charts in my PDFs"
User: "Find images containing 'architecture' text"
```

#### Document Management Queries
```
User: "List all documents in my collection"
User: "Delete the document about API documentation"
User: "Reset my collection"
User: "Show me documents from this month"
```

## 🛠️ Tools and Utilities

### Storage Management

```bash
# Storage management and health checks
./tools/storage.sh health       # Check storage service health and show available buckets
./tools/storage.sh buckets      # List all available buckets
./tools/storage.sh info         # Show storage configuration and status
./tools/storage.sh list         # List all files in storage
./tools/storage.sh list --all   # List files from all buckets
./tools/storage.sh list --bucket <name>  # List files from specific bucket
./tools/storage.sh help         # Show all storage management commands
```

### Performance Optimization

```bash
# Performance optimization tools
./tools/optimize.sh query-threshold     # Find optimal text_relevance_threshold
./tools/optimize.sh query-threshold 0.3 0.9  # Custom range
./tools/optimize.sh help                # Show all optimization commands
```

### Vector Database Management

```bash
# Vector database management tools
./tools/vdb.sh virtual-structure       # Show virtual structure (chunks, grouped images, documents)
./tools/vdb.sh document-groups         # Show how documents are grouped into chunks
./tools/vdb.sh image-groups            # Show how images are grouped by PDF source
./tools/vdb.sh delete-document <file>  # Delete document and all its chunks/images
./tools/vdb.sh health                  # Check VDB health and connectivity
./tools/vdb.sh --show                  # Show current VDB configuration
./tools/vdb.sh help                    # Show all VDB management commands
```

### Debugging and Log Monitoring

```bash
# Monitor all service logs
./tools/tail-logs.sh all

# Monitor specific services
./tools/tail-logs.sh api        # API logs (port 8021)
./tools/tail-logs.sh mcp        # MCP logs (port 8022)
./tools/tail-logs.sh frontend   # Frontend logs (port 8020)
./tools/tail-logs.sh minio      # MinIO logs (port 9000)
```

## 🎯 Use Cases and Examples

### 1. **Current Affairs Research**
1. Go to [Google News](https://news.google.com/home?hl=en-US&gl=US&ceid=US:en) and add a few articles you care about
2. Ask RAGme.io to summarize or ask any question about the articles

### 2. **Blog Analysis**
1. Ask `Crawl my <favorite.blog.url> up to 10 posts and add to my collection`
2. Ask RAGme.io questions about the blog posts ingested

### 3. **Code Documentation**
1. Find your favorite OSS GitHub project and ask `Crawl my <favorite.oss.github.url> up to 10 deep and add to my collection`
2. Ask RAGme.io questions about the project, e.g., give a quick user guide

### 4. **Technical Documentation**
1. Upload technical PDFs or documentation
2. Ask specific questions about implementation details
3. Get summaries of complex technical concepts

### 5. **Research Paper Analysis**
1. Upload research papers or academic documents
2. Extract key findings and methodologies
3. Compare findings across multiple papers

### 6. **Business Intelligence**
1. Collect business reports and market analysis
2. Extract trends and insights
3. Generate executive summaries

## 🔧 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check if ports are already in use
lsof -i :8020  # Frontend port
lsof -i :8021  # API port
lsof -i :8022  # MCP port
lsof -i :9000  # MinIO port

# Kill processes using these ports
kill -9 <PID>
```

#### Vector Database Connection Issues
```bash
# Check VDB health
./tools/vdb.sh health

# Restart VDB services
./tools/weaviate-local.sh restart  # For local Weaviate
```

#### Storage Issues
```bash
# Check storage health
./tools/storage.sh health

# Restart MinIO
./stop.sh minio
./start.sh minio
```

### Getting Help

For detailed troubleshooting information, see **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**.

## 🔮 Advanced Features

### Environment Switching

Switch between different application environments (e.g., RAGme ↔ YourFancyRAG) by simply changing the `.env` file and restarting with `./stop.sh && ./start.sh`. All configuration changes (APPLICATION_*, VECTOR_DB_TYPE, collection names) take effect immediately.

### Multiple Collections Support

RAGme supports multiple collections per vector database to enable different content types such as text documents and images. Configure in `config.yaml` under each database as a `collections` array:

```yaml
vector_databases:
  default: "weaviate-cloud"
  databases:
    - name: "weaviate-cloud"
      type: "weaviate"
      url: "${WEAVIATE_URL}"
      api_key: "${WEAVIATE_API_KEY}"
      collections:
        - name: "RagMeDocs"
          type: "text"
        - name: "RagMeImages"
          type: "image"
```

### MCP Server Integration

RAGme includes Model Context Protocol (MCP) server integration for enhanced functionality:

- **Google Drive Integration**: Access and process Google Drive documents
- **Dropbox Integration**: Connect to Dropbox for document access
- **Gmail Integration**: Process emails and attachments
- **Twilio Integration**: SMS and communication features
- **RAGme Test Tools**: Testing and validation utilities

Configure MCP servers in the Settings interface or via `config.yaml`.
