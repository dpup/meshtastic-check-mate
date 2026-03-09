.PHONY: help setup install develop run status test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Sync dependencies
	uv sync

install: ## Install the package
	uv sync

develop: ## Install with dev dependencies
	uv sync --extra dev

run: ## Run the app (HOST=<ip> required)
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Error: HOST environment variable is required"; \
		echo "Usage: make run HOST=<device_ip> [LOCATION=<location>] [HEALTHCHECKURL=<url>] [LATITUDE=<lat>] [LONGITUDE=<lon>] [WEATHER_API_KEY=<key>]"; \
		exit 1; \
	fi; \
	echo "🚀 Starting Check-Mate with host $(HOST)..."; \
	uv run python -m checkmate.main --host $(HOST) \
		$(if $(LOCATION),--location $(LOCATION),) \
		$(if $(HEALTHCHECKURL),--healthcheck $(HEALTHCHECKURL),) \
		$(if $(LATITUDE),--latitude $(LATITUDE),) \
		$(if $(LONGITUDE),--longitude $(LONGITUDE),) \
		$(if $(WEATHER_API_KEY),--weather-api-key $(WEATHER_API_KEY),)

status: ## Check app status
	@uv run python -m checkmate.main --status > /tmp/check_mate_status.json; \
	STATUS_CODE=$$?; \
	if [ $$STATUS_CODE -eq 0 ]; then \
		echo "✅ Check-Mate is running and active (status code: $$STATUS_CODE)"; \
	elif [ $$STATUS_CODE -eq 1 ]; then \
		echo "ℹ️ Check-Mate is not active (status code: $$STATUS_CODE)"; \
	else \
		echo "❌ Check-Mate status check failed (status code: $$STATUS_CODE)"; \
	fi; \
	cat /tmp/check_mate_status.json

test: ## Run tests
	@echo "🧪 Running tests..."
	@uv run pytest

lint: ## Run code quality checks
	@echo "🔍 Running code quality checks..."
	@uv run flake8 src/ tests/ || (echo "❌ Code quality issues found"; exit 1)

clean: ## Remove build artifacts and venv
	@echo "🧹 Cleaning up environment..."
	@rm -rf .venv build/ dist/ *.egg-info/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"
