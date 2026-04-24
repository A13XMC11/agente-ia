.PHONY: help install dev docker-up docker-down test test-cov lint format type-check security clean

help:
	@echo "Agente-IA Development Commands"
	@echo "==============================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install dependencies"
	@echo "  make env              - Copy .env.example to .env"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Run FastAPI server (hot reload)"
	@echo "  make docker-up        - Start Docker services (Redis, FastAPI, Streamlit)"
	@echo "  make docker-down      - Stop Docker services"
	@echo "  make docker-logs      - View Docker logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-cov         - Run tests with coverage report"
	@echo "  make test-watch       - Run tests in watch mode"
	@echo "  make test-one TEST=path/to/test.py::TestClass::test_method"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             - Run linting (flake8)"
	@echo "  make format           - Format code (black + isort)"
	@echo "  make type-check       - Run type checking (mypy)"
	@echo "  make security         - Security scan"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate       - Run database migrations"
	@echo "  make db-reset         - Reset database (dev only)"
	@echo ""
	@echo "Other:"
	@echo "  make clean            - Clean cache and artifacts"
	@echo "  make requirements      - Generate requirements.txt"

# ============================================================================
# SETUP
# ============================================================================

install:
	pip install -r requirements.txt

env:
	cp .env.example .env
	@echo "Created .env - please configure it with your credentials"

# ============================================================================
# DEVELOPMENT
# ============================================================================

dev:
	python main.py

docker-up:
	docker-compose up -d
	@echo "Services started:"
	@echo "  FastAPI: http://localhost:8000"
	@echo "  Streamlit: http://localhost:8501"
	@echo "  Redis: localhost:6379"
	@echo ""
	@echo "View logs with: make docker-logs"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

docker-rebuild:
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d

# ============================================================================
# TESTING
# ============================================================================

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report: htmlcov/index.html"

test-watch:
	pytest-watch tests/ -v

test-one:
	pytest $(TEST) -v

test-fast:
	pytest tests/ -v -x -q

# ============================================================================
# CODE QUALITY
# ============================================================================

lint:
	flake8 . --max-line-length=100 --ignore=E203,W503 --exclude=.git,__pycache__,venv

format:
	black . --line-length=100
	isort . --profile=black --line-length=100

format-check:
	black . --line-length=100 --check
	isort . --profile=black --line-length=100 --check-only

type-check:
	mypy . --ignore-missing-imports

type-check-strict:
	mypy . --strict --ignore-missing-imports

security:
	bandit -r . -ll -x ./tests,./venv

security-check:
	pip-audit

# ============================================================================
# DATABASE
# ============================================================================

db-migrate:
	@echo "Running database migrations..."
	# TODO: Add migration command

db-reset:
	@echo "WARNING: This will reset the development database!"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Resetting database..."; \
	fi

# ============================================================================
# CLEANUP
# ============================================================================

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

clean-all: clean
	rm -rf venv/
	rm -rf .env

# ============================================================================
# REQUIREMENTS
# ============================================================================

requirements-freeze:
	pip freeze > requirements.txt

# ============================================================================
# SHORTCUTS
# ============================================================================

# Quick development setup
setup: install env
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Edit .env with your credentials"
	@echo "2. Run: make docker-up"
	@echo "3. FastAPI will be available at http://localhost:8000"

# All checks before commit
check: format type-check lint test-fast security
	@echo ""
	@echo "All checks passed! ✓"

# Quick format and test
quick: format test-fast

# Production deployment checks
prod-check: format type-check lint test security
	@echo ""
	@echo "Ready for production! ✓"
