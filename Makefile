.PHONY: help setup up down logs test clean

help: ## Show this help message
	@echo "Artisan Promotion Platform - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Set up development environment
	@./scripts/dev-setup.sh

up: ## Start all services
	@docker-compose up -d
	@echo "Services started. Frontend: http://localhost:3000, Backend: http://localhost:8000"

down: ## Stop all services
	@docker-compose down

logs: ## View logs from all services
	@docker-compose logs -f

logs-backend: ## View backend logs
	@docker-compose logs -f backend

logs-frontend: ## View frontend logs
	@docker-compose logs -f frontend

test: ## Run all tests
	@echo "Running backend tests..."
	@docker-compose exec backend pytest
	@echo "Running frontend tests..."
	@docker-compose exec frontend npm test -- --run

test-backend: ## Run backend tests only
	@docker-compose exec backend pytest

test-frontend: ## Run frontend tests only
	@docker-compose exec frontend npm test -- --run

clean: ## Clean up containers and volumes
	@docker-compose down -v
	@docker system prune -f

restart: ## Restart all services
	@docker-compose restart

shell-backend: ## Open shell in backend container
	@docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	@docker-compose exec frontend sh

db-shell: ## Open PostgreSQL shell
	@docker-compose exec postgres psql -U artisan_user -d artisan_platform