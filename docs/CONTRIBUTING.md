# Contributing to RagMe AI

Thank you for your interest in contributing to RagMe AI! This document provides guidelines and instructions for contributing to this project.

## 📚 Documentation Structure

Before contributing, please familiarize yourself with our documentation:

- **[📖 Documentation Index](README.md)** - Overview of all documentation
- **[🔧 Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Understanding the database layer
- **[📋 Project Overview](PRESENTATION.md)** - Complete project overview

## 🆕 Recent Major Features

### 💡 Recent Prompts & Ideas
- **Smart prompt suggestions** with context-aware recommendations
- **New chat experience** with 5 sample prompts to help users get started
- **Ongoing chat support** showing 5 most recent user prompts + 3 sample prompts
- **Bottom sheet interface** with modern mobile-friendly design
- **Quick access** via history button positioned for easy reach
- **Seamless integration** - click to fill chat input, edit, and submit

### Smart Document Chunking
- **Automatic chunking** of large documents at sentence boundaries
- **Consistent processing** across all input methods (upload, watch directory, API)
- **Enhanced metadata** with chunk information and original filenames
- **Frontend grouping** of chunked documents for better UX

### Enhanced UI Features
- **Interactive visualizations** with D3.js charts and click-to-scroll functionality
- **Responsive design** with collapsible sidebars and smooth animations
- **Real-time synchronization** between document list and visualizations
- **Bulk operations** for document management and deletion

### Technical Improvements
- **Unified chunking logic** in `local_agent.py` and frontend processing
- **Improved performance** for large document handling
- **Better error handling** and user feedback
- **Enhanced debugging** with comprehensive logging

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for RagMe AI. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

#### Before Submitting A Bug Report

* Check the documentation for a list of common questions and problems.
* Perform a cursory search to see if the problem has already been reported. If it has, add a comment to the existing issue instead of opening a new one.

#### How Do I Submit A (Good) Bug Report?

Bugs are tracked as GitHub issues. Create an issue and provide the following information by filling in the template.

Explain the problem and include additional details to help maintainers reproduce the problem:

* Use a clear and descriptive title for the issue to identify the problem.
* Describe the exact steps which reproduce the problem in as many details as possible.
* Provide specific examples to demonstrate the steps.
* Describe the behavior you observed after following the steps and point out what exactly is the problem with that behavior.
* Explain which behavior you expected to see instead and why.
* Include screenshots and animated GIFs which show you following the described steps and clearly demonstrate the problem.
* If the problem wasn't triggered by a specific action, describe what you were doing before the problem happened.
* Include details about your configuration and environment:
  * Which version of RagMe AI are you using?
  * What's the name and version of the OS you're using?
  * Are you running RagMe AI in a virtual machine?
  * What are your environment variables?
  * Which vector database are you using? (Milvus, Weaviate, etc.)
  * Are you using the new frontend or legacy UI?

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for RagMe AI, including completely new features and minor improvements to existing functionality.

#### Before Submitting An Enhancement Suggestion

* Check the documentation for suggestions.
* Perform a cursory search to see if the enhancement has already been suggested. If it has, add a comment to the existing issue instead of opening a new one.

#### How Do I Submit A (Good) Enhancement Suggestion?

Enhancement suggestions are tracked as GitHub issues. Create an issue and provide the following information:

* Use a clear and descriptive title for the issue to identify the suggestion.
* Provide a step-by-step description of the suggested enhancement in as many details as possible.
* Provide specific examples to demonstrate the steps.
* Describe the current behavior and explain which behavior you expected to see instead and why.
* Include screenshots and animated GIFs which help you demonstrate the steps or point out the part of RagMe AI which the suggestion is related to.
* Explain why this enhancement would be useful to most RagMe AI users.

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Include screenshots and animated GIFs in your pull request whenever possible.
* Follow our coding conventions
* Document new code based on the Documentation Style Guide
* End all files with a newline

## 🏗️ Development Setup

### Installing Development Dependencies

Before contributing, install the development dependencies:

```bash
# Install development dependencies (includes ruff, pytest, etc.)
uv sync --extra dev
```

This installs:
- **ruff**: For linting and code formatting
- **pytest**: For running tests
- **pytest-cov**: For test coverage
- **requests-mock**: For mocking HTTP requests in tests

### Frontend Development Setup

For frontend development, you'll also need Node.js 18+:

```bash
# Install frontend dependencies
cd frontend
npm install

# Build TypeScript
npm run build

# Start development server
npm run dev
```

### Project Structure

```
ragme-ai/
├── docs/                    # 📚 Documentation
│   ├── README.md           # Documentation index
│   ├── VECTOR_DB_ABSTRACTION.md
│   ├── CONTRIBUTING.md     # This file
│   └── PRESENTATION.md
├── src/ragme/              # 🐍 Source code
│   ├── ragme.py            # Main RagMe class
│   ├── ragme_agent.py      # RagMeAgent class
│   ├── local_agent.py      # File monitoring agent
│   ├── vector_db.py        # Vector database compatibility layer
│   ├── vector_db_base.py   # Abstract base class
│   ├── vector_db_weaviate.py # Weaviate Cloud implementation
│   ├── vector_db_weaviate_local.py # Local Weaviate implementation
│   ├── vector_db_milvus.py # Milvus implementation (default)
│   ├── vector_db_factory.py # Factory function
│   ├── api.py              # FastAPI REST API
│   ├── mcp.py              # Model Context Protocol

│   ├── socket_manager.py   # WebSocket management
│   └── common.py           # Common utilities
├── frontend/               # 🌐 New frontend (TypeScript/Express)
│   ├── src/
│   │   └── index.ts        # Main server file
│   ├── public/
│   │   ├── index.html      # Main HTML file
│   │   ├── styles.css      # CSS styles
│   │   └── app.js          # Frontend JavaScript
│   ├── package.json
│   └── tsconfig.json
├── tests/                  # 🧪 Test suite
│   ├── test_vector_db_base.py
│   ├── test_vector_db_weaviate.py
│   ├── test_vector_db_milvus.py
│   ├── test_vector_db_factory.py
│   └── test_vector_db.py   # Compatibility layer
├── examples/               # 📖 Usage examples
├── chrome_ext/             # 🌐 Chrome extension
├── tools/                  # 🛠️ Development tools
│   ├── weaviate-local.sh   # Local Weaviate management
│   ├── tail-logs.sh        # Log monitoring
│   ├── lint.sh             # Code linting
│   └── podman-compose.weaviate.yml
└── watch_directory/        # 📁 Monitored directory
```

### Vector Database Development

When working with vector databases:

1. **Follow the abstraction pattern**: All vector database code should implement the `VectorDatabase` interface
2. **Create separate files**: New implementations should be in separate files (e.g., `vector_db_pinecone.py`)
3. **Add tests**: Include comprehensive tests in separate test files (e.g., `test_vector_db_pinecone.py`)
4. **Update factory function**: Add new database types to `create_vector_database()` in `vector_db_factory.py`
5. **Documentation**: Update [VECTOR_DB_ABSTRACTION.md](VECTOR_DB_ABSTRACTION.md) with new implementations
6. **Update compatibility layer**: Add imports to `vector_db.py` for backward compatibility

### Adding New Vector Database Support

To add support for a new vector database:

1. **Create implementation file**: `src/ragme/vector_db_[name].py`
2. **Create test file**: `tests/test_vector_db_[name].py`
3. **Update factory**: Add new type to `create_vector_database()` in `vector_db_factory.py`
4. **Update compatibility layer**: Add import to `vector_db.py`
5. **Update documentation**: Add new database to `VECTOR_DB_ABSTRACTION.md`
6. **Add environment variables**: Document required environment variables

Example for adding Pinecone support:

```python
# src/ragme/vector_db_pinecone.py
from .vector_db_base import VectorDatabase

class PineconeVectorDatabase(VectorDatabase):
    def __init__(self, collection_name: str = "RagMeDocs"):
        super().__init__(collection_name)
        # Initialize Pinecone client
        
    @property
    def db_type(self) -> str:
        return "pinecone"
        
    # Implement all required methods...
```

### Frontend Development

When working on the frontend:

1. **TypeScript**: All new code should be written in TypeScript
2. **ESLint**: Follow the ESLint configuration for code style
3. **Prettier**: Use Prettier for code formatting
4. **WebSocket**: Use Socket.IO for real-time communication
5. **D3.js**: Use D3.js for data visualization
6. **Responsive Design**: Ensure the UI works on desktop and mobile

### Process Management Development

When working on process management scripts:

1. **Bash Scripts**: Follow shell script best practices
2. **Error Handling**: Include proper error handling and cleanup
3. **Port Management**: Handle port conflicts gracefully
4. **PID Files**: Use PID files for process tracking
5. **Logging**: Provide clear status messages and logging

## Style Guides

### Python Style Guide

* Use 4 spaces for indentation rather than tabs
* Keep lines to a maximum of 79 characters
* Use docstrings for all public modules, functions, classes, and methods
* Use spaces around operators and after commas
* Follow PEP 8 guidelines
* Include warning filters for clean output in test files

### Code Quality and Linting

We use **Ruff** for linting and code formatting to maintain high code quality standards.

#### Linting Requirements

**All code must pass linting checks before submission.** This is enforced in our CI pipeline.

#### Running Linting

```bash
# Run all linting checks (required before PRs)
./tools/lint.sh

# Run linting on specific directories
uv run ruff check src/
uv run ruff check tests/
uv run ruff check examples/

# Auto-fix linting issues where possible
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/ examples/
```

#### Key Linting Rules

We enforce the following rules strictly:

- **B904**: Use `raise ... from e` for exception chaining
- **W291**: No trailing whitespace
- **W293**: No blank lines with whitespace
- **F841**: No unused variables
- **E722**: No bare `except` clauses (use `except Exception:`)
- **I001**: Proper import sorting and formatting
- **UP006**: Use modern type annotations (`list[str]` instead of `List[str]`)

#### Pre-commit Checklist

Before submitting any pull request, ensure:

1. ✅ **All tests pass**: `./test.sh`
2. ✅ **All linting checks pass**: `./tools/lint.sh`
3. ✅ **Code is properly formatted**: `uv run ruff format src/ tests/ examples/`
4. ✅ **No unused imports or variables** (F841)
5. ✅ **Proper exception handling** (B904 - use `raise ... from e`)
6. ✅ **No trailing whitespace** (W291)
7. ✅ **No blank lines with whitespace** (W293)
8. ✅ **Consistent code style** throughout

#### Linting Configuration

The project uses `pyproject.toml` for linting configuration:

```toml
[tool.ruff]
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long, handled by black
    "B008",  # do not perform function calls in argument defaults
    "B028",  # no explicit stacklevel keyword argument found
    "C901",  # too complex
]
```

#### Ignored Rules

Some rules are intentionally ignored:
- **B028**: No explicit stacklevel keyword argument found (suppressed for cleaner code)
- **E501**: Line too long (handled by formatter)
- **C901**: Too complex (allowed for complex business logic)

### JavaScript/TypeScript Style Guide

* Use 2 spaces for indentation rather than tabs
* Keep lines to a maximum of 100 characters
* Use semicolons
* Use single quotes for strings unless you are writing JSON
* Follow the Airbnb JavaScript Style Guide
* Use TypeScript for all new code
* Include proper type annotations

### Documentation Style Guide

* Use [Markdown](https://daringfireball.net/projects/markdown)
* Reference methods and classes in markdown with the following syntax:
  * Reference classes with `ClassName`
  * Reference instance methods with `ClassName#methodName`
  * Reference class methods with `ClassName.methodName`
* Update documentation in the `docs/` directory
* Keep the main `README.md` focused on quick start and overview

## Additional Notes

### Issue and Pull Request Labels

This section lists the labels we use to help us track and manage issues and pull requests.

* `bug` - Issues that are bugs
* `documentation` - Issues for improving or updating our documentation
* `enhancement` - Issues for enhancing a feature
* `good first issue` - Good for newcomers
* `help wanted` - Extra attention is needed
* `invalid` - Issues that can't be reproduced or are invalid
* `question` - Further information is requested
* `wontfix` - Issues that won't be fixed
* `vector-db` - Issues related to vector database implementations
* `frontend` - Issues related to the new frontend UI
* `process-management` - Issues related to service management

## Development Process

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Testing and Code Quality

Before submitting a pull request, please ensure that:

1. **All tests pass** (`./test.sh all`) - **REQUIRED**
2. **All linting checks pass** (`./tools/lint.sh`) - **REQUIRED**
3. **Code is properly formatted** (`uv run ruff format src/ tests/ examples/`)
4. **Documentation is updated** for any new features or changes
5. **New tests are added** for new functionality
6. **Warning filters are included** for clean test output
7. **No linting errors** in source files
8. **Consistent code style** throughout the codebase
9. **Integration tests pass** (`./test.sh integration`) - **For major changes**
10. **Frontend builds successfully** (`cd frontend && npm run build`) - **For frontend changes**

### Test Organization

The test suite is organized with clear categories and subcommands:

```bash
./test.sh unit         # Unit tests (core functionality, vector databases, agents)
./test.sh api          # API tests (FastAPI endpoints, response validation)
./test.sh mcp          # MCP tests (Model Context Protocol server)
./test.sh integration  # Integration tests (end-to-end system testing)
./test.sh all          # Run all test categories
./test.sh help         # Show detailed help and test categories
```

**Test Structure**:
- **Unit tests**: `test_vector_db_*.py`, `test_ragme_*.py`, `test_common.py` - Core functionality
- **API tests**: `test_api.py` - FastAPI endpoints and response validation
- **MCP tests**: MCP server functionality and protocol compliance
- **Integration tests**: `test-integration.sh` - End-to-end system testing with cleanup

Each test file should:
- Include appropriate warning filters
- Use mocking to avoid external dependencies
- Test both success and error cases
- Include proper cleanup in teardown methods
- Clean up test artifacts automatically (especially for integration tests)

### Process Management Testing

When testing process management:

1. **Test start/stop scripts**: Ensure services start and stop correctly
2. **Test status checking**: Verify status commands work properly
3. **Test error handling**: Test with missing dependencies or configuration
4. **Test port conflicts**: Verify graceful handling of port conflicts
5. **Test PID file management**: Ensure PID files are created and cleaned up

## License

By contributing to RagMe AI, you agree that your contributions will be licensed under its MIT License. 