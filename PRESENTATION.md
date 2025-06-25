# RAGme.ai: Personal RAG Agent for Web Content
## A Comprehensive Overview

---

## 🎯 What is RAGme.ai?

**RAGme.ai** is a personalized agent that uses [Retrieval-Augmented Generation (RAG)](https://en.wikipedia.org/wiki/Retrieval-augmented_generation) to process websites and documents you care about, enabling intelligent querying through an LLM agent.

### Core Concept
- **RAG**: Combines document retrieval with AI generation
- **Personal**: Focuses on your specific content and interests
- **Agentic**: Uses LLM agents for intelligent interaction
- **Multi-modal**: Supports web pages, PDFs, and DOCX documents

---

## 🚀 Key Features & Use Cases

### 1. **Interactive Personal RAG**
- Add websites and documents (PDFs and DOCX)
- Query using natural language
- Get intelligent responses based on your content

### 2. **Content Collection & Processing**
- **Web Crawling**: Automatically discover and process web pages
- **Document Processing**: PDF and DOCX file ingestion
- **Watch Directory**: Automatic processing of new files
- **Chrome Extension**: One-click web page capture

### 3. **Intelligent Querying**
- Ask questions about your collected content
- Get summaries and insights
- Cross-reference information across sources

---

## 🏗️ Architecture Overview

### Multi-Service Architecture

```mermaid
flowchart TB
    ui[Streamlit UI<br/>Port 8020] --> api[API Server<br/>Port 8021]
    chrome[Chrome Extension] --> api
    agent[File Monitor Agent] --> mcp[MCP Server<br/>Port 8022]
    mcp --> api
    api --> ragme[RAGme Core]
    ragme --> weaviate[(Weaviate DB)]
    ragme --> openai[OpenAI LLM]
```

### Core Components

| Component | Port | Purpose |
|-----------|------|---------|
| **Streamlit UI** | 8020 | Web interface for user interaction |
| **API Server** | 8021 | REST API for content ingestion |
| **MCP Server** | 8022 | Document processing (PDF/DOCX) |
| **File Monitor** | - | Watches directory for new files |
| **Chrome Extension** | - | Browser-based content capture |

---

## 🔧 Technology Stack

### Backend Technologies
- **Python 3.12+**: Core application language
- **FastAPI**: High-performance API framework
- **Streamlit**: Rapid web app development
- **Uvicorn**: ASGI server for FastAPI

### AI & ML Stack
- **OpenAI GPT-4o-mini**: Primary LLM for reasoning
- **LlamaIndex**: Document processing and RAG framework
- **Weaviate**: Vector database for embeddings

### Document Processing
- **PyPDF2**: PDF text extraction
- **python-docx**: DOCX document processing
- **BeautifulSoup**: HTML parsing for web content

---

## 📦 Installation & Setup

### Prerequisites
```bash
# Required software
- Python 3.12+
- uv (Python package manager)
- gh (GitHub CLI)
- Weaviate Cloud account
```

### Environment Configuration
```bash
# .env file setup
OPENAI_API_KEY=sk-proj-*****-**
WEAVIATE_API_KEY=*****
WEAVIATE_URL=*****.weaviate.cloud
RAGME_API_URL=http://localhost:8021
RAGME_MCP_URL=http://localhost:8022
```

### Quick Start
```bash
# Clone and setup
gh repo clone maximilien/ragme-ai
cd ragme-ai
uv venv
source .venv/bin/activate
uv sync

# Start all services
chmod +x start.sh
./start.sh
```

---

## 🎮 Usage Examples

### 1. **Web Content Processing**
```bash
# Add web pages to collection
"Crawl my https://example-blog.com up to 10 posts and add to my collection"

# Query the content
"What are the main topics discussed in the blog posts?"
```

### 2. **Document Analysis**
```bash
# Add PDF/DOCX to watch_directory/
# Automatically processed and indexed

# Query documents
"Summarize the key findings from the research papers"
```

### 3. **Current Affairs**
```bash
# Add news articles
"Add these Google News articles about AI developments"

# Get insights
"What are the latest trends in AI technology?"
```

---

## 🔌 API Endpoints

### Content Ingestion
```bash
# Add URLs
POST /add-urls
{
  "urls": ["https://example.com", "https://example.org"]
}

# Add JSON content
POST /add-json
{
  "data": {"content": "..."},
  "metadata": {"source": "..."}
}
```

### Querying
```bash
# Query the collection
POST /query
{
  "query": "What are the main topics?"
}

# List documents
GET /list-documents?limit=10&offset=0
```

---

## 🛠️ Development Features

### Chrome Extension
```javascript
// popup.js - Page capture functionality
async function captureCurrentPage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const response = await fetch(`${RAGME_API_URL}/add-urls`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urls: [tab.url] })
  });
}
```

### File Monitoring
```python
# agent.py - Automatic file processing
class FileHandler(FileSystemEventHandler):
    def __init__(self, callback=None):
        self.supported_extensions = {'.pdf', '.docx'}
    
    def on_created(self, event):
        if file_path.suffix.lower() in self.supported_extensions:
            self.callback(file_path)
```

---

## 📊 Data Flow

### 1. **Content Ingestion**
```mermaid
flowchart LR
    A[Web Page/PDF/DOCX] --> B[Parser]
    B --> C[Text Extraction]
    C --> D[Chunking]
    D --> E[Embedding]
    E --> F[Weaviate DB]
```

### 2. **Query Processing**
```mermaid
flowchart LR
    A[User Query] --> B[Query Embedding]
    B --> C[Vector Search]
    C --> D[Retrieve Documents]
    D --> E[LLM Context]
    E --> F[Generate Response]
```

---

## 🔒 Security & Limitations

### Current Limitations
- ✅ Single collection for all users
- ✅ Tied to Weaviate as vector database
- ✅ Tied to LlamaIndex for RAG operations
- ✅ No HTTPS by default

### Security Considerations
- API keys stored in environment variables
- CORS enabled for development
- No user authentication (single-user system)

---

## 🚀 Future Roadmap

### Phase 1: Infrastructure
- [ ] Decouple Weaviate dependency (OpenSearch support)
- [ ] Decouple LlamaIndex (docling integration)
- [ ] Add HTTPS security

### Phase 2: Content Types
- [ ] Image and video processing
- [ ] Audio content support
- [ ] Email integration (xyz@ragme.io)

### Phase 3: Collaboration
- [ ] Multi-user support (SaaS)
- [ ] Slack integration
- [ ] X/Twitter content ingestion

---

## 💡 Use Case Scenarios

### Scenario 1: Research Assistant
```
User: "I'm researching quantum computing. Add these papers to my collection."
RAGme: "I've added 5 research papers. What specific aspects would you like to explore?"
User: "What are the main challenges in quantum error correction?"
RAGme: "Based on your papers, the main challenges are..."
```

### Scenario 2: News Aggregator
```
User: "Add today's tech news articles about AI"
RAGme: "I've crawled and added 15 articles from tech news sites."
User: "What are the emerging AI trends this week?"
RAGme: "Based on the articles, the key trends are..."
```

### Scenario 3: Document Manager
```
User: *drops PDF into watch_directory*
RAGme: "New document detected and processed: quarterly_report.pdf"
User: "Summarize the financial highlights"
RAGme: "The quarterly report shows..."
```

---

## 🎯 Key Benefits

### For Individuals
- **Personalized Knowledge Base**: Your own curated content collection
- **Intelligent Search**: Natural language queries across all your content
- **Automated Processing**: Seamless ingestion of various content types
- **Insight Generation**: AI-powered analysis and summaries

### For Organizations
- **Document Intelligence**: Extract insights from internal documents
- **Research Efficiency**: Rapid analysis of large document collections
- **Knowledge Discovery**: Find connections across different content sources
- **Scalable Architecture**: Multi-service design for enterprise deployment

---

## 🔧 Technical Highlights

### Performance Optimizations
- **Batch Processing**: Efficient document ingestion
- **Vector Indexing**: Fast similarity search
- **Async Operations**: Non-blocking API responses
- **Memory Management**: Proper cleanup and resource handling

### Extensibility
- **Modular Design**: Easy to add new content types
- **Plugin Architecture**: MCP server for document processing
- **API-First**: RESTful interfaces for integration
- **Open Source**: MIT licensed for customization

---

## 📈 Getting Started Guide

### Step 1: Setup Environment
```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Step 2: Start Services
```bash
# Quick start
./start.sh

# Or manually
uv run uvicorn src.ragme.api:app --port 8021 &
uv run uvicorn src.ragme.mcp:app --port 8022 &
uv run python -m src.ragme.agent &
uv run streamlit run src/ragme/ui.py --port 8020
```

### Step 3: Add Content
```bash
# Via UI: http://localhost:8020
# Via Chrome Extension
# Via watch_directory/ folder
# Via API calls
```

### Step 4: Query & Explore
```bash
# Ask questions about your content
# Generate summaries
# Discover insights
# Cross-reference information
```

---

## 🤝 Contributing

### How to Help
- **Bug Reports**: Open issues for problems
- **Feature Requests**: Suggest new capabilities
- **Code Contributions**: Submit pull requests
- **Documentation**: Improve guides and examples

### Development Setup
```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Code formatting
uv run black src/
uv run isort src/
```

---

## 📞 Support & Resources

### Documentation
- **README.md**: Comprehensive setup guide
- **API Documentation**: Available at `/docs` when API server is running
- **Code Comments**: Well-documented source code

### Community
- **GitHub**: https://github.com/maximilien/ragme-ai
- **Issues**: Bug reports and feature requests
- **Discussions**: Community support and ideas

### Creator
**Created with ❤️ by @maximilien**

---

## 🎉 Conclusion

RAGme.ai represents a powerful approach to personal knowledge management:

- **🔍 Intelligent Content Discovery**: Automatically process and index your content
- **🤖 AI-Powered Insights**: Get intelligent responses from your personal knowledge base
- **🔄 Seamless Integration**: Multiple ways to add and interact with content
- **📈 Scalable Architecture**: Built for growth and customization

**Ready to build your personal AI knowledge assistant?**

---

*Thank you for your attention! Questions and feedback welcome.* 