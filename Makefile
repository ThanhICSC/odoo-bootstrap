# ============================================================
# odoo-bootstrap — Developer Makefile
# ============================================================

.PHONY: help install dev-install test test-unit test-int lint format typecheck clean zip

SHELL := /bin/bash
PROJECT := odoo_bootstrap

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install for production
	pip install .

dev-install: ## Install with dev dependencies
	pip install -e ".[dev]"

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-int: ## Run integration tests only
	pytest tests/integration/ -v

lint: ## Run ruff linter
	ruff check $(PROJECT)/

format: ## Format with black + isort
	black $(PROJECT)/ tests/
	isort $(PROJECT)/ tests/

typecheck: ## Run mypy
	mypy $(PROJECT)/

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

zip: clean ## Build odoo-bootstrap.zip ready for distribution
	@echo "Building odoo-bootstrap.zip..."
	@cd .. && zip -r odoo-bootstrap.zip odoo-bootstrap/ \
		--exclude "odoo-bootstrap/.git/*" \
		--exclude "odoo-bootstrap/.venv/*" \
		--exclude "odoo-bootstrap/dist/*" \
		--exclude "odoo-bootstrap/__pycache__/*" \
		--exclude "odoo-bootstrap/*.egg-info/*"
	@echo "✓ ../odoo-bootstrap.zip created"

.DEFAULT_GOAL := help
