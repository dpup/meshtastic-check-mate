# CI/CD Pipeline for Check-Mate

This document describes the Continuous Integration and Continuous Deployment (CI/CD) setup for the Check-Mate project.

## Workflows

### PR Validation (`pr-validation.yml`)

This workflow runs on every pull request to the `main` branch.

**Features:**
- Runs on multiple Python versions (3.9, 3.10, 3.11, 3.12)
- Performs code linting with flake8
- Runs all tests with pytest
- Generates code coverage reports
- Artifacts: Test results and coverage reports for each Python version

### CI/CD Pipeline (`ci-cd.yml`)

This workflow runs when code is pushed to the `main` branch.

**Features:**
- Runs linting and tests on Python 3.12
- Builds and pushes Docker images to GitHub Container Registry (only for main branch)
- Tags Docker images with:
  - Git SHA (long format)
  - Branch name
  - `latest`
- Artifacts: Test results and coverage reports

### Publish Docker Image (`publish-docker-image.yaml`)

This workflow runs when:
- Code is pushed to the `release` branch

**Features:**
- Runs tests to verify release quality
- Builds and pushes Docker images to GitHub Container Registry
- Tags Docker images with:
  - `release` tag (for stable production use)
  - Git SHA (long format) for traceability
- Generates build provenance attestation for supply chain security

## Docker Images

Docker images are published to GitHub Container Registry (ghcr.io) and can be pulled with:

```bash
# Latest development version (from main branch)
docker pull ghcr.io/meshtastic/check-mate:latest

# Stable release version (from release branch)
docker pull ghcr.io/meshtastic/check-mate:release

# Specific build by SHA
docker pull ghcr.io/meshtastic/check-mate:sha-1234567890abcdef
```

## Configuration

The CI/CD workflows use GitHub secrets:
- `GITHUB_TOKEN` (automatically provided by GitHub) for pushing to GitHub Container Registry
- Optional: `PYPI_API_TOKEN` for publishing to PyPI (if enabled)