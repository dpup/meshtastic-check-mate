.PHONY: setup run status test lint clean

VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

setup: $(VENV)
	$(PIP) install -r requirements.txt

$(VENV):
	python3 -m venv $(VENV)

run:
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Error: HOST environment variable is required"; \
		echo "Usage: make run HOST=<device_ip> [LOCATION=<location>] [HEALTHCHECKURL=<url>]"; \
		exit 1; \
	fi; \
	echo "🚀 Starting Check-Mate with host $(HOST)..."; \
	$(PYTHON) check_mate.py --host $(HOST) $(if $(LOCATION),--location $(LOCATION),) $(if $(HEALTHCHECKURL),--healthcheck $(HEALTHCHECKURL),)

status:
	@$(PYTHON) check_mate.py --status > /tmp/check_mate_status.json; \
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
	@$(PYTHON) -m flake8 *.py || (echo "❌ Code quality issues found"; exit 1)

clean:
	@echo "🧹 Cleaning up environment..."
	@rm -rf $(VENV)
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"