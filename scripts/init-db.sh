#!/bin/bash
# Database Initialization Script - PRD-002 DB-001
# CLI interface for initializing the AI Documentation Cache database

set -e

# Default values
DB_PATH="${DB_PATH:-/app/data/docaiche.db}"
FORCE="${FORCE:-false}"
INFO="${INFO:-false}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Initialize the AI Documentation Cache SQLite database with all tables and indexes.

OPTIONS:
    -p, --db-path PATH      Database file path (default: /app/data/docaiche.db)
    -f, --force            Force recreate database (removes existing file)
    -i, --info             Show database information instead of initializing
    -h, --help             Show this help message

ENVIRONMENT VARIABLES:
    DB_PATH                Override default database path
    FORCE                  Set to 'true' to force recreation
    INFO                   Set to 'true' to show info

EXAMPLES:
    # Initialize database with defaults
    $0

    # Force recreate database
    $0 --force

    # Initialize with custom path
    $0 --db-path /custom/path/db.sqlite

    # Show database information
    $0 --info

    # Using environment variables
    DB_PATH=/custom/db.sqlite FORCE=true $0

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--db-path)
            DB_PATH="$2"
            shift 2
            ;;
        -f|--force)
            FORCE="true"
            shift
            ;;
        -i|--info)
            INFO="true"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "src/database/init_db.py" ]]; then
    print_error "Database initialization script not found. Are you in the project root?"
    exit 1
fi

print_info "AI Documentation Cache Database Initialization"
print_info "Database path: $DB_PATH"

# Set Python path to include src directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src:$(pwd)"

# Build command arguments
PYTHON_ARGS=()
if [[ "$DB_PATH" != "/app/data/docaiche.db" ]]; then
    PYTHON_ARGS+=("--db-path" "$DB_PATH")
fi

if [[ "$FORCE" == "true" ]]; then
    PYTHON_ARGS+=("--force")
    print_warning "Force recreation enabled - existing database will be removed"
fi

if [[ "$INFO" == "true" ]]; then
    PYTHON_ARGS+=("--info")
fi

# Check if database directory is writable
DB_DIR=$(dirname "$DB_PATH")
if [[ ! -w "$DB_DIR" ]] && [[ ! -d "$DB_DIR" ]]; then
    print_warning "Database directory does not exist or is not writable: $DB_DIR"
    print_info "Attempting to create directory..."
    mkdir -p "$DB_DIR" || {
        print_error "Failed to create database directory: $DB_DIR"
        exit 1
    }
fi

# Execute the database initialization
print_info "Executing database initialization..."

if python3 -m src.database.init_db "${PYTHON_ARGS[@]}"; then
    if [[ "$INFO" == "true" ]]; then
        print_success "Database information retrieved successfully"
    else
        print_success "Database initialization completed successfully!"
        print_info "Database created at: $DB_PATH"
        
        # Show basic database info
        if [[ -f "$DB_PATH" ]]; then
            DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
            print_info "Database file size: $DB_SIZE"
        fi
    fi
else
    print_error "Database initialization failed"
    exit 1
fi

print_info "Operation completed"