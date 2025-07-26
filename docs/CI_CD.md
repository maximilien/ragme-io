# CI/CD Pipeline

This document describes the Continuous Integration and Continuous Deployment setup for RagMe AI.

## 🚀 GitHub Actions CI

The project uses GitHub Actions for automated testing and quality assurance.

### Workflow Location

The CI workflow is defined in `.github/workflows/ci.yml`

### Triggers

The CI pipeline runs automatically on:

- **Push** to `main` or `develop` branches
- **Pull Request** targeting `main` or `develop` branches

### Jobs

#### Lint Job

The lint job runs code quality checks before testing:

- **Platform**: Ubuntu Latest
- **Python Version**: 3.10
- **Dependencies**: Uses `uv` for fast dependency management
- **Lint Command**: Runs `./lint.sh` script
- **Purpose**: Ensures code quality and consistency
- **Failure**: Blocks test job if linting fails

#### Test Job

The main test job runs the complete test suite:

- **Dependencies**: Requires lint job to pass first
- **Matrix Strategy**: Tests against Python 3.10, 3.11, and 3.12
- **Platform**: Ubuntu Latest
- **Dependencies**: Uses `uv` for fast dependency management
- **Test Command**: Runs `./test.sh` script
- **Caching**: Caches virtual environment and dependencies for faster builds

#### Test Coverage

The CI runs **72 tests** covering:

- ✅ API endpoints (`test_api.py`)
- ✅ JSON processing (`test_add_json.py`)
- ✅ Web crawling (`test_common.py`)
- ✅ File monitoring (`test_local_agent.py`)
- ✅ Core RAG functionality (`test_ragme.py`)
- ✅ Agent functionality (`test_ragme_agent.py`)
- ✅ Vector database abstraction (`test_vector_db.py`, `test_vector_db_base.py`, `test_vector_db_weaviate.py`, `test_vector_db_milvus.py`, `test_vector_db_factory.py`)

### Artifacts

The CI pipeline uploads test artifacts:

- **Test Results**: `.pytest_cache/` directory
- **Retention**: 7 days
- **Access**: Available in GitHub Actions UI

## 🛠️ Local Development

### Running Tests Locally

```bash
# Run unit tests
./test.sh

# Run specific test file
uv run pytest tests/test_api.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/ragme

# Run integration tests (requires services to be running)
./test-integration.sh
```

### Running Linting Locally

```bash
# Run all linting checks
./lint.sh

# Run linting on specific directories
uv run ruff check src/
uv run ruff check tests/
uv run ruff check examples/

# Auto-fix linting issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/ examples/
```

### Test Script

The `./test.sh` script:

1. **Sets up environment**: Ensures proper Python path
2. **Runs pytest**: Executes all test files
3. **Suppresses warnings**: Filters out Pydantic deprecation warnings
4. **Reports results**: Shows test summary

### Test Structure

#### Unit Tests
```
tests/
├── test_add_json.py      # JSON processing tests
├── test_api.py           # FastAPI endpoint tests
├── test_common.py        # Web crawling tests
├── test_local_agent.py   # File monitoring tests
├── test_ragme.py         # Core RAG tests
├── test_ragme_agent.py   # Agent tests
├── test_vector_db.py     # Vector database compatibility layer
├── test_vector_db_base.py # Abstract base class tests
├── test_vector_db_weaviate.py # Weaviate implementation tests
├── test_vector_db_milvus.py # Milvus implementation tests
└── test_vector_db_factory.py # Factory function tests
```

#### Integration Tests

The project includes comprehensive integration testing via `test-integration.sh`:

**What it tests:**
1. **Service Status** - All services (API, MCP, UI) are running and accessible
2. **Vector Database** - Connection and basic operations
3. **MCP Server** - Health check and document processing
4. **RagMe API** - Endpoints and functionality
5. **Local Agent** - File monitoring and processing
6. **RagMe Agent** - Query processing and responses
7. **Streamlit UI** - Web interface accessibility
8. **File Monitoring** - PDF/DOCX file processing (optional)

**How to run:**
```bash
# Start services first
./start.sh

# Run integration tests
./test-integration.sh
```

**Integration test features:**
- **Colored output** for easy reading
- **Comprehensive checks** of all system components
- **Automatic cleanup** of test files
- **Detailed error reporting** for troubleshooting
- **Service health validation** before testing

Each test file focuses on its specific component, making it easy to:
- Run tests for specific vector database implementations
- Add new tests when adding new database support
- Maintain clean separation of test concerns
- Debug issues in specific components

## 🔧 CI Configuration

### Dependencies

The CI uses the same dependency management as local development:

- **Package Manager**: `uv` for fast Python package management
- **Lock File**: `uv.lock` for reproducible builds
- **Development Dependencies**: Installed via `uv sync --extra dev`
  - **ruff**: For linting and code formatting
  - **pytest**: For running tests
  - **pytest-cov**: For test coverage
  - **requests-mock**: For mocking HTTP requests

### Environment

- **Python Versions**: 3.10, 3.11, 3.12
- **Operating System**: Ubuntu Latest
- **Architecture**: x64

### Caching Strategy

```yaml
cache:
  path: |
    .venv
    uv.lock
  key: ${{ runner.os }}-uv-${{ hashFiles('**/uv.lock') }}
  restore-keys: |
    ${{ runner.os }}-uv-
```

## 📊 Monitoring

### CI Status

- **Green**: All tests passing across all Python versions
- **Red**: Tests failing - requires immediate attention
- **Yellow**: Tests running or partially complete

### Test Metrics

- **Total Tests**: 72
- **Coverage**: Core functionality and edge cases
- **Execution Time**: ~1.5-2 minutes per Python version
- **Reliability**: High - tests are isolated and mocked

## 🚨 Troubleshooting

### Common Issues

1. **Test Failures**: Check if all dependencies are properly mocked
2. **Environment Issues**: Ensure `uv.lock` is up to date
3. **Timeout Issues**: Tests should complete within 10 minutes

### Debugging

```bash
# Run tests with detailed output
uv run pytest -vvv

# Run specific failing test
uv run pytest tests/test_specific.py::test_specific_function -v

# Check test dependencies
uv run pip list
```

## 🔮 Future Enhancements

### Implemented Features

1. ✅ **Linting**: Ruff-based linting and formatting checks
2. ✅ **Code Quality**: Automated code style enforcement
3. ✅ **Formatting**: Consistent code formatting across the codebase

### Planned Additions

1. **Security**: Add bandit and safety checks
2. **Coverage Reports**: Generate and upload coverage reports
3. **Performance Tests**: Add performance benchmarking
4. **Integration Tests**: Add end-to-end testing

### Code Quality

- **Type Checking**: Add mypy for static type checking
- **Documentation**: Add docstring coverage checks

## 📚 Related Documentation

- **[Contributing Guidelines](CONTRIBUTING.md)** - Development workflow
- **[Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Testing strategy
- **[Project Overview](PRESENTATION.md)** - Architecture details 