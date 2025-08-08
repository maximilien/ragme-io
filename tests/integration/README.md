# RAGme AI Integration Tests

This directory contains comprehensive integration tests for RAGme AI that test both the API and Agent levels of the system.

## Overview

The integration tests implement a complete scenario that validates the end-to-end functionality of the RAGme AI system:

1. **Step 0**: Start with empty collection verification
2. **Step 1**: Query with empty collection (should return no information)
3. **Step 2**: Add documents one by one and verify queries return appropriate results
4. **Step 3**: Remove documents one by one and verify queries return no results

## Test Files

### Core Test Files

- **`test_apis.py`**: API-level integration tests using HTTP requests to the RAGme API endpoints
- **`test_agents.py`**: Agent-level integration tests using the RagMeAgent directly
- **`run_integration_tests.py`**: Python test runner with command-line interface
- **`test-integration-agents.sh`**: Shell script for easy test execution

### Test Data

- **Test URL**: `https://maximilien.org` - Used for testing URL document addition
- **Test PDF**: `tests/fixtures/pdfs/askg.pdf` - Used for testing PDF document addition
- **Test Queries**:
  - "who is Maximilien?" - Should return information about Maximilien from the URL document
  - "give detailed report on AskG" - Should return detailed information about AskG from the PDF document

## Prerequisites

Before running the integration tests, ensure:

1. **RAGme services are running**:
   ```bash
   ./start.sh
   ```

2. **Test PDF exists**:
   ```bash
   ls tests/fixtures/pdfs/askg.pdf
   ```

3. **Python dependencies are installed**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

4. **Configuration file exists**:
   ```bash
   ls config.yaml
   ```
   
   The tests will automatically backup your `config.yaml`, modify it to use a test collection (`test_integration`), and restore it after the tests complete.

## Running the Tests

### Using the Main Test Script (Recommended)

The easiest way to run integration tests is using the main test script:

```bash
# Run all integration tests (API + Agent)
./test.sh integration

# Run only agent integration tests
./test.sh agents

# Run all tests including integration
./test.sh all
```

### Using the Integration Test Script

For more control over integration tests, use the dedicated integration test script:

```bash
# Run all integration tests
./tools/test-integration-agents.sh

# Run only API tests
./tools/test-integration-agents.sh --api

# Run only Agent tests
./tools/test-integration-agents.sh --agents

# Run tests with pytest framework
./tools/test-integration-agents.sh --pytest

# Start services before running tests
./tools/test-integration-agents.sh --start-services --all

# Stop services after running tests
./tools/test-integration-agents.sh --all --cleanup

# Clean up test configuration files (if needed)
./tools/test-integration-agents.sh --cleanup-config

### Using the Python Test Runner

```bash
# Run all tests
python tests/integration/run_integration_tests.py

# Run specific test types
python tests/integration/run_integration_tests.py --api
python tests/integration/run_integration_tests.py --agents

# Use pytest framework
python tests/integration/run_integration_tests.py --api --pytest
```

### Using Pytest Directly

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test files
pytest tests/integration/test_apis.py -v
pytest tests/integration/test_agents.py -v

# Run specific test methods
pytest tests/integration/test_apis.py::TestAPIIntegration::test_complete_scenario -v
```

## Test Scenarios

### API Integration Tests (`test_apis.py`)

Tests the RAGme API endpoints directly:

- **Endpoints tested**:
  - `POST /query` - Query the RAG system
  - `POST /add-urls` - Add URL documents
  - `POST /upload-files` - Upload PDF documents
  - `GET /list-documents` - List all documents
  - `DELETE /delete-document/{id}` - Delete specific documents
  - `POST /tool/process_pdf` (MCP) - Process PDF files

- **Test flow**:
  1. Verify empty collection
  2. Test queries with empty collection
  3. Add URL document and verify query returns information
  4. Add PDF document and verify query returns detailed information
  5. Remove documents one by one and verify queries return no information

### Agent Integration Tests (`test_agents.py`)

Tests the RagMeAgent functionality:

- **Agent features tested**:
  - RagMeAgent initialization and configuration
  - Query processing through the agent
  - Document addition via agent commands
  - Document removal via agent commands
  - Agent memory and state management

- **Test flow**:
  1. Verify empty collection using agent
  2. Test queries with empty collection using agent
  3. Add URL document via agent and verify query returns information
  4. Add PDF document via MCP server and verify query returns detailed information
  5. Remove documents via agent and verify queries return no information

## Test Validation

### Expected Behaviors

1. **Empty Collection Queries**: Should return responses indicating no information found
2. **URL Document Queries**: Should return information about Maximilien from maximilien.org
3. **PDF Document Queries**: Should return detailed information about AskG from the PDF
4. **Document Removal**: Should return no information after documents are removed

### Response Validation

The tests validate that:

- **No information responses** contain phrases like: "no information", "no documents", "not found", "no data", "don't have", "cannot find", "no relevant"
- **Information responses** contain relevant keywords from the source documents
- **Detailed responses** are sufficiently long (>100 characters) and contain structured content

## Configuration Management

The integration tests use a dedicated test collection to avoid polluting your main development collection:

### Automatic Configuration Management

The tests automatically:
1. **Backup** your original `config.yaml` to `config.yaml.test_backup`
2. **Modify** the config to use collection name `test_integration` for all vector databases
3. **Restore** the original config after tests complete
4. **Clean up** temporary files

### Test Configuration

- **API Base URL**: `http://localhost:8021`
- **MCP Base URL**: `http://localhost:8022`
- **Test Collection Name**: `test_integration`
- **Test Documents**: 
  - URL: `https://maximilien.org`
  - PDF: `tests/fixtures/pdfs/askg.pdf`

### Manual Configuration Cleanup

If tests are interrupted and don't complete cleanup automatically:

```bash
# Clean up test configuration files
./tools/test-integration-agents.sh --cleanup-config
```

This will restore your original `config.yaml` and remove backup files.

## Troubleshooting

### Common Issues

1. **Services not running**:
   ```bash
   ./start.sh
   ```

2. **Test PDF missing**:
   ```bash
   # Ensure the test PDF exists
   ls tests/fixtures/pdfs/askg.pdf
   ```

3. **Configuration issues**:
   ```bash
   # Clean up test configuration files
   ./tools/test-integration-agents.sh --cleanup-config
   ```

4. **Port conflicts**:
   ```bash
   # Check if ports are in use
   lsof -i :8021
   lsof -i :8022
   ```

5. **Vector database issues**:
   ```bash
   # Restart vector database
   ./stop.sh
   ./start.sh
   ```

### Debug Mode

Run tests with verbose output:

```bash
# Enable debug output
pytest tests/integration/ -v -s --tb=long

# Run with custom test runner debug
python tests/integration/run_integration_tests.py --api --pytest
```

### Logs

Check the following logs for debugging:

- **API logs**: `logs/api.log`
- **MCP logs**: `logs/mcp.log`
- **Agent logs**: `logs/agents.log`

## Future Enhancements

1. **MCP Agent Integration**: Currently PDFs are added via MCP server directly. Future TODO is to integrate MCP tools with the RagMeAgent.
2. **Additional Document Types**: Extend tests to cover more document types (DOCX, TXT, etc.)
3. **Performance Testing**: Add performance benchmarks and load testing
4. **Multi-User Testing**: Test concurrent user scenarios
5. **Error Recovery**: Test system behavior under various error conditions

## Contributing

When adding new integration tests:

1. Follow the existing test structure and naming conventions
2. Include proper setup and cleanup
3. Add comprehensive error handling
4. Document any new test scenarios
5. Update this README with new test information
