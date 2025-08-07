# Agent Refactor Implementation

## Overview

This document describes the refactoring of the RagMeAgent into a cleaner three-agent architecture as outlined in the TODOs.

## Problem Statement

The original RagMeAgent was a monolithic class that:
1. Included all tools directly in the class
2. Mixed functional operations with query operations
3. Had complex routing logic embedded within the agent
4. Made it difficult to test and maintain individual components

## Solution: Three-Agent Architecture

### 1. RagMeAgent (Dispatcher)
- **Purpose**: Routes queries to appropriate specialized agents
- **Location**: `src/ragme/agents/ragme_agent.py`
- **Responsibilities**:
  - Determines query type (functional vs. content query)
  - Routes to FunctionalAgent or QueryAgent accordingly
  - Provides agent information and capabilities

### 2. FunctionalAgent
- **Purpose**: Handles tool-based operations using LlamaIndex FunctionAgent
- **Location**: `src/ragme/agents/functional_agent.py`
- **Responsibilities**:
  - Manages document collection operations (add, delete, list, reset)
  - Handles URL crawling and vector database info
  - Uses LlamaIndex FunctionAgent for tool execution
  - Identifies functional queries using keyword matching

### 3. QueryAgent
- **Purpose**: Answers questions about document content using vector search
- **Location**: `src/ragme/agents/query_agent.py`
- **Responsibilities**:
  - Performs vector similarity search on documents
  - Uses LLM to summarize and answer questions
  - Handles document content queries
  - Identifies question queries using keyword matching

### 4. RagMeTools
- **Purpose**: Centralized tool collection for RagMe operations
- **Location**: `src/ragme/agents/tools.py`
- **Responsibilities**:
  - Contains all tool functions (write, delete, list, etc.)
  - Provides clean interface for tool access
  - Separates tools from agent logic

## Key Features

### Query Routing
The dispatcher uses keyword-based routing:
- **Functional queries**: "add", "delete", "list", "reset", etc.
- **Content queries**: "what", "who", "explain", "describe", etc.

### Configuration
- Added `query.top_k` configuration for number of documents to retrieve
- Each agent can be configured independently
- Maintains backward compatibility with existing config structure

### Error Handling
- Graceful fallback to QueryAgent for unknown query types
- Proper error handling in each agent
- Maintains existing error handling patterns

## Testing

### Unit Tests
- Comprehensive tests for each agent component
- Tests for query routing logic
- Tests for tool functionality

### Integration Tests
- End-to-end tests for functional operations
- Tests for document addition and querying workflow
- Tests for agent dispatch functionality

## Benefits

1. **Separation of Concerns**: Each agent has a single, clear responsibility
2. **Testability**: Individual components can be tested in isolation
3. **Maintainability**: Easier to modify and extend individual agents
4. **Scalability**: New agent types can be added easily
5. **Clarity**: Clear distinction between functional operations and content queries

## Migration

The refactor maintains backward compatibility:
- Existing RagMeAgent interface is preserved
- All existing functionality continues to work
- Configuration changes are minimal and optional

## Future Enhancements

1. **MCP Agent**: Can be added as a third specialized agent
2. **Gateway Agent**: Could replace the dispatcher for more sophisticated routing
3. **Agent Configuration**: More granular configuration options
4. **Performance Optimization**: Agent-specific optimizations

## Files Changed

### New Files
- `src/ragme/agents/functional_agent.py`
- `src/ragme/agents/query_agent.py`
- `src/ragme/agents/tools.py`
- `tests/test_agent_refactor.py`

### Modified Files
- `src/ragme/agents/ragme_agent.py` (refactored)
- `tests/test_ragme_agent.py` (updated for new structure)
- `config.yaml.example` (added query configuration)
- `TODOs.md` (marked items as completed)

## Usage Example

```python
# Initialize the refactored agent
ragme_agent = RagMeAgent(ragme_instance)

# Functional query - routes to FunctionalAgent
result = await ragme_agent.run("add https://example.com to my collection")

# Content query - routes to QueryAgent
result = await ragme_agent.run("who is maximilien")

# Unknown query - defaults to QueryAgent
result = await ragme_agent.run("hello")
```

This refactor successfully addresses the original issues while providing a cleaner, more maintainable architecture for future development.
