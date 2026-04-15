# ============================================
# Makefile para OBRAS FINANCEIRO PRO
# ============================================
# Facilita o uso do Docker e comandos comuns
# ============================================

# Variáveis
DOCKER_COMPOSE := docker compose
PROJECT_NAME := obras_financeiro
PYTHON := python

# ==========================================
# Help
# ==========================================
.PHONY: help
help: ## Show this help message
	@echo ''
	@echo '🏗️  OBRAS FINANCEIRO PRO - Makefile Commands'
	@echo '============================================'
	@echo ''
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ''

# ==========================================
# Docker Build
# ==========================================
.PHONY: build build-no-cache rebuild
build: ## Build Docker images
	$(DOCKER_COMPOSE) build

build-no-cache: ## Build Docker images without cache
	$(DOCKER_COMPOSE) build --no-cache

rebuild: down build ## Rebuild and restart services

# ==========================================
# Docker Up/Down
# ==========================================
.PHONY: up up-detach down restart
up: ## Start services (foreground)
	$(DOCKER_COMPOSE) up

up-detach: ## Start services (detached mode)
	$(DOCKER_COMPOSE) up -d

down: ## Stop and remove containers
	$(DOCKER_COMPOSE) down

restart: ## Restart all services
	$(DOCKER_COMPOSE) restart

# ==========================================
# Docker Logs
# ==========================================
.PHONY: logs logs-follow logs-app logs-db logs-redis logs-nginx
logs: ## Show all logs
	$(DOCKER_COMPOSE) logs

logs-follow: ## Follow logs in real-time
	$(DOCKER_COMPOSE) logs -f --tail=100

logs-app: ## Show app logs
	$(DOCKER_COMPOSE) logs -f app

logs-db: ## Show PostgreSQL logs
	$(DOCKER_COMPOSE) logs -f postgres

logs-redis: ## Show Redis logs
	$(DOCKER_COMPOSE) logs -f redis

logs-nginx: ## Show Nginx logs
	$(DOCKER_COMPOSE) logs -f nginx

# ==========================================
# Database Management
# ==========================================
.PHONY: db-shell db-backup db-restore db-migrate db-roles db-admin db-init
db-shell: ## Open PostgreSQL shell
	$(DOCKER_COMPOSE) exec postgres psql -U $${POSTGRES_USER:-obras_user} -d $${POSTGRES_DB:-obras_financeiro}

db-backup: ## Backup database
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec postgres pg_dump -U $${POSTGRES_USER:-obras_user} -d $${POSTGRES_DB:-obras_financeiro} > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup criado em backups/"

db-restore: ## Restore database from backup (usage: make db-restore FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Usage: make db-restore FILE=backup.sql"; \
		exit 1; \
	fi
	cat $(FILE) | $(DOCKER_COMPOSE) exec -T postgres psql -U $${POSTGRES_USER:-obras_user} -d $${POSTGRES_DB:-obras_financeiro}
	@echo "✅ Database restored!"

db-migrate: ## Run Flask database migrations
	$(DOCKER_COMPOSE) exec app flask db upgrade
	@echo "✅ Migrations applied!"

db-roles: ## Initialize default roles
	$(DOCKER_COMPOSE) exec app flask init_roles
	@echo "✅ Roles initialized!"

db-admin: ## Create admin user
	$(DOCKER_COMPOSE) exec app flask create_admin
	@echo "✅ Admin user created!"

db-init: db-migrate db-roles db-admin ## Full database initialization

# ==========================================
# Shell Access
# ==========================================
.PHONY: shell app-shell redis-cli
shell: ## Open shell in app container
	$(DOCKER_COMPOSE) exec app /bin/bash

app-shell: ## Open Python shell in app container
	$(DOCKER_COMPOSE) exec app flask shell

redis-cli: ## Open Redis CLI
	$(DOCKER_COMPOSE) exec redis redis-cli

# ==========================================
# Testing & Quality
# ==========================================
.PHONY: test test-coverage lint format
test: ## Run tests
	$(DOCKER_COMPOSE) exec app pytest

test-coverage: ## Run tests with coverage
	$(DOCKER_COMPOSE) exec app pytest --cov=app --cov-report=term-missing

lint: ## Run linter
	$(DOCKER_COMPOSE) exec app ruff check .

format: ## Format code
	$(DOCKER_COMPOSE) exec app ruff format .

# ==========================================
# Flask Commands
# ==========================================
.PHONY: flask seed
flask: ## Run Flask commands (usage: make flask COMMAND=init_roles)
	$(DOCKER_COMPOSE) exec app flask $(COMMAND)

seed: ## Seed initial data
	$(DOCKER_COMPOSE) exec app flask seed_db

# ==========================================
# Cleanup
# ==========================================
.PHONY: clean prune reset
clean: down ## Remove containers and volumes
	$(DOCKER_COMPOSE) down -v
	@echo "✅ Containers and volumes removed!"

prune: ## Remove all unused Docker resources
	docker system prune -af --volumes
	@echo "✅ Docker pruned!"

reset: ## Complete reset (DANGER: removes everything)
	@echo "⚠️  WARNING: This will remove ALL Docker data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	$(DOCKER_COMPOSE) down -v --rmi all --remove-orphans
	docker system prune -af --volumes
	@echo "✅ Everything removed!"

# ==========================================
# Development
# ==========================================
.PHONY: dev dev-up
dev: ## Start development environment
	FLASK_ENV=development $(DOCKER_COMPOSE) up -d
	@echo "🚀 Development environment started!"
	@echo "   App: http://localhost:5000"
	@echo "   DB: localhost:5432"
	@echo "   Redis: localhost:6379"

dev-up: build up-detach ## Build and start development

# ==========================================
# Production
# ==========================================
.PHONY: prod prod-up
prod: ## Start production environment
	FLASK_ENV=production $(DOCKER_COMPOSE) up -d
	@echo "🚀 Production environment started!"

prod-up: build up-detach ## Build and start production

# ==========================================
# Status & Info
# ==========================================
.PHONY: status ps
status: ## Show service status
	$(DOCKER_COMPOSE) ps

ps: ## Show service status (alias)
	$(DOCKER_COMPOSE) ps

stats: ## Show Docker stats
	docker stats --no-stream

# ==========================================
# SSL/TLS (Let's Encrypt)
# ==========================================
.PHONY: ssl-cert ssl-renew
ssl-cert: ## Generate SSL certificates (Let's Encrypt)
	@echo "🔐 Generating SSL certificates..."
	@echo "Note: Configure nginx with certbot for production"
	@echo "See DEPLOY_RENDER.md for instructions"

ssl-renew: ## Renew SSL certificates
	@echo "🔄 Renewing SSL certificates..."
	@echo "Configure with your SSL provider"

# ==========================================
# Default target
# ==========================================
.PHONY: all
all: help
