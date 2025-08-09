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
    'application', 'network', 'vector_databases', 'agents',
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

# Validate vector_databases section
if 'vector_databases' in config:
    vdb = config['vector_databases']
    
    print("\nValidating vector_databases section...")
    if 'default' not in vdb:
        print_error("Missing vector_databases.default")
    elif not isinstance(vdb['default'], str):
        print_error("vector_databases.default must be a string")
    
    if 'databases' not in vdb:
        print_error("Missing vector_databases.databases")
    elif not isinstance(vdb['databases'], list):
        print_error("vector_databases.databases must be a list")
    elif len(vdb['databases']) == 0:
        print_error("vector_databases.databases cannot be empty")
    else:
        print_success(f"Found {len(vdb['databases'])} database configurations")
        
        # Check if default database exists in list
        default_db = vdb.get('default')
        db_names = [db.get('name') for db in vdb['databases'] if isinstance(db, dict)]
        
        if default_db and default_db not in db_names:
            print_error(f"Default database '{default_db}' not found in databases list")
        elif default_db:
            print_success(f"Default database '{default_db}' found in databases list")
        
        # Validate each database configuration
        for i, db in enumerate(vdb['databases']):
            if not isinstance(db, dict):
                print_error(f"Database {i} must be a dictionary")
                continue
                
            required_db_fields = ['name', 'type', 'collection_name']
            for field in required_db_fields:
                if field not in db:
                    print_error(f"Database {i} missing required field: {field}")
                elif not isinstance(db[field], str) or not db[field].strip():
                    print_error(f"Database {i} field '{field}' must be a non-empty string")

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

if 'vector_databases' in config:
    vdb = config['vector_databases']
    db_count = len(vdb.get('databases', []))
    default_db = vdb.get('default', 'None')
    print(f"  Vector Databases: {db_count} configured, default: {default_db}")

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
    export PROJECT_ROOT
    
    # Run all checks
    check_dependencies || exit 1
    check_file_exists || exit 1
    validate_yaml_syntax || exit 1
    validate_config_structure || exit 1
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
        echo "This script validates the RAGme configuration file for:"
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