# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run tests: `python -m unittest discover`
- Run single test: `python -m unittest test_quality.TestQuality.test_excellent_quality`
- Run main application: `python check-mate.py --host <device_ip> --location <location>`
- Check status: `python check-mate.py --status`

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