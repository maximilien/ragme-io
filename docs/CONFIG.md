# 📋 RAGme Configuration System

RAGme now features a comprehensive configuration system that allows you to customize every aspect of the application for different client deployments. This document describes how to configure and customize RAGme using the `config.yaml` file.

## 🚀 Quick Start

1. **Copy the example configuration:**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **Edit the configuration:**
   ```bash
   # Edit the configuration file
   nano config.yaml
   ```

3. **Set environment variables:**
   ```bash
   # Copy and edit environment variables
   cp env.example .env
   nano .env
   ```

4. **Start RAGme:**
   ```bash
   ./start.sh
   ```

## 📁 Configuration File Structure

The configuration is organized into logical sections:

### 🏢 Application Metadata
```yaml
application:
  name: "RAGme"
  version: "0.1.0"
  title: "🤖 RAGme.ai Assistant"
  description: "RAGme is a RAG system that uses vector databases and LLMs for intelligent document retrieval."
```

### 🌐 Network Configuration
```yaml
network:
  api:
    host: "0.0.0.0"
    port: 8021
    cors_origins: ["*"]
  mcp:
    host: "0.0.0.0"
    port: 8022
  frontend:
    port: 3020
    api_url: "http://localhost:8021"
```

### 🔒 Security Settings
```yaml
security:
  csp:
    connect_src: ["'self'", "http://localhost:8021", "ws://localhost:8021"]
  file_upload:
    max_file_size_mb: 50
    allowed_extensions: [".pdf", ".docx", ".txt", ".md", ".json", ".csv"]
```

### 🗄️ Vector Database Configuration
```yaml
vector_databases:
  default: "weaviate-local"
  databases:
    - name: "weaviate-local"
      type: "weaviate-local"
      url: "http://localhost:8080"
      collection_name: "RagMeDocs"
      embedding_model: "text-embedding-3-large"
      chunk_size: 1000
      chunk_overlap: 100
```

### 🤖 LLM Configuration
```yaml
llm:
  default_model: "gpt-4o-mini"
  temperature: 0.7
  max_tokens: 4000
  summarization:
    model: "gpt-4o-mini"
    temperature: 0.1
    max_tokens: 2000
```

### 🔧 MCP Server Configuration
```yaml
mcp_servers:
  - name: "Google GDrive"
    icon: "fab fa-google-drive"
    authentication_type: "oauth"
    enabled: false
    description: "Access and process files from Google Drive"
```

### 🎨 Frontend Configuration
```yaml
frontend:
  settings:
    max_documents: 50
    auto_refresh: true
    refresh_interval_ms: 30000
    max_tokens: 4000
    temperature: 0.7
  ui:
    default_date_filter: "current"
    default_visualization: "graph"
    visualization_visible: true
```

### 🎯 Client Customization
```yaml
client:
  branding:
    primary_color: "#2563eb"
    secondary_color: "#64748b"
    accent_color: "#10b981"
    logo_url: ""
    favicon_url: ""
  welcome_message: "Welcome to RAGme! Upload documents or add URLs to get started."
  footer_text: "Powered by RAGme AI"
```

### 🚩 Feature Flags
```yaml
features:
  document_summarization: true
  mcp_integration: true
  real_time_updates: true
  file_upload: true
  url_crawling: true
  json_ingestion: true
  pattern_deletion: true
  authentication: false
  multi_tenant: false
```

## 🔧 Configuration Management

### 🔒 Security & Secret Protection

**CRITICAL SECURITY FEATURE**: RAGme's configuration system includes built-in protection against secret leakage:

#### ✅ **What's Protected:**
- **API Keys** (`WEAVIATE_API_KEY`, `OPENAI_API_KEY`, etc.)
- **Tokens** (authentication tokens, bearer tokens)
- **Passwords** and other credentials
- **Database connection strings** with embedded credentials
- **Environment variable values** (only placeholders are shown)

#### 🛡️ **Security Mechanisms:**

1. **Safe Configuration Endpoints:**
   - `/config` endpoint only returns filtered, safe configuration data
   - Sensitive sections (vector databases, environment, network) are excluded
   - API keys and tokens are never exposed to frontend

2. **Whitelist-Based Filtering:**
   - Only explicitly safe sections are included in API responses
   - MCP servers are filtered to remove authentication details
   - URLs are only included if they're localhost addresses

3. **Automatic Secret Detection:**
   - Automatically filters out fields containing: `api_key`, `token`, `password`, `secret`
   - Environment variable placeholders (`${VAR_NAME}`) are replaced with safe indicators
   - Vector database configurations with credentials are completely excluded

#### 🔍 **Security Testing:**

The system includes comprehensive security tests:

```bash
# Run security tests
python -m pytest tests/test_config_security.py -v
```

**Example of what's SAFE to expose:**
```json
{
  "application": {"name": "RAGme", "version": "1.0.0"},
  "frontend": {"settings": {"max_documents": 50}},
  "mcp_servers": [{"name": "Local Agent", "icon": "fas fa-flask"}]
}
```

**Example of what's PROTECTED:**
```yaml
# These are NEVER exposed via API endpoints:
vector_databases:
  databases:
    - api_key: "sk-secret-key-12345"  # 🔒 PROTECTED
    - token: "bearer-token-xyz"       # 🔒 PROTECTED
environment:
  required: ["OPENAI_API_KEY"]        # 🔒 PROTECTED
```

### Environment Variable Substitution

The configuration system supports environment variable substitution using the `${VAR_NAME}` syntax:

```yaml
vector_databases:
  databases:
    - name: "weaviate-cloud"
      type: "weaviate"
      url: "${WEAVIATE_URL}"
      api_key: "${WEAVIATE_API_KEY}"
```

### Required Environment Variables

Define required environment variables that must be set:

```yaml
environment:
  required:
    - "OPENAI_API_KEY"
  optional:
    - "WEAVIATE_API_KEY"
    - "WEAVIATE_URL"
```

### Configuration Loading

The configuration is loaded in this order:

1. **config.yaml** - Main configuration file
2. **Environment variables** - Override specific values
3. **Default values** - Fallback for missing configuration

## 🏗️ Deployment Scenarios

### 📊 Development Environment

```yaml
# config.yaml for development
application:
  name: "RAGme Dev"
  title: "🧪 RAGme Development"

vector_databases:
  default: "weaviate-local"

development:
  hot_reload: true
  debug_mode: true
  mock_external_services: false

logging:
  level: "DEBUG"
```

### 🚀 Production Environment

```yaml
# config.yaml for production
application:
  name: "RAGme Production"
  title: "🤖 RAGme.ai Assistant"

vector_databases:
  default: "weaviate-cloud"

production:
  hot_reload: false
  debug_mode: false
  compress_responses: true
  rate_limiting:
    enabled: true
    requests_per_minute: 100

logging:
  level: "WARNING"

security:
  file_upload:
    max_file_size_mb: 25
```

### 🏢 Enterprise Deployment

```yaml
# config.yaml for enterprise
application:
  name: "Enterprise RAG"
  title: "🏢 Enterprise Knowledge Assistant"

client:
  branding:
    primary_color: "#1f2937"
    secondary_color: "#374151"
    logo_url: "/assets/company-logo.png"
  welcome_message: "Welcome to the Enterprise Knowledge Assistant"
  footer_text: "© 2025 Your Company Name"

features:
  authentication: true
  multi_tenant: true
  document_summarization: true

monitoring:
  enabled: true
  metrics:
    - "document_count"
    - "query_count"
    - "response_time"
```

## 🔄 Dynamic Configuration

### Configuration Reload

Reload configuration without restarting:

```python
from src.ragme.utils.config_manager import config
config.reload()
```

### Runtime Configuration Access

```python
# Get specific configuration values
api_port = config.get('network.api.port', 8021)
llm_model = config.get('llm.default_model', 'gpt-4o-mini')

# Get complex configurations
db_config = config.get_database_config('weaviate-local')
agent_config = config.get_agent_config('ragme-agent')

# Check feature flags
if config.is_feature_enabled('document_summarization'):
    # Enable summarization feature
    pass
```

## 🎛️ Configuration API

### Frontend Configuration Endpoint

The backend provides a `/config` endpoint that serves configuration to the frontend:

```bash
curl http://localhost:8021/config
```

Response:
```json
{
  "application": {
    "name": "RAGme",
    "title": "🤖 RAGme.ai Assistant",
    "version": "0.1.0"
  },
  "frontend": {
    "settings": {
      "max_documents": 50,
      "auto_refresh": true,
      "refresh_interval_ms": 30000
    }
  },
  "mcp_servers": [...],
  "features": {...}
}
```

## 🔧 Advanced Configuration

### Custom Vector Database

Add support for a new vector database:

```yaml
vector_databases:
  databases:
    - name: "custom-db"
      type: "custom"
      connection_string: "${CUSTOM_DB_URL}"
      collection_name: "documents"
      custom_settings:
        batch_size: 100
        timeout: 30
```

### Custom Agents

Configure custom agents:

```yaml
agents:
  - name: "custom-agent"
    type: "custom"
    llm_model: "gpt-4"
    custom_prompt: "You are a specialized assistant for..."
    tools:
      - "web_search"
      - "document_analysis"
```

### Monitoring Integration

Configure external monitoring:

```yaml
monitoring:
  enabled: true
  services:
    prometheus:
      enabled: true
      port: 9090
      metrics_path: "/metrics"
    grafana:
      enabled: true
      port: 3000
      dashboard_url: "/dashboards"
```

## 📚 Configuration Reference

### Complete Configuration Schema

See `config.yaml.example` for the complete configuration schema with all available options and their descriptions.

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM operations | ✅ |
| `WEAVIATE_API_KEY` | Weaviate Cloud API key | ❌ |
| `WEAVIATE_URL` | Weaviate Cloud URL | ❌ |
| `WEAVIATE_LOCAL_URL` | Local Weaviate URL | ❌ |
| `MILVUS_URI` | Milvus database URI | ❌ |
| `MILVUS_TOKEN` | Milvus authentication token | ❌ |
| `VECTOR_DB_TYPE` | Default vector database type | ❌ |
| `RAGME_API_PORT` | API server port (default: 8021) | ❌ |
| `RAGME_MCP_PORT` | MCP server port (default: 8022) | ❌ |
| `RAGME_FRONTEND_PORT` | Frontend port (default: 3020) | ❌ |

### Configuration Validation

The configuration system validates:

- ✅ Required fields are present
- ✅ Data types are correct
- ✅ Environment variables are available
- ✅ Port numbers are valid
- ✅ File paths exist

## 🐛 Troubleshooting

### Common Issues

1. **Configuration file not found:**
   ```
   FileNotFoundError: Configuration file not found: /path/to/config.yaml
   ```
   **Solution:** Ensure `config.yaml` exists in the project root directory.

2. **Missing environment variables:**
   ```
   ValueError: Required environment variables not set: OPENAI_API_KEY
   ```
   **Solution:** Set the required environment variables in your `.env` file.

3. **Invalid YAML syntax:**
   ```
   ValueError: Error parsing configuration file: ...
   ```
   **Solution:** Check YAML syntax using a YAML validator.

### Debug Configuration

Enable debug logging to see configuration loading:

```yaml
logging:
  level: "DEBUG"
```

### Validate Configuration

Test your configuration:

```python
from src.ragme.utils.config_manager import config
print(f"Loaded configuration: {config}")
print(f"API Port: {config.get('network.api.port')}")
print(f"Default DB: {config.get('vector_databases.default')}")
```

### Security Issues

4. **API keys exposed in logs/endpoints:**
   ```
   WARNING: Sensitive data found in configuration endpoint
   ```
   **Solution:** This should never happen with the current system. If you see this:
   - Check that you're using `get_safe_frontend_config()` for API endpoints
   - Run security tests: `python -m pytest tests/test_config_security.py`
   - Report as a security issue if tests fail

5. **Configuration endpoint returning sensitive data:**
   ```bash
   # Test the configuration endpoint security
   curl http://localhost:8021/config | grep -i "api_key\|token\|password"
   # Should return no results
   ```
   
6. **Environment variables not being substituted:**
   ```
   ValueError: Required environment variables not set: OPENAI_API_KEY
   ```
   **Solution:** Ensure environment variables are set before starting RAGme.

### Configuration Validation

Use the built-in configuration validator to check your config.yaml:

```bash
# Validate current configuration
./tools/config-validator.sh

# Validate specific config file
./tools/config-validator.sh --config /path/to/config.yaml

# Show help
./tools/config-validator.sh --help
```

The validator checks for:
- ✅ **YAML syntax** correctness
- ✅ **Required sections** and fields
- ✅ **Data type validation** (ports as integers, features as booleans)
- ✅ **Security best practices** (no hardcoded secrets)
- ✅ **Environment variable** usage and documentation
- ✅ **Configuration loading** test with actual ConfigManager
- ✅ **Port conflicts** and performance warnings

**Example output:**
```
✅ Configuration file exists: config.yaml
✅ YAML syntax is valid
✅ Found section: application
✅ network.api.port: 8021
✅ Found 4 database configurations
✅ Default database 'weaviate-local' found in databases list
✅ All environment variables are documented
✅ Configuration loading test passed
✅ Security tests passed
✅ Validation PASSED - Configuration is perfect!
```

## 🚀 Migration Guide

### From Environment Variables

If you're migrating from environment variable configuration:

1. **Create config.yaml:**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **Move settings to config:**
   ```yaml
   # Old: VECTOR_DB_TYPE=weaviate-local
   # New:
   vector_databases:
     default: "weaviate-local"
   ```

3. **Keep sensitive data in environment:**
   ```yaml
   # Keep API keys in .env file
   vector_databases:
     databases:
       - name: "weaviate-cloud"
         api_key: "${WEAVIATE_API_KEY}"
   ```

### Backward Compatibility

The configuration system maintains backward compatibility with environment variables. If a configuration value is not found in `config.yaml`, it falls back to environment variables.

## 📖 Best Practices

1. **🔐 Security:**
   - Keep sensitive data (API keys, passwords) in environment variables
   - Use specific CORS origins in production
   - Enable rate limiting for production deployments

2. **⚡ Performance:**
   - Adjust chunk sizes based on your document types
   - Configure appropriate timeouts
   - Enable compression for production

3. **🔧 Maintenance:**
   - Use version control for configuration files
   - Document custom configurations
   - Test configuration changes in staging first

4. **🏢 Multi-Environment:**
   - Use different config files for dev/staging/prod
   - Override sensitive values with environment variables
   - Use feature flags for gradual rollouts

## 🤝 Contributing

When adding new configuration options:

1. Add the option to `config.yaml.example`
2. Update the configuration manager
3. Add documentation to this file
4. Include tests for the new configuration
5. Update the migration guide if needed

## 📞 Support

For configuration-related issues:

1. Check this documentation
2. Validate your YAML syntax
3. Review the logs for configuration errors
4. Check the troubleshooting section
5. Open an issue with your configuration (redact sensitive data)