# 🛠️ RAGme Development Guide

This guide covers development practices, testing, code quality, and contribution guidelines for RAGme.

## 🚀 Development Setup

### Prerequisites

1. **Python 3.12+**: Latest Python version recommended
2. **uv**: Fast Python package manager
3. **Node.js 18+**: For frontend development
4. **Git**: Version control
5. **Vector Database**: Weaviate (recommended) or Milvus

### Development Environment

```bash
# Clone the repository
gh repo clone maximilien/ragme-io
cd ragme-io

# Setup development environment
./setup.sh --force

# Activate virtual environment
source .venv/bin/activate

# Install development dependencies
uv sync --extra dev
```

### Development Workflow

```bash
# Start development services
./start.sh

# Compile frontend after changes
./start.sh compile-frontend

# Restart specific services
./start.sh restart-backend  # API, MCP, Agent
./start.sh restart-frontend # Frontend only

# Monitor logs during development
./tools/tail-logs.sh all
```

## 🧪 Testing

### Test Structure

RAGme uses a comprehensive testing framework with multiple test categories:

```
tests/
├── test_vector_db_base.py      # Tests for abstract base class
├── test_vector_db_weaviate.py  # Tests for Weaviate implementation
├── test_vector_db_milvus.py    # Tests for Milvus implementation
├── test_vector_db_factory.py   # Tests for factory function
├── test_vector_db.py           # Compatibility layer tests
├── test_api.py                 # API endpoint tests
├── test_mcp.py                 # MCP server tests
├── integration/                # Integration tests
│   ├── test_agents.py          # Agent integration tests
│   ├── test_document_processing.py # Document processing tests
│   └── test_image_processing.py # Image processing tests
└── fixtures/                   # Test data and fixtures
```

### Running Tests

```bash
# Run all tests (unit + API + MCP + integration)
./test.sh all

# Run specific test categories
./test.sh unit         # Unit tests only
./test.sh api          # API tests only  
./test.sh mcp          # MCP server tests only
./test.sh integration  # Integration tests only

# Run tests with coverage
uv run --active python -m pytest --cov=src/ragme tests/

# Show test help
./test.sh help
```

### Safe Integration Testing

For integration tests that require a clean environment:

```bash
# Run integration tests with automatic environment backup/restore
./tools/test-with-backup.sh integration-fast  # Fast integration tests (recommended)
./tools/test-with-backup.sh integration       # Full integration tests
./tools/test-with-backup.sh agents           # Agent integration tests
```

The safe testing approach automatically:
- Backs up your current `.env` and `config.yaml`
- Sets collections to `test_integration` and `test_integration_images`
- Runs the specified tests
- Restores your original configuration (regardless of test outcome)

### Test Categories

#### Unit Tests
- **Core functionality**: Core RAGme classes and utilities
- **Vector databases**: Database abstraction and implementations
- **Agents**: Agent system and tool functionality
- **Utilities**: Helper functions and utilities

#### API Tests
- **FastAPI endpoints**: All REST API endpoints
- **Response validation**: Response format and content validation
- **Request handling**: Input validation and error handling
- **Authentication**: MCP server authentication flow

#### MCP Tests
- **Model Context Protocol**: MCP server compliance
- **Endpoint validation**: MCP endpoint functionality
- **Protocol compliance**: Standard MCP protocol adherence
- **Tool integration**: MCP tool server integration

#### Integration Tests
- **End-to-end system**: Complete system functionality
- **Service communication**: Inter-service communication
- **File monitoring**: Watch directory functionality
- **Document processing**: Complete document processing pipeline

## 🔍 Code Quality

### Linting and Formatting

We maintain high code quality standards using automated linting and formatting:

```bash
# Run linting checks (required before submitting PRs)
./tools/lint.sh

# Auto-fix linting issues where possible
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/ examples/

# Validate configuration file
./tools/config-validator.sh
```

### Code Quality Tools

- **Ruff**: Fast Python linter and formatter
- **Type Hints**: Comprehensive type annotations
- **Docstrings**: Google-style docstrings for all public APIs
- **Import Sorting**: Consistent import organization

### Pre-commit Hooks

Set up pre-commit hooks for automatic code quality checks:

```bash
# Install pre-commit
uv run pip install pre-commit

# Install git hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## 🏗️ Architecture Development

### Three-Agent System

The three-agent architecture provides intelligent query routing and specialized processing:

#### 1. **RagMeAgent (Dispatcher)**
- **Location**: `src/ragme/agents/ragme_agent.py`
- **Purpose**: Routes user queries to appropriate specialized agents
- **Development**: Add new query classification rules and routing logic

#### 2. **FunctionalAgent**
- **Location**: `src/ragme/agents/functional_agent.py`
- **Purpose**: Handles tool-based operations and document management
- **Development**: Add new tools and document operations

#### 3. **QueryAgent**
- **Location**: `src/ragme/agents/query_agent.py`
- **Purpose**: Answers questions about document content using advanced RAG
- **Development**: Improve query processing and response generation

#### 4. **RagMeTools**
- **Location**: `src/ragme/agents/tools.py`
- **Purpose**: Centralized tool collection for all RagMe operations
- **Development**: Add new tools and enhance existing functionality

### Vector Database Abstraction

The vector database abstraction allows easy addition of new database backends:

#### Adding a New Vector Database

1. **Create Implementation Class**:
   ```python
   # src/ragme/vdbs/vector_db_new.py
   from .vector_db_base import VectorDatabase
   
   class NewVectorDatabase(VectorDatabase):
       def __init__(self, config: dict):
           # Implementation
           pass
       
       def add_documents(self, documents: List[Document]) -> bool:
           # Implementation
           pass
       
       # Implement all abstract methods
   ```

2. **Add Factory Support**:
   ```python
   # src/ragme/vdbs/vector_db_factory.py
   def create_vector_database(config: dict) -> VectorDatabase:
       db_type = config.get("type", "milvus")
       
       if db_type == "new":
           return NewVectorDatabase(config)
       # ... existing cases
   ```

3. **Add Tests**:
   ```python
   # tests/test_vector_db_new.py
   class TestNewVectorDatabase:
       def test_add_documents(self):
           # Test implementation
           pass
   ```

4. **Update Configuration**:
   ```yaml
   # config.yaml
   vector_databases:
     databases:
       - name: "new-db"
         type: "new"
         # New database specific configuration
   ```

### Storage Service Development

The storage service abstraction supports multiple backends:

#### Adding a New Storage Backend

1. **Create Storage Implementation**:
   ```python
   # src/ragme/utils/storage_new.py
   from .storage_base import StorageService
   
   class NewStorageService(StorageService):
       def __init__(self, config: dict):
           # Implementation
           pass
       
       def upload_file(self, file_path: str, object_name: str = None) -> str:
           # Implementation
           pass
       
       # Implement all abstract methods
   ```

2. **Add Factory Support**:
   ```python
   # src/ragme/utils/storage_factory.py
   def create_storage_service(config: dict) -> StorageService:
       storage_type = config.get("type", "minio")
       
       if storage_type == "new":
           return NewStorageService(config)
       # ... existing cases
   ```

## 🤝 Contributing

### Contribution Guidelines

We welcome contributions! Please follow these guidelines:

#### 1. **Fork and Clone**
```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/your-username/ragme-io.git
cd ragme-io

# Add upstream remote
git remote add upstream https://github.com/maximilien/ragme-io.git
```

#### 2. **Create Feature Branch**
```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/your-bug-description
```

#### 3. **Development Workflow**
```bash
# Make your changes
# Run tests
./test.sh all

# Run linting
./tools/lint.sh

# Commit with descriptive message
git commit -m "feat: add new vector database support

- Add NewVectorDatabase implementation
- Include comprehensive test coverage
- Update documentation with usage examples"
```

#### 4. **Submit Pull Request**
- Create a pull request with a clear description
- Include tests for new functionality
- Update documentation as needed
- Ensure all CI checks pass

### Commit Message Convention

We follow conventional commit messages:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(agents): add new query classification rule
fix(api): resolve CORS issue with frontend
docs(config): update configuration examples
test(vdb): add comprehensive test coverage
```

### Pull Request Guidelines

#### Before Submitting
- [ ] All tests pass (`./test.sh all`)
- [ ] Code is linted (`./tools/lint.sh`)
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts

#### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Test addition

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes
```

## 🔧 Development Tools

### Debugging

#### Log Monitoring
```bash
# Monitor all service logs
./tools/tail-logs.sh all

# Monitor specific services
./tools/tail-logs.sh api        # API logs (port 8021)
./tools/tail-logs.sh mcp        # MCP logs (port 8022)
./tools/tail-logs.sh frontend   # Frontend logs (port 8020)
./tools/tail-logs.sh minio      # MinIO logs (port 9000)
```

#### Debug Mode
```bash
# Enable debug logging
export RAGME_DEBUG=true
./start.sh

# Or set in .env
RAGME_DEBUG=true
```

### Performance Optimization

#### Query Threshold Optimization
```bash
# Find optimal threshold for your document collection
./tools/optimize.sh query-threshold

# Custom range optimization
./tools/optimize.sh query-threshold 0.3 0.9
```

#### Vector Database Management
```bash
# Show virtual structure (chunks, grouped images, documents)
./tools/vdb.sh virtual-structure

# Show how documents are grouped into chunks
./tools/vdb.sh document-groups

# Delete document and all its chunks/images
./tools/vdb.sh delete-document <file>
```

### Configuration Management

#### Environment Switching
```bash
# Switch between different application environments
cp .env.production .env
./stop.sh && ./start.sh

# Or for development
cp .env.development .env
./stop.sh && ./start.sh
```

#### Configuration Validation
```bash
# Validate configuration file
./tools/config-validator.sh

# Check for configuration issues
./tools/config-validator.sh --strict
```

## 📚 Documentation Development

### Documentation Structure

```
docs/
├── ARCHITECTURE.md      # Technical architecture
├── USER_GUIDE.md        # User-facing documentation
├── DEVELOPMENT.md       # Development guide (this file)
├── CONFIGURATION.md     # Configuration reference
├── TROUBLESHOOTING.md   # Troubleshooting guide
└── README.md           # Documentation index
```

### Writing Documentation

#### Guidelines
- Use clear, concise language
- Include code examples
- Add screenshots for UI features
- Keep documentation up-to-date with code changes
- Use consistent formatting and structure

#### Documentation Updates
```bash
# When making code changes, update relevant documentation
# Update README.md for new features
# Update USER_GUIDE.md for user-facing changes
# Update ARCHITECTURE.md for architectural changes
```

## 🚀 Deployment

### Local Development Deployment
```bash
# Standard development setup
./setup.sh
./start.sh

# Access services
# Frontend: http://localhost:8020
# API: http://localhost:8021
# MCP: http://localhost:8022
# MinIO: http://localhost:9001
```

### Production Deployment

#### Environment Configuration
```bash
# Production environment variables
export RAGME_ENV=production
export VECTOR_DB_TYPE=weaviate
export WEAVIATE_URL=your-weaviate-cluster.weaviate.cloud
export WEAVIATE_API_KEY=your-api-key

# Storage configuration
export S3_ENDPOINT=https://s3.amazonaws.com
export S3_ACCESS_KEY=your-access-key
export S3_SECRET_KEY=your-secret-key
export S3_BUCKET_NAME=your-bucket-name
```

#### Service Management
```bash
# Production service management
./start.sh

# Monitor services
./stop.sh status

# Restart services
./stop.sh restart
```

## 🔮 Future Development

### Planned Features
1. **Multi-User Support**: SaaS architecture with user isolation
2. **Advanced Security**: HTTPS, authentication, and authorization
3. **Content Types**: Support for audio and video
4. **Integration APIs**: Email, Slack, and social media ingestion
5. **Advanced Analytics**: Usage patterns and performance metrics
6. **Microservices**: Further service decomposition for scalability
7. **Containerization**: Docker and Kubernetes deployment support

### Development Roadmap
- **Q1**: Multi-user authentication and authorization
- **Q2**: Advanced content type support (audio, video)
- **Q3**: Integration APIs and third-party services
- **Q4**: Performance optimization and scalability improvements

### Contributing to Future Features
- Check the [Issues](https://github.com/maximilien/ragme-io/issues) page
- Join discussions in [Discussions](https://github.com/maximilien/ragme-io/discussions)
- Submit proposals for new features
- Help implement planned features

## 📞 Getting Help

### Development Support
- **Issues**: [GitHub Issues](https://github.com/maximilien/ragme-io/issues)
- **Discussions**: [GitHub Discussions](https://github.com/maximilien/ragme-io/discussions)
- **Documentation**: [docs/](docs/) directory
- **Code**: [Source Code](https://github.com/maximilien/ragme-io)

### Community Guidelines
- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the project's code of conduct

---

**Happy coding! 🚀**

Created with ❤️ by @maximilien
