# MicroK8s Cluster Orchestrator - Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install dev-install test lint format clean build run docker-build docker-run docker-stop setup quick-setup system-setup health-check migrate validate-models update

# Default target
help:
	@echo "MicroK8s Cluster Orchestrator - Available Commands"
	@echo "=================================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install          Install dependencies in virtual environment"
	@echo "  dev-install      Install development dependencies"
	@echo "  setup            Run full system setup (interactive)"
	@echo "  quick-setup      Run quick setup for experienced users"
	@echo "  system-setup     Run comprehensive system setup with service"
	@echo ""
	@echo "Development Commands:"
	@echo "  run              Start the web interface"
	@echo "  test             Run tests"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black"
	@echo "  clean            Clean up temporary files"
	@echo ""
	@echo "Database Commands:"
	@echo "  migrate          Run database migrations"
	@echo "  validate-models  Validate model-database consistency"
	@echo "  health-check     Run comprehensive system health check"
	@echo ""
	@echo "Playbook Commands:"
	@echo "  playbook-templates  List available playbook templates"
	@echo "  playbook-init      Initialize system templates"
	@echo "  playbook-executions List recent executions"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run with Docker Compose"
	@echo "  docker-stop      Stop Docker containers"
	@echo ""
	@echo "System Commands:"
	@echo "  init             Initialize the application"
	@echo "  update           Pull latest code and run migrations"
	@echo "  backup           Create database backup"
	@echo "  restore          Restore from backup"

# Setup commands
install:
	@echo "📦 Installing dependencies..."
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	ansible-galaxy install -r ansible/requirements.yml
	@echo "✅ Installation complete!"

dev-install: install
	@echo "🔧 Installing development dependencies..."
	.venv/bin/pip install pytest pytest-cov black flake8 mypy
	@echo "✅ Development setup complete!"

setup:
	@echo "🚀 Running interactive setup..."
	./scripts/setup_system.sh

quick-setup:
	@echo "⚡ Running quick setup..."
	./scripts/quick_setup.sh

system-setup:
	@echo "🏗️  Running comprehensive system setup..."
	./scripts/setup_system.sh

# Development commands
run:
	@echo "🌐 Starting web interface..."
	.venv/bin/python cli.py web

test:
	@echo "🧪 Running tests..."
	.venv/bin/python -m pytest tests/ -v

lint:
	@echo "🔍 Running linting checks..."
	.venv/bin/flake8 app/ --max-line-length=100 --ignore=E203,W503
	.venv/bin/mypy app/ --ignore-missing-imports

format:
	@echo "🎨 Formatting code..."
	.venv/bin/black app/ --line-length=100

clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	@echo "✅ Cleanup complete!"

# Database commands
migrate:
	@echo "🔄 Running database migrations..."
	.venv/bin/python cli.py migrate

validate-models:
	@echo "🔍 Validating model-database consistency..."
	.venv/bin/python app/utils/migration_manager.py --validate-models

health-check:
	@echo "🏥 Running system health check..."
	.venv/bin/python app/utils/migration_manager.py --health

# Docker commands
docker-build:
	@echo "🐳 Building Docker image..."
	docker-compose build

docker-run:
	@echo "🐳 Starting with Docker Compose..."
	docker-compose up -d
	@echo "✅ Service started! Access at http://localhost:5000"

docker-stop:
	@echo "🛑 Stopping Docker containers..."
	docker-compose down

docker-logs:
	@echo "📋 Showing Docker logs..."
	docker-compose logs -f

# System commands
init:
	@echo "🏗️  Initializing application..."
	.venv/bin/python cli.py init

update:
	@echo "🔄 Running safe codebase update..."
	./scripts/safe_update.sh

backup:
	@echo "💾 Creating database backup..."
	.venv/bin/python scripts/backup_db.py

restore:
	@echo "📥 Restoring from backup..."
	@read -p "Enter backup file path: " backup_file; \
	.venv/bin/python scripts/restore_db.py "$$backup_file"

# Validation and sync
validate-and-sync:
	@echo "🔧 Validating and synchronizing models..."
	.venv/bin/python scripts/validate_and_sync_models.py

# Development server with auto-reload
dev:
	@echo "🔄 Starting development server with auto-reload..."
	.venv/bin/python cli.py web --debug

# Production server
prod:
	@echo "🚀 Starting production server..."
	.venv/bin/python cli.py web --host 0.0.0.0 --port 5000

# Show system status
status:
	@echo "📊 System Status:"
	@echo "=================="
	@.venv/bin/python -c "from app.utils.migration_manager import MigrationManager; mm = MigrationManager(); print(mm.create_health_report())"

# Install system dependencies (Ubuntu/Debian)
install-deps:
	@echo "📦 Installing system dependencies..."
	sudo apt update
	sudo apt install -y python3 python3-pip python3-venv ansible git curl wget
	@echo "✅ System dependencies installed!"

# Create necessary directories
create-dirs:
	@echo "📁 Creating necessary directories..."
	mkdir -p logs config ssh_keys backups migrations
	@echo "✅ Directories created!"

# Full installation from scratch
install-full: install-deps create-dirs install
	@echo "🎉 Full installation complete!"
	@echo "Next steps:"
	@echo "1. Run 'make init' to initialize the database"
	@echo "2. Run 'make run' to start the web interface"
	@echo "3. Access http://localhost:5000 in your browser"

# Playbook commands
playbook-templates:
	@echo "📋 Listing playbook templates..."
	.venv/bin/python cli.py playbook list-templates

playbook-init:
	@echo "🔧 Initializing system templates..."
	.venv/bin/python cli.py playbook init-templates

playbook-executions:
	@echo "📊 Listing recent executions..."
	.venv/bin/python cli.py playbook list-executions

# Show help for specific command
help-%:
	@echo "Help for command: $*"
	@grep -A 5 "^$*:" Makefile || echo "No help available for $*"
