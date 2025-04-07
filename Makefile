.PHONY: setup install develop run status test lint clean

VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

setup: $(VENV)
	$(PIP) install -r requirements.txt

install: $(VENV)
	$(PIP) install -e .

develop: $(VENV)
	$(PIP) install -e ".[dev]"

$(VENV):
	python3 -m venv $(VENV)

run:
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Error: HOST environment variable is required"; \
		echo "Usage: make run HOST=<device_ip> [LOCATION=<location>] [HEALTHCHECKURL=<url>]"; \
		exit 1; \
	fi; \
	echo "🚀 Starting Check-Mate with host $(HOST)..."; \
	$(PYTHON) -m checkmate.main --host $(HOST) $(if $(LOCATION),--location $(LOCATION),) $(if $(HEALTHCHECKURL),--healthcheck $(HEALTHCHECKURL),)

status:
	@$(PYTHON) -m checkmate.main --status > /tmp/check_mate_status.json; \
	STATUS_CODE=$$?; \
	if [ $$STATUS_CODE -eq 0 ]; then \
		echo "✅ Check-Mate is running and active (status code: $$STATUS_CODE)"; \
	elif [ $$STATUS_CODE -eq 1 ]; then \
		echo "ℹ️ Check-Mate is not active (status code: $$STATUS_CODE)"; \
	else \
		echo "❌ Check-Mate status check failed (status code: $$STATUS_CODE)"; \
	fi; \
	cat /tmp/check_mate_status.json

test:
	@echo "🧪 Running tests..."
	@$(PYTHON) -m pytest

lint:
	@echo "🔍 Running code quality checks..."
	@$(PYTHON) -m flake8 src/ tests/ || (echo "❌ Code quality issues found"; exit 1)

clean:
	@echo "🧹 Cleaning up environment..."
	@rm -rf $(VENV) build/ dist/ *.egg-info/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"