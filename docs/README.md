# RagMe Documentation

Welcome to the RagMe documentation! This directory contains comprehensive documentation for the RagMe project.

## 📚 Documentation Structure

### Core Documentation
- **[Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Guide to the vector database agnostic architecture
- **[Contributing Guidelines](CONTRIBUTING.md)** - How to contribute to the project
- **[Presentation](PRESENTATION.md)** - Project overview and technical details
- **[CI/CD Pipeline](CI_CD.md)** - Continuous Integration and testing setup
- **[Process Management](PROCESS_MANAGEMENT.md)** - Service lifecycle management and troubleshooting
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions

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
│   ├── vector_db.py        # Vector database compatibility layer
│   ├── vector_db_base.py   # Abstract base class
│   ├── vector_db_weaviate.py # Weaviate implementation
│   ├── vector_db_milvus.py # Milvus implementation
│   ├── vector_db_factory.py # Factory function
│   ├── api.py              # FastAPI REST API
│   ├── mcp.py              # Model Context Protocol
│   ├── ui.py               # Streamlit UI
│   └── common.py           # Common utilities
├── tests/                  # 🧪 Test suite
│   ├── test_vector_db_base.py
│   ├── test_vector_db_weaviate.py
│   ├── test_vector_db_milvus.py
│   ├── test_vector_db_factory.py
│   └── test_vector_db.py   # Compatibility layer
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

- **Vector Database Abstraction**: Support for multiple vector databases (Weaviate, Milvus, etc.)
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
- [Process Management](PROCESS_MANAGEMENT.md) - Service management and troubleshooting

### For Users
- [Presentation](PRESENTATION.md) - Complete project overview with examples
- [Process Management](PROCESS_MANAGEMENT.md) - Service lifecycle management
- Main [README.md](../README.md) - Installation and basic usage

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style and standards
- Testing requirements
- Pull request process
- Development setup

## 🧪 Testing and Code Quality

The project includes comprehensive testing and code quality enforcement:

### Testing

- **72 tests** covering all major functionality
- **Modular test organization** with separate test files for each component
- **Automated CI/CD** with GitHub Actions
- **Multi-Python version support** (3.10, 3.11, 3.12)
- **Mocked dependencies** for reliable testing
- **Vector database abstraction tests** with full coverage

### Code Quality

- **Automated linting** with Ruff for code quality enforcement
- **Consistent formatting** across the entire codebase
- **Type hints** required for all functions and methods
- **Exception handling** standards (B904 compliance)
- **Import organization** and sorting
- **CI enforcement** - all linting checks must pass before merging

### Test Structure

The test suite is organized to match the modular code structure:

```
tests/
├── test_vector_db_base.py      # Tests for abstract base class
├── test_vector_db_weaviate.py  # Tests for Weaviate implementation
├── test_vector_db_milvus.py    # Tests for Milvus implementation
├── test_vector_db_factory.py   # Tests for factory function
└── test_vector_db.py           # Compatibility layer (imports from above)
```

Each test file focuses on its specific component, making it easy to:
- Run tests for specific vector database implementations
- Add new tests when adding new database support
- Maintain clean separation of test concerns
- Debug issues in specific components

See [CI_CD.md](CI_CD.md) for detailed testing information.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details. 