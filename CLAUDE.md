# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the app locally
uv run python app.py

# Run CLI utilities for endpoint testing
uv run python model_serving_utils.py list
uv run python model_serving_utils.py info [endpoint-name]
uv run python model_serving_utils.py test [endpoint-name]
uv run python model_serving_utils.py chat [endpoint-name]

# Run demo CLI
uv run python demo_cli.py

# Sync code to workspace
databricks sync --watch . /Workspace/Users/[your-email]/apps/[app-name]/

# Deploy to Databricks
databricks apps create [app-name]  # First time only
databricks apps deploy [app-name] --source-code-path /Workspace/Users/[your-email]/apps/[app-name]
databricks apps deploy [app-name] --source-code-path /Workspace/Users/[your-email]/apps/[app-name] --mode SNAPSHOT

# Manage Databricks apps
databricks apps list
databricks apps get [app-name]
```

## Project Architecture

This is a Databricks chatbot application built with Dash that works in both local development and Databricks deployment environments.

### Core Components

- **app.py**: Main application entry point that handles environment detection and orchestrates the Dash web server
- **DatabricksChatbot.py**: The main chatbot UI component implementing the chat interface, message handling, and real-time interactions
- **model_serving_utils.py**: Comprehensive utilities for interacting with Databricks serving endpoints, includes CLI interface and endpoint compatibility checking
- **demo_cli.py**: Simple CLI demo script for quick testing

### Key Architecture Patterns

**Environment Detection**: The app automatically detects whether it's running locally (uses `.env` file) or on Databricks (uses `app.yaml` resource configuration) via `DATABRICKS_RUNTIME_VERSION`.

**Endpoint Compatibility**: The system validates serving endpoint compatibility before attempting to use them. Supported endpoint types:
- `llm/v1/chat` - Standard LLM chat endpoints  
- `agent/v1/chat` / `agent/v2/chat` - Agent chat endpoints
- `agent/v1/supervisor` / `agent/v2/supervisor` - Multi-agent supervisor endpoints
- `agent/v1/responses` - Agent response endpoints

**Dash Component Architecture**: Uses a class-based approach for the chatbot component with callback registration and CSS styling encapsulation.

### Configuration

**Local Development**: Set `SERVING_ENDPOINT` environment variable to your endpoint name (not full URL). Use `.env` file or export directly.

**Databricks Deployment**: Configure `app.yaml` with serving endpoint resource and proper `CAN_QUERY` permissions. Dashboard URLs can be configured via environment variables.

## Environment Variables

- `SERVING_ENDPOINT`: Name of the Databricks serving endpoint (required)
- `DASHBOARD_1_URL` through `DASHBOARD_4_URL`: Optional dashboard embed URLs
- `DATABRICKS_RUNTIME_VERSION`: Auto-set in Databricks environment for detection

## Dependencies

Uses `uv` package manager with dependencies defined in `pyproject.toml`:
- `dash==3.0.2` - Web framework
- `dash-bootstrap-components==2.0.0` - UI components  
- `mlflow>=2.21.2` - Model serving integration
- `databricks-sdk` - Databricks API access
- `rich>=14.1.0` - CLI formatting

## Common Issues

Reference `TROUBLESHOOTING.md` for detailed troubleshooting of endpoint compatibility issues, particularly around unsupported endpoint types and response format mismatches.