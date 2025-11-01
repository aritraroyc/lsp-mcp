.PHONY: help install dev test run-stdio run-http run-example clean

# Default target
help:
	@echo "Java Error Checker MCP Service - Make targets:"
	@echo ""
	@echo "Installation & Setup:"
	@echo "  make install          - Install Python dependencies"
	@echo "  make dev              - Install with development dependencies"
	@echo ""
	@echo "Running:"
	@echo "  make run-stdio        - Start stdio transport (Claude Desktop)"
	@echo "  make run-http         - Start HTTP/SSE transport"
	@echo "  make run-example      - Run example client"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests"
	@echo "  make test-e2e         - Run end-to-end tests"
	@echo "  make lint             - Run code linting"
	@echo "  make format           - Format code"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            - Remove temporary files"
	@echo "  make clean-workspaces - Remove session workspaces"
	@echo ""

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov black isort pylint

test: test-unit test-e2e

test-unit:
	python -m pytest src/tests/test_server.py -v

test-e2e:
	python -m pytest src/tests/test_end_to_end.py -v

test-coverage:
	python -m pytest src/tests/ --cov=src --cov-report=html

run-stdio:
	python src/server/server.py

run-http:
	python src/server/server_sse.py --host 0.0.0.0 --port 8000

run-example:
	python src/examples/example_client.py

run-example-interactive:
	python src/examples/example_client.py --interactive

lint:
	python -m pylint src/core/*.py src/server/*.py

format:
	black src/ --line-length=100
	python -m isort src/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage_*" -exec rm -rf {} + 2>/dev/null || true

clean-workspaces:
	rm -rf /tmp/jdtls-workspaces/*
	@echo "Cleaned session workspaces"

docker-build:
	docker build -t java-error-checker:latest .

docker-run:
	docker run -p 8000:8000 java-error-checker:latest

docs:
	@echo "Documentation is in docs/ directory:"
	@echo "  - docs/README.md          (Quick start & usage guide)"
	@echo "  - docs/ARCHITECTURE.md    (System design & patterns)"
	@echo "  - docs/DEPLOYMENT.md      (Deployment & examples)"
	@echo "  - docs/REFACTORING.md     (Code refactoring details)"
	@echo "  - docs/PROJECT_STRUCTURE.md (File organization)"
