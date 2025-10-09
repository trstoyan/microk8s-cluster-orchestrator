# MicroK8s Cluster Orchestrator - Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install dev-install test lint format clean build run docker-build docker-run docker-stop setup quick-setup system-setup health-check migrate validate-models update update-dry prod-start prod-stop prod-restart prod-status prod-logs prod-cleanup logo sync-test sync-api sync-connect sync-compare sync-interactive

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
	@echo "Production Server Commands:"
	@echo "  prod-start       Start production server in background"
	@echo "  prod-stop        Stop production server"
	@echo "  prod-restart     Restart production server"
	@echo "  prod-status      Check production server status"
	@echo "  prod-logs        View production server logs"
	@echo "  prod-cleanup     Clean up orphaned processes and stale files"
	@echo ""
	@echo "Live Sync Commands:"
	@echo "  sync-test        Test sync API availability"
	@echo "  sync-api         Start sync API server"
	@echo "  sync-connect     Connect to remote server (requires URL=)"
	@echo "  sync-compare     Compare with remote (requires URL=)"
	@echo "  sync-interactive Open sync web interface"
	@echo ""
	@echo "System Commands:"
	@echo "  init             Initialize the application"
	@echo "  update           Pull latest code and run migrations"
	@echo "  update-dry       Check for updates without applying"
	@echo "  backup           Create database backup"
	@echo "  restore          Restore from backup"
	@echo "  logo             Display the project logo"

# Setup commands
install:
	@echo "📦 Installing dependencies..."
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "📦 Installing Ansible collections..."
	@ansible-galaxy install -r ansible/requirements.yml || { \
		echo "⚠️  Some Ansible collections failed to install (non-critical)"; \
		echo "💡 You can ignore collection errors if you're not using those specific roles"; \
		echo "💡 To retry: ansible-galaxy install -r ansible/requirements.yml --force"; \
		true; \
	}
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

update-dry:
	@echo "🔍 Checking for available updates (dry-run)..."
	@CURRENT_BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	echo "🌿 Current branch: $$CURRENT_BRANCH"; \
	echo "📥 Fetching remote changes..."; \
	git fetch origin $$CURRENT_BRANCH 2>/dev/null || git fetch origin; \
	LOCAL_COMMITS=$$(git rev-list --count origin/$$CURRENT_BRANCH..HEAD 2>/dev/null || echo "0"); \
	REMOTE_COMMITS=$$(git rev-list --count HEAD..origin/$$CURRENT_BRANCH 2>/dev/null || echo "0"); \
	echo ""; \
	echo "📊 Update Status:"; \
	echo "   Local commits ahead: $$LOCAL_COMMITS"; \
	echo "   Remote commits ahead: $$REMOTE_COMMITS"; \
	echo ""; \
	if [ "$$REMOTE_COMMITS" -eq 0 ]; then \
		echo "✅ Already up to date!"; \
		echo "   No updates available."; \
	else \
		echo "🔄 Updates available: $$REMOTE_COMMITS new commit(s)"; \
		echo ""; \
		echo "📋 Recent commits on remote:"; \
		git log --oneline HEAD..origin/$$CURRENT_BRANCH 2>/dev/null | head -10 | sed 's/^/   /'; \
		echo ""; \
		echo "📝 Files that will be updated:"; \
		git diff --name-status HEAD origin/$$CURRENT_BRANCH 2>/dev/null | sed 's/^/   /'; \
		echo ""; \
		echo "💡 To apply updates, run: make update"; \
	fi

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

# Production server management commands
prod-start:
	@echo "🚀 Starting production server in background..."
	@if [ -f .prod-server.pid ]; then \
		if ps -p $$(cat .prod-server.pid) > /dev/null 2>&1; then \
			echo "⚠️  Production server is already running (PID: $$(cat .prod-server.pid))"; \
			echo "Use 'make prod-stop' to stop it first, or 'make prod-restart' to restart."; \
			exit 1; \
		else \
			rm -f .prod-server.pid; \
		fi; \
	fi
	@echo "🔍 Checking if port 5000 is available..."
	@PORT_CHECK=$$(ss -tlnp 2>/dev/null | grep ':5000' || netstat -tlnp 2>/dev/null | grep ':5000' || lsof -Pi :5000 -sTCP:LISTEN 2>/dev/null || echo ""); \
	if [ -n "$$PORT_CHECK" ]; then \
		echo "⚠️  Port 5000 is already in use!"; \
		echo ""; \
		echo "Process using port 5000:"; \
		echo "$$PORT_CHECK" | head -1 | sed 's/^/   /'; \
		echo ""; \
		PID=$$(echo "$$PORT_CHECK" | grep -oP 'pid=\K[0-9]+' | head -1 || echo "$$PORT_CHECK" | awk '{print $$NF}' | grep -oP '[0-9]+/[^/]+' | cut -d'/' -f1 | head -1 || echo ""); \
		if [ -n "$$PID" ]; then \
			echo "💡 Solutions:"; \
			echo "   1. Kill the process: sudo kill $$PID"; \
			echo "   2. Kill all Python on port 5000: sudo pkill -f 'cli.py web'"; \
			echo "   3. Use different port: .venv/bin/python cli.py web --port 5001"; \
			echo "   4. Run cleanup: make prod-cleanup"; \
			echo ""; \
			read -p "Do you want to kill process $$PID now? [y/N]: " response; \
			if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
				echo "🔪 Killing process $$PID..."; \
				kill $$PID 2>/dev/null || sudo kill $$PID; \
				sleep 2; \
				echo "✅ Process killed"; \
			else \
				echo "❌ Cannot start - port 5000 is in use"; \
				exit 1; \
			fi; \
		else \
			echo "⚠️  Could not determine PID, trying pkill..."; \
			read -p "Kill all 'cli.py web' processes? [y/N]: " response; \
			if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
				sudo pkill -f 'cli.py web' && echo "✅ Processes killed" || echo "⚠️  No processes found"; \
				sleep 2; \
			else \
				exit 1; \
			fi; \
		fi; \
	fi
	@mkdir -p logs
	@nohup .venv/bin/python cli.py web --host 0.0.0.0 --port 5000 > logs/production.log 2>&1 & echo $$! > .prod-server.pid
	@sleep 2
	@if ps -p $$(cat .prod-server.pid) > /dev/null 2>&1; then \
		echo "✅ Production server started successfully!"; \
		echo "   PID: $$(cat .prod-server.pid)"; \
		echo "   Access at: http://0.0.0.0:5000"; \
		echo "   Logs: logs/production.log"; \
		echo ""; \
		echo "Use 'make prod-stop' to stop the server"; \
		echo "Use 'make prod-logs' to view logs"; \
	else \
		echo "❌ Failed to start production server"; \
		echo "Check logs/production.log for details"; \
		rm -f .prod-server.pid; \
		exit 1; \
	fi

prod-stop:
	@echo "🛑 Stopping production server..."
	@if [ ! -f .prod-server.pid ]; then \
		echo "⚠️  No PID file found. Checking for orphaned processes..."; \
		PORT_INFO=$$(ss -tlnp 2>/dev/null | grep ':5000' || netstat -tlnp 2>/dev/null | grep ':5000' || echo ""); \
		if [ -n "$$PORT_INFO" ]; then \
			PID=$$(echo "$$PORT_INFO" | grep -oP 'pid=\K[0-9]+' | head -1 || echo "$$PORT_INFO" | awk '{print $$NF}' | grep -oP '[0-9]+' | head -1); \
			echo "⚠️  Found orphaned process on port 5000 (PID: $$PID)"; \
			read -p "Kill this process? [Y/n]: " response; \
			response=$${response:-y}; \
			if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
				kill $$PID 2>/dev/null || sudo kill $$PID; \
				echo "✅ Orphaned process killed"; \
			fi; \
		else \
			echo "✅ No server running on port 5000"; \
		fi; \
		exit 0; \
	fi
	@PID=$$(cat .prod-server.pid); \
	if ps -p $$PID > /dev/null 2>&1; then \
		kill $$PID && echo "✅ Production server stopped (PID: $$PID)"; \
		rm -f .prod-server.pid; \
	else \
		echo "⚠️  Process $$PID not found. Cleaning up PID file."; \
		rm -f .prod-server.pid; \
		echo "🔍 Checking for orphaned processes on port 5000..."; \
		PORT_INFO=$$(ss -tlnp 2>/dev/null | grep ':5000' || netstat -tlnp 2>/dev/null | grep ':5000' || echo ""); \
		if [ -n "$$PORT_INFO" ]; then \
			ORPHAN_PID=$$(echo "$$PORT_INFO" | grep -oP 'pid=\K[0-9]+' | head -1 || echo "$$PORT_INFO" | awk '{print $$NF}' | grep -oP '[0-9]+' | head -1); \
			echo "⚠️  Found orphaned process (PID: $$ORPHAN_PID)"; \
			kill $$ORPHAN_PID 2>/dev/null || sudo kill $$ORPHAN_PID; \
			echo "✅ Orphaned process killed"; \
		fi; \
	fi

prod-restart: prod-stop
	@echo "🔄 Restarting production server..."
	@sleep 1
	@$(MAKE) prod-start

prod-status:
	@echo "📊 Production Server Status:"
	@echo "=============================="
	@if [ -f .prod-server.pid ]; then \
		PID=$$(cat .prod-server.pid); \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "✅ Status: RUNNING"; \
			echo "   PID: $$PID"; \
			echo "   URL: http://0.0.0.0:5000"; \
			echo ""; \
			ps -p $$PID -o pid,ppid,cmd,%mem,%cpu,etime; \
		else \
			echo "❌ Status: STOPPED"; \
			echo "   PID file exists but process not running"; \
			echo "   Cleaning up stale PID file..."; \
			rm -f .prod-server.pid; \
		fi; \
	else \
		echo "❌ Status: STOPPED"; \
		echo "   No PID file found"; \
	fi; \
	echo ""; \
	echo "🔍 Port 5000 Status:"; \
	PORT_INFO=$$(ss -tlnp 2>/dev/null | grep ':5000' || netstat -tlnp 2>/dev/null | grep ':5000' || echo ""); \
	if [ -n "$$PORT_INFO" ]; then \
		PORT_PID=$$(echo "$$PORT_INFO" | grep -oP 'pid=\K[0-9]+' | head -1 || echo "$$PORT_INFO" | awk '{print $$NF}' | grep -oP '[0-9]+' | head -1); \
		if [ -f .prod-server.pid ] && [ "$$PORT_PID" = "$$(cat .prod-server.pid 2>/dev/null)" ]; then \
			echo "   ✅ Port in use by our server"; \
		else \
			echo "   ⚠️  Port in use by another process (PID: $$PORT_PID)"; \
			echo "$$PORT_INFO" | head -1 | sed 's/^/   /'; \
			echo "   💡 Run 'make prod-cleanup' to fix"; \
		fi; \
	else \
		echo "   ✅ Port 5000 is available"; \
		if [ ! -f .prod-server.pid ]; then \
			echo ""; \
			echo "💡 Use 'make prod-start' to start the server"; \
		fi; \
	fi

prod-logs:
	@echo "📋 Production Server Logs:"
	@echo "=============================="
	@if [ -f logs/production.log ]; then \
		tail -f logs/production.log; \
	else \
		echo "⚠️  No log file found at logs/production.log"; \
		echo "Server may not have been started yet."; \
	fi

prod-cleanup:
	@echo "🧹 Cleaning up production server artifacts..."
	@echo ""
	@CLEANED=0; \
	\
	if [ -f .prod-server.pid ]; then \
		PID=$$(cat .prod-server.pid); \
		if ! ps -p $$PID > /dev/null 2>&1; then \
			echo "🗑️  Removing stale PID file (.prod-server.pid)"; \
			rm -f .prod-server.pid; \
			CLEANED=$$((CLEANED + 1)); \
		else \
			echo "⚠️  Server is running (PID: $$PID) - use 'make prod-stop' first"; \
		fi; \
	fi; \
	\
	PORT_INFO=$$(ss -tlnp 2>/dev/null | grep ':5000' || netstat -tlnp 2>/dev/null | grep ':5000' || echo ""); \
	if [ -n "$$PORT_INFO" ]; then \
		PORT_PID=$$(echo "$$PORT_INFO" | grep -oP 'pid=\K[0-9]+' | head -1 || echo "$$PORT_INFO" | awk '{print $$NF}' | grep -oP '[0-9]+' | head -1); \
		if [ -f .prod-server.pid ] && [ "$$PORT_PID" != "$$(cat .prod-server.pid 2>/dev/null)" ] || [ ! -f .prod-server.pid ]; then \
			echo "🔍 Found orphaned process on port 5000 (PID: $$PORT_PID)"; \
			echo "$$PORT_INFO" | head -1 | sed 's/^/   /'; \
			read -p "Kill this process? [Y/n]: " response; \
			response=$${response:-y}; \
			if [ "$$response" = "y" ] || [ "$$response" = "Y" ]; then \
				kill $$PORT_PID 2>/dev/null || sudo kill $$PORT_PID; \
				sleep 1; \
				if ! ps -p $$PORT_PID > /dev/null 2>&1; then \
					echo "✅ Orphaned process killed"; \
					CLEANED=$$((CLEANED + 1)); \
				else \
					echo "⚠️  Process still running, trying SIGKILL..."; \
					kill -9 $$PORT_PID 2>/dev/null || sudo kill -9 $$PORT_PID; \
					CLEANED=$$((CLEANED + 1)); \
				fi; \
			fi; \
		fi; \
	fi; \
	\
	echo ""; \
	if [ $$CLEANED -gt 0 ]; then \
		echo "✅ Cleanup complete: $$CLEANED item(s) cleaned"; \
	else \
		echo "✅ No cleanup needed - everything is clean!"; \
	fi; \
	echo ""; \
	echo "💡 Tip: Run 'make prod-status' to verify"

# Display logo
logo:
	@.venv/bin/python app/utils/logo.py startup

# Live Sync Commands
sync-test:
	@echo "🔄 Testing Sync API..."
	@curl -s http://localhost:5000/api/v1/sync/test | python3 -m json.tool || echo "❌ Sync API not available. Make sure server is running."

sync-api:
	@echo "🚀 Starting Sync API Server..."
	@echo "   The sync API is available when the web server is running."
	@echo "   Use 'make prod-start' or 'make run' to start the server."
	@echo ""
	@echo "Sync API endpoints:"
	@echo "  - POST /api/v1/sync/connect"
	@echo "  - GET  /api/v1/sync/inventory"
	@echo "  - POST /api/v1/sync/compare"
	@echo "  - POST /api/v1/sync/transfer"
	@echo "  - POST /api/v1/sync/receive"

sync-connect:
	@echo "🔗 Connecting to Remote Server..."
	@if [ -z "$(URL)" ]; then \
		echo "❌ Error: URL parameter is required"; \
		echo "Usage: make sync-connect URL=https://remote-server:5000"; \
		exit 1; \
	fi
	@echo "Testing connection to $(URL)..."
	@curl -s $(URL)/api/v1/sync/test && echo "\n✅ Connection successful!" || echo "❌ Connection failed"

sync-compare:
	@echo "⚖️  Comparing with Remote Server..."
	@if [ -z "$(URL)" ]; then \
		echo "❌ Error: URL parameter is required"; \
		echo "Usage: make sync-compare URL=https://remote-server:5000"; \
		exit 1; \
	fi
	@echo "Fetching remote inventory from $(URL)..."
	@echo "Use the web interface for detailed comparison."
	@echo ""
	@echo "Opening web interface..."
	@echo "Navigate to: http://localhost:5000/sync/interactive"

sync-interactive:
	@echo "🌐 Opening Interactive Sync Interface..."
	@echo ""
	@echo "📋 Steps to use:"
	@echo "1. Make sure both servers are running"
	@echo "2. Navigate to: http://localhost:5000/sync/interactive"
	@echo "3. Enter remote server URL"
	@echo "4. Review differences"
	@echo "5. Select items to sync"
	@echo "6. Start sync"
	@echo ""
	@if command -v xdg-open > /dev/null 2>&1; then \
		xdg-open http://localhost:5000/sync/interactive 2>/dev/null || true; \
	elif command -v open > /dev/null 2>&1; then \
		open http://localhost:5000/sync/interactive 2>/dev/null || true; \
	else \
		echo "Please open: http://localhost:5000/sync/interactive"; \
	fi

# Sync workflow helpers
sync-full:
	@echo "🔄 Starting Full Sync Workflow..."
	@if [ -z "$(URL)" ]; then \
		echo "❌ Error: URL parameter is required"; \
		echo "Usage: make sync-full URL=https://remote-server:5000 [PASSWORD=secret]"; \
		exit 1; \
	fi
	@echo ""
	@echo "Step 1: Testing connection..."
	@$(MAKE) sync-connect URL=$(URL)
	@echo ""
	@echo "Step 2: Opening interactive interface..."
	@$(MAKE) sync-interactive
	@echo ""
	@echo "✅ Ready to sync! Use the web interface to complete the process."
