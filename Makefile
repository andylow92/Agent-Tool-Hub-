.PHONY: test lint format docker-build docker-up docker-down help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

test: ## Run all tests
	pytest tests/ -v

lint: ## Run linter
	ruff check .

format: ## Format code
	ruff format .

format-check: ## Check code formatting
	ruff format --check .

docker-build: ## Build all Docker images
	docker compose build

docker-up: ## Start all services
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
