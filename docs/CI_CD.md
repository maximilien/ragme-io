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

#### Test Job

The main test job runs the complete test suite:

- **Matrix Strategy**: Tests against Python 3.10, 3.11, and 3.12
- **Platform**: Ubuntu Latest
- **Dependencies**: Uses `uv` for fast dependency management
- **Test Command**: Runs `./tests.sh` script
- **Caching**: Caches virtual environment and dependencies for faster builds

#### Test Coverage

The CI runs **61 tests** covering:

- ✅ API endpoints (`test_api.py`)
- ✅ JSON processing (`test_add_json.py`)
- ✅ Web crawling (`test_common.py`)
- ✅ File monitoring (`test_local_agent.py`)
- ✅ Core RAG functionality (`test_ragme.py`)
- ✅ Agent functionality (`test_ragme_agent.py`)
- ✅ Vector database abstraction (`test_vector_db.py`)

### Artifacts

The CI pipeline uploads test artifacts:

- **Test Results**: `.pytest_cache/` directory
- **Retention**: 7 days
- **Access**: Available in GitHub Actions UI

## 🛠️ Local Development

### Running Tests Locally

```bash
# Run all tests
./tests.sh

# Run specific test file
uv run pytest tests/test_api.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/ragme
```

### Test Script

The `./tests.sh` script:

1. **Sets up environment**: Ensures proper Python path
2. **Runs pytest**: Executes all test files
3. **Suppresses warnings**: Filters out Pydantic deprecation warnings
4. **Reports results**: Shows test summary

### Test Structure

```
tests/
├── test_add_json.py      # JSON processing tests
├── test_api.py           # FastAPI endpoint tests
├── test_common.py        # Web crawling tests
├── test_local_agent.py   # File monitoring tests
├── test_ragme.py         # Core RAG tests
├── test_ragme_agent.py   # Agent tests
└── test_vector_db.py     # Vector database tests
```

## 🔧 CI Configuration

### Dependencies

The CI uses the same dependency management as local development:

- **Package Manager**: `uv` for fast Python package management
- **Lock File**: `uv.lock` for reproducible builds
- **Test Dependencies**: `requirements-test.txt`

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

- **Total Tests**: 61
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

### Planned Additions

1. **Linting**: Add pylint and flake8 checks
2. **Security**: Add bandit and safety checks
3. **Coverage Reports**: Generate and upload coverage reports
4. **Performance Tests**: Add performance benchmarking
5. **Integration Tests**: Add end-to-end testing

### Code Quality

- **Type Checking**: Add mypy for static type checking
- **Documentation**: Add docstring coverage checks
- **Formatting**: Add black and isort for code formatting

## 📚 Related Documentation

- **[Contributing Guidelines](CONTRIBUTING.md)** - Development workflow
- **[Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Testing strategy
- **[Project Overview](PRESENTATION.md)** - Architecture details 