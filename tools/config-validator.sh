#!/bin/bash

# RAGme Configuration Validator
# Validates config.yaml for correctness and completeness

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
ERRORS=0
WARNINGS=0
CHECKS=0

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config.yaml"
AGENTS_FILE="$PROJECT_ROOT/agents.yaml"

# Load environment variables from .env file
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Function to print colored output
print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}" >&2
    ((ERRORS++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
    ((WARNINGS++))
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to increment check counter
check_done() {
    ((CHECKS++))
}

# Check if Python and required modules are available
check_dependencies() {
    print_header "Checking Dependencies"
    
    if ! command_exists python; then
        print_error "Python is not installed or not in PATH"
        return 1
    fi
    
    if ! python -c "import yaml" 2>/dev/null; then
        print_error "PyYAML is not installed. Run: pip install PyYAML"
        return 1
    fi
    
    print_success "All dependencies available"
    check_done
    return 0
}

# Check if config file exists
check_file_exists() {
    print_header "Checking Configuration File"
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        return 1
    fi
    
    print_success "Configuration file exists: $CONFIG_FILE"
    check_done
    return 0
}

# Validate YAML syntax
validate_yaml_syntax() {
    print_header "Validating YAML Syntax"
    
    if ! python -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null; then
        print_error "Invalid YAML syntax in configuration file"
        python -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>&1 | head -5
        return 1
    fi
    
    print_success "YAML syntax is valid"
    check_done
    return 0
}

# Validate configuration structure and content
validate_config_structure() {
    print_header "Validating Configuration Structure"
    
    python << 'EOF'
import yaml
import sys
import os

CONFIG_FILE = os.environ.get('CONFIG_FILE')
errors = 0
warnings = 0

def print_error(msg):
    global errors
    print(f"\033[0;31m❌ ERROR: {msg}\033[0m", file=sys.stderr)
    errors += 1

def print_warning(msg):
    global warnings
    print(f"\033[1;33m⚠️  WARNING: {msg}\033[0m")
    warnings += 1

def print_success(msg):
    print(f"\033[0;32m✅ {msg}\033[0m")

try:
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
except Exception as e:
    print_error(f"Failed to load config: {e}")
    sys.exit(1)

# Required sections
required_sections = [
    'application', 'network', 'databases', 'agents',
    'mcp_servers', 'frontend', 'features', 'environment'
]

print("Checking required sections...")
for section in required_sections:
    if section not in config:
        print_error(f"Missing required section: {section}")
    else:
        print_success(f"Found section: {section}")

# Validate application section
if 'application' in config:
    app = config['application']
    required_app_fields = ['name', 'version', 'title', 'description']
    
    print("\nValidating application section...")
    for field in required_app_fields:
        if field not in app:
            print_error(f"Missing application.{field}")
        elif not isinstance(app[field], str) or not app[field].strip():
            print_error(f"application.{field} must be a non-empty string")
        else:
            print_success(f"application.{field}: {app[field]}")

# Validate network section
if 'network' in config:
    network = config['network']
    
    print("\nValidating network section...")
    for service in ['api', 'mcp', 'frontend']:
        if service not in network:
            print_error(f"Missing network.{service} configuration")
            continue
            
        service_config = network[service]
        if 'port' not in service_config:
            print_error(f"Missing network.{service}.port")
        elif not isinstance(service_config['port'], int):
            print_error(f"network.{service}.port must be an integer")
        elif not (1 <= service_config['port'] <= 65535):
            print_error(f"network.{service}.port must be between 1 and 65535")
        else:
            print_success(f"network.{service}.port: {service_config['port']}")

# Validate databases section
if 'databases' in config:
    databases = config['databases']
    
    print("\nValidating databases section...")
    if 'default' not in databases:
        print_error("Missing databases.default")
    elif not isinstance(databases['default'], str):
        print_error("databases.default must be a string")
    else:
        print_success(f"Default database: {databases['default']}")
    
    if 'vector_databases' not in databases:
        print_error("Missing databases.vector_databases")
    elif not isinstance(databases['vector_databases'], list):
        print_error("databases.vector_databases must be a list")
    elif len(databases['vector_databases']) == 0:
        print_error("databases.vector_databases cannot be empty")
    else:
        print_success(f"Found {len(databases['vector_databases'])} database configurations")
        
        # Check if default database exists in list
        default_db = databases.get('default')
        db_names = [db.get('name') for db in databases['vector_databases'] if isinstance(db, dict)]
        
        if default_db:
            # Handle environment variable references
            if default_db.startswith('${') and default_db.endswith('}'):
                # Extract the default value from env var syntax like ${VAR:-default}
                import re
                match = re.search(r':-(.+?)}', default_db)
                if match:
                    resolved_default = match.group(1)
                    if resolved_default in db_names:
                        print_success(f"Default database resolves to '{resolved_default}' and exists in databases list")
                    else:
                        print_error(f"Default database resolves to '{resolved_default}' but not found in databases list")
                else:
                    print_warning(f"Default database uses environment variable '{default_db}' - cannot validate without resolution")
            elif default_db in db_names:
                print_success(f"Default database '{default_db}' found in databases list")
            else:
                print_error(f"Default database '{default_db}' not found in databases list")
        
        # Validate each database configuration
        for i, db in enumerate(databases['vector_databases']):
            if not isinstance(db, dict):
                print_error(f"Database {i} must be a dictionary")
                continue
            
            # Base required fields
            required_db_fields = ['name', 'type']
            for field in required_db_fields:
                if field not in db:
                    print_error(f"Database {i} missing required field: {field}")
                elif not isinstance(db[field], str) or not db[field].strip():
                    print_error(f"Database {i} field '{field}' must be a non-empty string")

            # Collections validation (new schema)
            if 'collections' in db:
                collections = db.get('collections')
                if not isinstance(collections, list):
                    print_error(f"Database {i} 'collections' must be a list")
                elif len(collections) == 0:
                    print_error(f"Database {i} 'collections' cannot be empty")
                else:
                    text_found = False
                    for j, col in enumerate(collections):
                        if not isinstance(col, dict):
                            print_error(f"Database {i} collection {j} must be a dictionary")
                            continue
                        # Validate collection name and type
                        name = col.get('name')
                        ctype = col.get('type')
                        if not isinstance(name, str) or not name.strip():
                            print_error(f"Database {i} collection {j} missing or invalid 'name'")
                        if not isinstance(ctype, str) or not ctype.strip():
                            print_error(f"Database {i} collection {j} missing or invalid 'type'")
                        else:
                            if ctype not in ('text', 'image'):
                                print_warning(f"Database {i} collection {j} has unrecognized type '{ctype}'. Expected 'text' or 'image'")
                            if ctype == 'text':
                                text_found = True
                    if not text_found:
                        print_warning(f"Database {i} has no 'text' collection; defaulting may apply (RagMeDocs)")
            # Legacy single collection_name support
            elif 'collection_name' in db:
                cname = db.get('collection_name')
                if not isinstance(cname, str) or not cname.strip():
                    print_error(f"Database {i} field 'collection_name' must be a non-empty string")
                else:
                    print_warning(f"Database {i} uses legacy 'collection_name'. Consider migrating to 'collections' array with types")
            else:
                print_error(f"Database {i} must define either 'collections' (preferred) or legacy 'collection_name'")

# Validate agents section
if 'agents' in config:
    agents = config['agents']
    
    print("\nValidating agents section...")
    if not isinstance(agents, list):
        print_error("agents must be a list")
    elif len(agents) == 0:
        print_warning("No agents configured")
    else:
        print_success(f"Found {len(agents)} agent configurations")
        
        for i, agent in enumerate(agents):
            if not isinstance(agent, dict):
                print_error(f"Agent {i} must be a dictionary")
                continue
                
            required_agent_fields = ['name', 'type', 'llm_model']
            for field in required_agent_fields:
                if field not in agent:
                    print_error(f"Agent {i} missing required field: {field}")
                elif not isinstance(agent[field], str) or not agent[field].strip():
                    print_error(f"Agent {i} field '{field}' must be a non-empty string")

# Validate mcp_servers section
if 'mcp_servers' in config:
    mcp_servers = config['mcp_servers']
    
    print("\nValidating mcp_servers section...")
    if not isinstance(mcp_servers, list):
        print_error("mcp_servers must be a list")
    elif len(mcp_servers) == 0:
        print_warning("No MCP servers configured")
    else:
        print_success(f"Found {len(mcp_servers)} MCP server configurations")
        
        for i, server in enumerate(mcp_servers):
            if not isinstance(server, dict):
                print_error(f"MCP server {i} must be a dictionary")
                continue
                
            if 'name' not in server:
                print_error(f"MCP server {i} missing required field: name")
            elif not isinstance(server['name'], str) or not server['name'].strip():
                print_error(f"MCP server {i} name must be a non-empty string")

# Validate features section
if 'features' in config:
    features = config['features']
    
    print("\nValidating features section...")
    if not isinstance(features, dict):
        print_error("features must be a dictionary")
    else:
        print_success(f"Found {len(features)} feature flags")
        
        for feature, value in features.items():
            if not isinstance(value, bool):
                print_error(f"Feature '{feature}' must be a boolean value")

# Validate environment section
if 'environment' in config:
    env = config['environment']
    
    print("\nValidating environment section...")
    if not isinstance(env, dict):
        print_error("environment must be a dictionary")
    else:
        if 'required' in env:
            if not isinstance(env['required'], list):
                print_error("environment.required must be a list")
            else:
                print_success(f"Found {len(env['required'])} required environment variables")
                
                # Check for essential environment variables
                essential_vars = ['OPENAI_API_KEY']
                for var in essential_vars:
                    if var not in env['required']:
                        print_warning(f"Essential environment variable '{var}' not in required list")

# Security checks
print("\nPerforming security checks...")
def check_for_secrets(obj, path=""):
    """Recursively check for potential secrets in configuration."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check for suspicious key names
            if any(secret_key in key.lower() for secret_key in ['password', 'secret', 'private_key', 'client_secret']):
                if isinstance(value, str) and value and not value.startswith('${'):
                    print_warning(f"Potential hardcoded secret at {current_path}")
            
            # Check for hardcoded API keys
            if 'api_key' in key.lower() and isinstance(value, str):
                if value and not value.startswith('${') and len(value) > 10:
                    print_warning(f"Potential hardcoded API key at {current_path}")
            
            check_for_secrets(value, current_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            check_for_secrets(item, f"{path}[{i}]")

check_for_secrets(config)

# Performance and best practice checks
print("\nPerforming best practice checks...")

# Check port conflicts
ports = []
if 'network' in config:
    for service, service_config in config['network'].items():
        if isinstance(service_config, dict) and 'port' in service_config:
            port = service_config['port']
            if port in ports:
                print_error(f"Port conflict: {port} is used by multiple services")
            else:
                ports.append(port)

# Check for reasonable limits
if 'frontend' in config and 'settings' in config['frontend']:
    settings = config['frontend']['settings']
    if 'max_documents' in settings:
        max_docs = settings['max_documents']
        if isinstance(max_docs, int):
            if max_docs > 1000:
                print_warning(f"max_documents ({max_docs}) is very high, may impact performance")
            elif max_docs < 1:
                print_error("max_documents must be at least 1")

print(f"\n\033[0;34mValidation Summary:\033[0m")
print(f"Errors: {errors}")
print(f"Warnings: {warnings}")

if errors > 0:
    sys.exit(1)
else:
    print("\033[0;32m✅ Configuration structure is valid\033[0m")

EOF

    if [[ $? -ne 0 ]]; then
        ((ERRORS++))
        return 1
    fi
    
    check_done
}

# Check environment variable usage
check_environment_variables() {
    print_header "Checking Environment Variables"
    
    python << 'EOF'
import yaml
import os
import re

CONFIG_FILE = os.environ.get('CONFIG_FILE')

try:
    with open(CONFIG_FILE, 'r') as f:
        config_content = f.read()
        config = yaml.safe_load(config_content)
except Exception as e:
    print(f"\033[0;31m❌ ERROR: Failed to load config: {e}\033[0m", file=sys.stderr)
    exit(1)

# Find all environment variable references
env_var_pattern = r'\$\{([^}]+)\}'
env_vars_used = set(re.findall(env_var_pattern, config_content))

print(f"Found {len(env_vars_used)} environment variable references:")
for var in sorted(env_vars_used):
    print(f"  - ${{{var}}}")

# Check against required/optional lists
required_vars = config.get('environment', {}).get('required', [])
optional_vars = config.get('environment', {}).get('optional', [])

print(f"\nRequired environment variables: {len(required_vars)}")
for var in required_vars:
    print(f"  - {var}")

print(f"\nOptional environment variables: {len(optional_vars)}")
for var in optional_vars:
    print(f"  - {var}")

# Check for undocumented variables
all_documented = set(required_vars + optional_vars)
undocumented = env_vars_used - all_documented

if undocumented:
    print(f"\n\033[1;33m⚠️  WARNING: Undocumented environment variables:\033[0m")
    for var in sorted(undocumented):
        print(f"  - {var}")
else:
    print(f"\n\033[0;32m✅ All environment variables are documented\033[0m")

# Check for unused documented variables
unused_documented = all_documented - env_vars_used
if unused_documented:
    print(f"\n\033[1;33m⚠️  WARNING: Documented but unused environment variables:\033[0m")
    for var in sorted(unused_documented):
        print(f"  - {var}")

EOF
    
    check_done
}

# Check if agents file exists
check_agents_file_exists() {
    print_header "Checking Agents Configuration File"
    
    if [[ ! -f "$AGENTS_FILE" ]]; then
        print_info "Agents file not found: $AGENTS_FILE (using inline configuration)"
        return 0
    fi
    
    print_success "Agents configuration file exists: $AGENTS_FILE"
    check_done
    return 0
}

# Validate agents.yaml syntax
validate_agents_yaml_syntax() {
    if [[ ! -f "$AGENTS_FILE" ]]; then
        return 0  # Skip if file doesn't exist
    fi
    
    print_header "Validating Agents YAML Syntax"
    
    if ! python -c "import yaml; yaml.safe_load(open('$AGENTS_FILE'))" 2>/dev/null; then
        print_error "Invalid YAML syntax in agents configuration file"
        python -c "import yaml; yaml.safe_load(open('$AGENTS_FILE'))" 2>&1 | head -5
        return 1
    fi
    
    print_success "Agents YAML syntax is valid"
    check_done
    return 0
}

# Validate agents configuration structure and content
validate_agents_structure() {
    if [[ ! -f "$AGENTS_FILE" ]]; then
        return 0  # Skip if file doesn't exist
    fi
    
    print_header "Validating Agents Configuration Structure"
    
    python << 'EOF'
import yaml
import sys
import os

AGENTS_FILE = os.environ.get('AGENTS_FILE')
errors = 0
warnings = 0

def print_error(msg):
    global errors
    print(f"\033[0;31m❌ ERROR: {msg}\033[0m", file=sys.stderr)
    errors += 1

def print_warning(msg):
    global warnings
    print(f"\033[1;33m⚠️  WARNING: {msg}\033[0m")
    warnings += 1

def print_success(msg):
    print(f"\033[0;32m✅ {msg}\033[0m")

try:
    with open(AGENTS_FILE, 'r') as f:
        agents_config = yaml.safe_load(f)
except Exception as e:
    print_error(f"Failed to load agents config: {e}")
    sys.exit(1)

# Check root structure
if not isinstance(agents_config, dict):
    print_error("Agents configuration must be a dictionary")
    sys.exit(1)

if 'agents' not in agents_config:
    print_error("Missing required 'agents' section")
    sys.exit(1)

agents = agents_config['agents']

print("Validating agents configuration...")
if not isinstance(agents, list):
    print_error("'agents' must be a list")
    sys.exit(1)
elif len(agents) == 0:
    print_warning("No agents configured in agents.yaml")
else:
    print_success(f"Found {len(agents)} agent configurations")

# Validate each agent
valid_roles = ['dispatch', 'functional', 'query', 'react', 'local']
valid_types = ['openai', 'llamaindex', 'custom']

for i, agent in enumerate(agents):
    if not isinstance(agent, dict):
        print_error(f"Agent {i} must be a dictionary")
        continue
    
    agent_name = agent.get('name', f'Agent {i}')
    print(f"\nValidating agent: {agent_name}")
    
    # Required fields
    required_fields = ['name', 'role', 'type', 'llm_model']
    for field in required_fields:
        if field not in agent:
            print_error(f"Agent '{agent_name}' missing required field: {field}")
        elif not isinstance(agent[field], str) or not agent[field].strip():
            print_error(f"Agent '{agent_name}' field '{field}' must be a non-empty string")
        else:
            print_success(f"  {field}: {agent[field]}")
    
    # Validate role
    role = agent.get('role')
    if role and role not in valid_roles:
        print_warning(f"Agent '{agent_name}' has unrecognized role '{role}'. Valid roles: {', '.join(valid_roles)}")
    
    # Validate type
    agent_type = agent.get('type')
    if agent_type and agent_type not in valid_types:
        print_warning(f"Agent '{agent_name}' has unrecognized type '{agent_type}'. Valid types: {', '.join(valid_types)}")
    
    # Validate class_name for custom agents
    if agent_type == 'custom' and 'class_name' not in agent:
        print_error(f"Agent '{agent_name}' with type 'custom' must have 'class_name' field")
    elif 'class_name' in agent:
        class_name = agent['class_name']
        if not isinstance(class_name, str) or not class_name.strip():
            print_error(f"Agent '{agent_name}' class_name must be a non-empty string")
        elif '.' not in class_name:
            print_warning(f"Agent '{agent_name}' class_name should be fully qualified (e.g., 'module.ClassName')")
        else:
            print_success(f"  class_name: {class_name}")
    
    # Validate code configuration
    if 'code' in agent:
        code_config = agent['code']
        if not isinstance(code_config, dict):
            print_error(f"Agent '{agent_name}' code must be a dictionary")
        else:
            has_uri = 'uri' in code_config
            has_inline = 'inline' in code_config
            
            if not has_uri and not has_inline:
                print_error(f"Agent '{agent_name}' code must have either 'uri' or 'inline' field")
            elif has_uri and has_inline:
                print_warning(f"Agent '{agent_name}' has both 'uri' and 'inline' code. 'uri' will take precedence")
            
            if has_uri:
                uri = code_config['uri']
                if not isinstance(uri, str) or not uri.strip():
                    print_error(f"Agent '{agent_name}' code.uri must be a non-empty string")
                elif uri.startswith('https://github.com/'):
                    print_success(f"  code.uri: {uri} (GitHub repository)")
                elif uri.startswith('./') or uri.startswith('/'):
                    print_success(f"  code.uri: {uri} (local file)")
                else:
                    print_warning(f"Agent '{agent_name}' code.uri format not recognized: {uri}")
            
            if has_inline and not has_uri:
                inline_code = code_config['inline']
                if not isinstance(inline_code, str) or not inline_code.strip():
                    print_error(f"Agent '{agent_name}' code.inline must be a non-empty string")
                else:
                    print_success(f"  code.inline: {len(inline_code)} characters")
    
    # Validate environment variables
    if 'env' in agent:
        env_config = agent['env']
        if not isinstance(env_config, dict):
            print_error(f"Agent '{agent_name}' env must be a dictionary")
        else:
            print_success(f"  env: {len(env_config)} environment variables")
            
            # Check for common environment variable patterns
            for env_key, env_value in env_config.items():
                if isinstance(env_value, str) and env_value.startswith('${') and env_value.endswith('}'):
                    print_success(f"    {env_key}: {env_value} (environment variable reference)")
                else:
                    print_success(f"    {env_key}: {type(env_value).__name__}")

# Check for duplicate agent names
agent_names = [agent.get('name') for agent in agents if isinstance(agent, dict)]
duplicate_names = set([name for name in agent_names if agent_names.count(name) > 1])
if duplicate_names:
    print_error(f"Duplicate agent names found: {', '.join(duplicate_names)}")

# Check for agents directory configuration
if 'agents_directory' in agents_config:
    agents_dir = agents_config['agents_directory']
    if not isinstance(agents_dir, str) or not agents_dir.strip():
        print_error("agents_directory must be a non-empty string")
    else:
        print_success(f"Agents directory configured: {agents_dir}")

print(f"\n\033[0;34mAgents Validation Summary:\033[0m")
print(f"Errors: {errors}")
print(f"Warnings: {warnings}")

if errors > 0:
    sys.exit(1)
else:
    print("\033[0;32m✅ Agents configuration structure is valid\033[0m")

EOF

    if [[ $? -ne 0 ]]; then
        ((ERRORS++))
        return 1
    fi
    
    check_done
}

# Test configuration loading with Python
test_config_loading() {
    print_header "Testing Configuration Loading"
    
    python << 'EOF'
import sys
import os
sys.path.insert(0, os.path.join(os.environ.get('PROJECT_ROOT'), 'src'))

try:
    from ragme.utils.config_manager import ConfigManager
    
    print("Testing ConfigManager instantiation...")
    config = ConfigManager()
    
    print("✅ ConfigManager created successfully")
    
    # Test basic methods
    print("Testing basic configuration methods...")
    
    # Test dot notation access
    app_name = config.get('application.name', 'Unknown')
    print(f"✅ Application name: {app_name}")
    
    # Test database config
    db_config = config.get_database_config()
    if db_config:
        print(f"✅ Default database: {db_config.get('name', 'Unknown')}")
    else:
        print("⚠️  No default database configuration found")
    
    # Test safe config
    safe_config = config.get_safe_frontend_config()
    print(f"✅ Safe frontend config has {len(safe_config)} sections")
    
    # Test feature flags
    features = config.get('features', {})
    enabled_features = [k for k, v in features.items() if v]
    print(f"✅ {len(enabled_features)} features enabled")
    
    # Test agents configuration
    if config.has_agents_file():
        agents = config.get_all_agents()
        print(f"✅ {len(agents)} agents loaded from agents.yaml")
        
        # Test agent config access
        for agent in agents[:2]:  # Test first 2 agents
            agent_name = agent.get('name', 'unknown')
            agent_config = config.get_agent_config(agent_name)
            if agent_config:
                print(f"✅ Agent '{agent_name}' config loaded successfully")
            else:
                print(f"⚠️  Agent '{agent_name}' config not found")
    else:
        print("ℹ️  Using inline agent configuration from config.yaml")
    
    print("\n\033[0;32m✅ Configuration loading test passed\033[0m")
    
except Exception as e:
    print(f"\033[0;31m❌ ERROR: Configuration loading failed: {e}\033[0m", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

EOF

    if [[ $? -ne 0 ]]; then
        ((ERRORS++))
        return 1
    fi
    
    check_done
}

# Run security validation
run_security_validation() {
    print_header "Running Security Validation"
    
    if [[ -f "$PROJECT_ROOT/tests/test_config_security.py" ]]; then
        cd "$PROJECT_ROOT"
        if python -m pytest tests/test_config_security.py -v --tb=short >/dev/null 2>&1; then
            print_success "Security tests passed"
        else
            print_error "Security tests failed"
            python -m pytest tests/test_config_security.py -v --tb=short
            return 1
        fi
    else
        print_warning "Security tests not found, skipping"
    fi
    
    check_done
}

# Generate configuration report
generate_report() {
    print_header "Configuration Report"
    
    python << 'EOF'
import sys
import os
sys.path.insert(0, os.path.join(os.environ.get('PROJECT_ROOT'), 'src'))

try:
    from ragme.utils.config_manager import ConfigManager
    config_manager = ConfigManager()
    config = config_manager.config
except Exception as e:
    print(f"Failed to load config via ConfigManager: {e}")
    exit(1)

print("📊 Configuration Summary:")
app_name = config.get('application', {}).get('name', 'Unknown')
app_version = config.get('application', {}).get('version', 'Unknown')
print(f"  Application: {app_name} v{app_version}")

if 'databases' in config:
    databases = config['databases']
    db_count = len(databases.get('vector_databases', []))
    default_db = databases.get('default', 'None')
    print(f"  Vector Databases: {db_count} configured, default: {default_db}")

try:
    # Try to get agents from new system first
    agents = config_manager.get_all_agents()
    agent_count = len(agents)
    has_agents_file = config_manager.has_agents_file()
    
    if has_agents_file:
        print(f"  Agents: {agent_count} configured (from agents.yaml)")
        
        # Show agent types breakdown
        agent_types = {}
        agent_roles = {}
        for agent in agents:
            agent_type = agent.get('type', 'unknown')
            agent_role = agent.get('role', 'unknown')
            agent_types[agent_type] = agent_types.get(agent_type, 0) + 1
            agent_roles[agent_role] = agent_roles.get(agent_role, 0) + 1
        
        types_str = ', '.join([f"{k}:{v}" for k, v in agent_types.items()])
        roles_str = ', '.join([f"{k}:{v}" for k, v in agent_roles.items()])
        print(f"    Types: {types_str}")
        print(f"    Roles: {roles_str}")
        
    else:
        # Fallback to inline agents
        if 'agents' in config:
            agent_count = len(config['agents'])
            print(f"  Agents: {agent_count} configured (inline in config.yaml)")
        else:
            print("  Agents: None configured")
            
except Exception as e:
    # Fallback to old method
    if 'agents' in config:
        agent_count = len(config['agents'])
        print(f"  Agents: {agent_count} configured")

if 'mcp_servers' in config:
    mcp_count = len(config['mcp_servers'])
    enabled_mcp = sum(1 for server in config['mcp_servers'] if server.get('enabled', False))
    print(f"  MCP Servers: {mcp_count} configured, {enabled_mcp} enabled")

if 'features' in config:
    features = config['features']
    enabled_features = sum(1 for v in features.values() if v)
    total_features = len(features)
    print(f"  Features: {enabled_features}/{total_features} enabled")

if 'network' in config:
    network = config['network']
    ports = []
    for service, service_config in network.items():
        if isinstance(service_config, dict) and 'port' in service_config:
            ports.append(f"{service}:{service_config['port']}")
    print(f"  Network Ports: {', '.join(ports)}")

EOF
    
    check_done
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════╗"
    echo "║           RAGme Config Validator         ║"
    echo "║     Validating configuration file        ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
    
    export CONFIG_FILE
    export AGENTS_FILE
    export PROJECT_ROOT
    
    # Run all checks
    check_dependencies || exit 1
    check_file_exists || exit 1
    validate_yaml_syntax || exit 1
    validate_config_structure || exit 1
    
    # Agents configuration checks
    check_agents_file_exists
    validate_agents_yaml_syntax || exit 1
    validate_agents_structure || exit 1
    
    check_environment_variables
    test_config_loading || exit 1
    run_security_validation
    generate_report
    
    # Final summary
    echo -e "\n${BLUE}=== Validation Summary ===${NC}"
    echo -e "Total checks performed: ${CHECKS}"
    
    if [[ $ERRORS -gt 0 ]]; then
        echo -e "${RED}❌ Validation FAILED with ${ERRORS} error(s)${NC}"
        if [[ $WARNINGS -gt 0 ]]; then
            echo -e "${YELLOW}⚠️  ${WARNINGS} warning(s) found${NC}"
        fi
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  Validation PASSED with ${WARNINGS} warning(s)${NC}"
        echo -e "${GREEN}✅ Configuration is valid but could be improved${NC}"
    else
        echo -e "${GREEN}✅ Validation PASSED - Configuration is perfect!${NC}"
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "RAGme Configuration Validator"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --config FILE  Specify config file path (default: config.yaml)"
        echo "  --quiet, -q    Suppress non-error output"
        echo ""
        echo "This script validates the RAGme configuration files for:"
        echo "  - config.yaml: Main configuration file"
        echo "  - agents.yaml: Agent definitions (if present)"
        echo "  - YAML syntax correctness"
        echo "  - Required sections and fields"
        echo "  - Data type validation"
        echo "  - Security best practices"
        echo "  - Environment variable usage"
        echo "  - Configuration loading test"
        exit 0
        ;;
    --config)
        if [[ -n "${2:-}" ]]; then
            CONFIG_FILE="$2"
        else
            echo "Error: --config requires a file path" >&2
            exit 1
        fi
        ;;
    --quiet|-q)
        exec >/dev/null
        ;;
esac

# Run main function
main "$@"