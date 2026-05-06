# ─── Trovly dev Makefile ─────────────────────────────────────
# `make` (with no target) prints help.

.DEFAULT_GOAL := help
SHELL := /bin/bash

PYTHON ?= python3
VENV   ?= .venv
PIP    := $(VENV)/bin/pip
PY     := $(VENV)/bin/python

.PHONY: help install dev down logs shell lint fmt test audit clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create local venv and install dev deps
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

dev: ## Start the Dockerized dev site at http://localhost:8501
	docker compose up --build -d
	@echo "→ http://localhost:8501"

down: ## Stop the dev site
	docker compose down

logs: ## Tail dev site logs
	docker compose logs -f trovly

shell: ## Open a shell inside the dev container
	docker compose exec trovly bash

lint: ## Ruff + black --check
	$(VENV)/bin/ruff check .
	$(VENV)/bin/black --check .

fmt: ## Auto-format with black + ruff --fix
	$(VENV)/bin/black .
	$(VENV)/bin/ruff check --fix .

test: ## Run pytest
	$(VENV)/bin/pytest

audit: ## pip-audit + detect-secrets scan
	$(VENV)/bin/pip-audit -r requirements.txt || true
	$(VENV)/bin/detect-secrets scan --baseline .secrets.baseline || true

clean: ## Remove caches and the venv
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
