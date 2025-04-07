# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
Always use the Makefile commands when performing operations to ensure the virtual environment is used correctly:

- Setup: `make setup` (Creates virtual environment and installs dependencies)
- Install: `make install` (Installs the package)
- Developer install: `make develop` (Installs the package with dev dependencies)
- Run tests: `make test` 
- Run main application: `make run HOST=<device_ip>` (Set additional options as environment variables)
- Check status: `make status`
- Run linting: `make lint`
- Clean project: `make clean`

## Code style
- Use Python type hints for function parameters and return values
- Format code with 4-space indentation
- Class names use PascalCase, functions and variables use snake_case
- Import order: standard library, third-party, local modules
- Use dataclasses for data containers
- Use enum.Enum for enumerated values
- Error handling: use try/except with specific exceptions
- JSON logging format for consistency
- Include detailed docstrings for functions and classes