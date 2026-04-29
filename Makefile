# ClawShell v1.0 Makefile

.PHONY: help install test clean docs

# Colors
GREEN  := \033[0;32m
YELLOW := \033[0;33m
NC     := \033[0m

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[1;32m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install ClawShell
	@bash install.sh

install-dev: ## Install with dev dependencies
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt

test: ## Run tests
	@python -m pytest tests/ -v

test-coverage: ## Run tests with coverage
	@python -m pytest tests/ --cov=lib --cov-report=html --cov-report=term

clean: ## Clean build artifacts
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

docs: ## Build documentation
	@cd docs && make html

lint: ## Run linting
	@flake8 lib/ --max-line-length=120 --ignore=E501,W503

format: ## Format code
	@black lib/ tests/

health: ## Check system health
	@clawshell health

status: ## Show system status
	@clawshell status

.DEFAULT_GOAL := help
