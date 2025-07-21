# RagMe Documentation

Welcome to the RagMe documentation! This directory contains comprehensive documentation for the RagMe project.

## 📚 Documentation Structure

### Core Documentation
- **[Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Guide to the vector database agnostic architecture
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to the project
- **[Presentation](PRESENTATION.md)** - Project overview and technical details
- **[CI/CD Pipeline](CI_CD.md)** - Continuous Integration and testing setup

### Project Structure
```
ragme-ai/
├── docs/                    # 📚 Documentation
│   ├── README.md           # This file
│   ├── VECTOR_DB_ABSTRACTION.md
│   ├── CONTRIBUTING.md
│   ├── PRESENTATION.md
│   └── CI_CD.md            # CI/CD documentation
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
5. **Testing**: See [CI_CD.md](CI_CD.md) for testing and CI information

## 🔧 Architecture Overview

RagMe is built with a modular, vector database agnostic architecture:

- **Vector Database Abstraction**: Support for multiple vector databases (Weaviate, Pinecone, etc.)
- **REST API**: FastAPI-based API for programmatic access
- **File Monitoring**: Automatic processing of PDF and DOCX files
- **Web UI**: Streamlit interface for easy interaction
- **Chrome Extension**: Browser integration for web content
- **CI/CD Pipeline**: Automated testing across multiple Python versions

## 📖 Detailed Guides

### For Developers
- [Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md) - Understanding the database layer
- [Contributing Guidelines](CONTRIBUTING.md) - Development workflow and standards
- [CI/CD Pipeline](CI_CD.md) - Testing and continuous integration

### For Users
- [Presentation](PRESENTATION.md) - Complete project overview with examples
- Main [README.md](../README.md) - Installation and basic usage

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style and standards
- Testing requirements
- Pull request process
- Development setup

## 🧪 Testing

The project includes comprehensive testing:

- **61 tests** covering all major functionality
- **Automated CI/CD** with GitHub Actions
- **Multi-Python version support** (3.10, 3.11, 3.12)
- **Mocked dependencies** for reliable testing

See [CI_CD.md](CI_CD.md) for detailed testing information.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details. 