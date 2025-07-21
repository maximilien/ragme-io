# Contributing to RagMe AI

Thank you for your interest in contributing to RagMe AI! This document provides guidelines and instructions for contributing to this project.

## 📚 Documentation Structure

Before contributing, please familiarize yourself with our documentation:

- **[📖 Documentation Index](README.md)** - Overview of all documentation
- **[🔧 Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Understanding the database layer
- **[📋 Project Overview](PRESENTATION.md)** - Complete project overview

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
  * Which vector database are you using? (Weaviate, Milvus, etc.)

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

## Style Guides

### Python Style Guide

* Use 4 spaces for indentation rather than tabs
* Keep lines to a maximum of 79 characters
* Use docstrings for all public modules, functions, classes, and methods
* Use spaces around operators and after commas
* Follow PEP 8 guidelines
* Include warning filters for clean output in test files

### JavaScript Style Guide

* Use 2 spaces for indentation rather than tabs
* Keep lines to a maximum of 100 characters
* Use semicolons
* Use single quotes for strings unless you are writing JSON
* Follow the Airbnb JavaScript Style Guide

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

## Development Process

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Testing

Before submitting a pull request, please ensure that:

1. All tests pass (`./tests.sh`)
2. The code is properly formatted
3. Documentation is updated
4. New tests are added for new functionality
5. Warning filters are included for clean test output

### Test Organization

The test suite follows the modular structure:

- **Base tests**: `test_vector_db_base.py` - Tests for abstract base class
- **Implementation tests**: `test_vector_db_[name].py` - Tests for specific implementations
- **Factory tests**: `test_vector_db_factory.py` - Tests for factory function
- **Compatibility tests**: `test_vector_db.py` - Tests for compatibility layer

Each test file should:
- Include appropriate warning filters
- Use mocking to avoid external dependencies
- Test both success and error cases
- Include proper cleanup in teardown methods

## License

By contributing to RagMe AI, you agree that your contributions will be licensed under its MIT License. 