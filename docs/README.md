# RagMe Documentation

Welcome to the RagMe documentation! This directory contains comprehensive documentation for the RagMe project.

## 📚 Documentation Structure

### Core Documentation
- **[Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Guide to the vector database agnostic architecture
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to the project
- **[Presentation](PRESENTATION.md)** - Project overview and technical details

### Project Structure
```
ragme-ai/
├── docs/                    # 📚 Documentation
│   ├── README.md           # This file
│   ├── VECTOR_DB_ABSTRACTION.md
│   ├── CONTRIBUTING.md
│   └── PRESENTATION.md
├── src/ragme/              # 🐍 Source code
│   ├── __init__.py
│   ├── ragme.py            # Main RagMe class
│   ├── ragme_agent.py      # RagMeAgent class
│   ├── local_agent.py      # File monitoring agent
│   ├── vector_db.py        # Vector database abstraction
│   ├── api.py              # FastAPI REST API
│   ├── mcp.py              # Model Context Protocol
│   ├── ui.py               # Streamlit UI
│   └── common.py           # Common utilities
├── tests/                  # 🧪 Test suite
├── examples/               # 📖 Usage examples
├── chrome_ext/             # 🌐 Chrome extension
└── watch_directory/        # 📁 Monitored directory
```

## 🚀 Quick Start

1. **Installation**: See the main [README.md](../README.md) in the project root
2. **Vector Database Setup**: Read [VECTOR_DB_ABSTRACTION.md](VECTOR_DB_ABSTRACTION.md)
3. **API Usage**: Check the [Presentation](PRESENTATION.md) for API examples
4. **Contributing**: Review [CONTRIBUTING.md](CONTRIBUTING.md)

## 🔧 Architecture Overview

RagMe is built with a modular, vector database agnostic architecture:

- **Vector Database Abstraction**: Support for multiple vector databases (Weaviate, Pinecone, etc.)
- **REST API**: FastAPI-based API for programmatic access
- **File Monitoring**: Automatic processing of PDF and DOCX files
- **Web UI**: Streamlit interface for easy interaction
- **Chrome Extension**: Browser integration for web content

## 📖 Detailed Guides

### For Developers
- [Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md) - Understanding the database layer
- [Contributing Guidelines](CONTRIBUTING.md) - Development workflow and standards

### For Users
- [Presentation](PRESENTATION.md) - Complete project overview with examples
- Main [README.md](../README.md) - Installation and basic usage

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style and standards
- Testing requirements
- Pull request process
- Development setup

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details. 