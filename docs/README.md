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

### 🆕 Latest Features Documentation
- **🔐 MCP Servers Integration & Authentication**: Complete MCP server management with authentication flow and security controls
- **💡 Recent Prompts & Ideas**: Quick access to sample prompts and recent chat history with a convenient bottom sheet interface
- **🧪 Enhanced Testing Framework**: Comprehensive test suite with subcommands for unit, API, MCP, and integration tests
- **🧹 Smart Test Cleanup**: Integration tests now properly clean up test documents from vector database
- **Save and Email**: Save individual chat responses as markdown files or send via email
- **Smart Document Chunking**: Automatic splitting of large documents at sentence boundaries
- **Enhanced UI**: Interactive visualizations with click-to-scroll functionality
- **Improved Document Management**: Grouped chunked documents with bulk operations
- **Real-time Synchronization**: Better refresh and update mechanisms
- **Responsive Design**: Enhanced mobile and desktop experience

## 🚀 Quick Start

1. **Installation**: See the main [README.md](../README.md) in the project root
2. **Vector Database Setup**: Read [VECTOR_DB_ABSTRACTION.md](VECTOR_DB_ABSTRACTION.md)
3. **API Usage**: Check the [Presentation](PRESENTATION.md) for API examples
4. **Contributing**: Review [CONTRIBUTING.md](CONTRIBUTING.md)
5. **Testing**: See [CI_CD.md](CI_CD.md) for testing and CI information

## 🔧 Architecture Overview

RagMe is built with a modular, vector database agnostic architecture:

- **Vector Database Abstraction**: Support for multiple vector databases (Milvus, Weaviate, etc.)
- **REST API**: FastAPI-based API for programmatic access
- **File Monitoring**: Automatic processing of PDF and DOCX files
- **New Frontend**: Modern TypeScript/Express interface with three-pane layout ⭐ **DEFAULT**

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
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- Main [README.md](../README.md) - Installation and basic usage

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style and standards
- Testing requirements
- Pull request process
- Development setup
- Frontend development

## 🧪 Testing and Code Quality

The project includes comprehensive testing and code quality enforcement:

### Testing

- **Enhanced Test Suite**: 71+ tests covering all major functionality with organized subcommands
- **Test Categories**: Unit, API, MCP, and Integration tests with clear separation
- **Smart Cleanup**: Integration tests properly clean up test documents from vector database
- **Modular test organization** with separate test files for each component
- **Automated CI/CD** with GitHub Actions
- **Multi-Python version support** (3.10, 3.11, 3.12)
- **Mocked dependencies** for reliable testing
- **Vector database abstraction tests** with full coverage
- **Integration testing** for all services
- **Frontend testing** with TypeScript compilation

### Code Quality

- **Automated linting** with Ruff for code quality enforcement
- **Consistent formatting** across the entire codebase
- **Type hints** required for all functions and methods
- **Exception handling** standards (B904 compliance)
- **Import organization** and sorting
- **CI enforcement** - all linting checks must pass before merging
- **Frontend linting** with ESLint and Prettier

### Test Structure

The test suite is organized with clear categories and subcommands:

```bash
./test.sh unit         # Unit tests (core functionality, vector databases, agents)
./test.sh api          # API tests (FastAPI endpoints, response validation)
./test.sh mcp          # MCP tests (Model Context Protocol server)
./test.sh integration  # Integration tests (end-to-end system testing)
./test.sh all          # Run all test categories
./test.sh help         # Show detailed help and test categories
```

**Test Organization**:
```
tests/
├── test_vector_db_base.py      # Tests for abstract base class
├── test_vector_db_weaviate.py  # Tests for Weaviate implementation
├── test_vector_db_milvus.py    # Tests for Milvus implementation
├── test_vector_db_factory.py   # Tests for factory function
├── test_api.py                 # API endpoint tests
├── test_ragme_agent.py         # Agent functionality tests
├── test_local_agent.py         # File monitoring tests
└── tools/
    └── test-integration.sh     # End-to-end integration tests
```

Each test file focuses on its specific component, making it easy to:
- Run tests for specific vector database implementations
- Add new tests when adding new database support
- Maintain clean separation of test concerns
- Debug issues in specific components
- Clean up test artifacts automatically

See [CI_CD.md](CI_CD.md) for detailed testing information.

## 🚀 Key Features

### Vector Database Support
- **Weaviate Cloud**: Recommended managed vector database service
- **Local Weaviate**: Podman-based local deployment (recommended for local development)
- **Milvus Lite**: Alternative for local development (no server setup)
- **Extensible**: Easy to add new vector databases

### User Interfaces
- **New Frontend**: Modern three-pane layout with real-time features ⭐ **DEFAULT**
  - **MCP Server Tools**: Configure and enable/disable MCP tool servers
  - **Recent Prompts & Ideas**: Quick access to sample prompts and chat history
  - **Interactive Visualizations**: D3.js charts with click-to-scroll functionality
  - **Smart Document Management**: Automatic chunking and grouped display

- **Chrome Extension**: Browser integration for web content capture

### Process Management
- **Comprehensive scripts**: Start, stop, restart, and status checking
- **Service monitoring**: Real-time log monitoring and debugging
- **Error handling**: Graceful error handling and recovery
- **Port management**: Automatic port conflict resolution

### Development Tools
- **Linting**: Automated code quality enforcement
- **Testing**: Comprehensive test suite with mocking
- **Documentation**: Complete documentation with examples
- **CI/CD**: Automated testing and quality checks

## 🖼️ Image Collections & Multiple Collections Support

RAGme supports multiple collections per vector database to enable different content types (e.g., text documents and images). The backend exposes configured collections via `/config`, and the frontend top bar shows `Collections:` with file and image icons. See `docs/CONFIG.md` for configuration examples.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details. 