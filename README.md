# Databricks Chatbot App

Based on https://medium.com/@AI-on-Databricks/vibe-coding-your-first-databricks-app-8d662f41b959


A Databricks chatbot application that works seamlessly in both local development and Databricks deployment environments. Supports both traditional chat endpoints and multi-agent supervisor endpoints created with agent-bricks.

## Features

- 🤖 Interactive chatbot interface using Dash
- 🔄 Seamless local development and Databricks deployment
- 🎨 Modern, responsive UI with Databricks branding
- ⚡ Real-time chat with typing indicators
- 🔒 Secure endpoint access with proper permissions
- 🧠 Multi-agent supervisor endpoint support (agent-bricks)
- 🛠️ CLI utilities for endpoint testing and management

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Databricks workspace access
- A Databricks serving endpoint (e.g., Claude 3.5 Sonnet, multi-agent supervisor)

## Quick Start

### 1. Install Dependencies

```bash
# Install dependencies using uv
uv sync
```

### 2. Local Development

Set your serving endpoint name as an environment variable:

```bash
# Option 1: Set environment variable directly
export SERVING_ENDPOINT="databricks-claude-3-7-sonnet"
# Or for multi-agent supervisor endpoints:
export SERVING_ENDPOINT="my-agent-supervisor"

# Option 2: Create a .env file
echo "SERVING_ENDPOINT=databricks-claude-3-7-sonnet" > .env
```

Run the application locally:

```bash
uv run python app.py
```

The app will be available at `http://localhost:8050`

### 3. Databricks Deployment

First, sync your code to the workspace:

```bash
# Sync code to workspace (with watch for continuous sync)
databricks sync --watch . /Workspace/Users/your-email@databricks.com/apps/your-app-name/
```

Then create and deploy your app:

```bash
# Create the app (first time only)
databricks apps create your-app-name

# Deploy the app from workspace source
databricks apps deploy your-app-name --source-code-path /Workspace/Users/your-email@databricks.com/apps/your-app-name

# Deploy with snapshot mode (recommended for updates)
databricks apps deploy your-app-name --source-code-path /Workspace/Users/your-email@databricks.com/apps/your-app-name --mode SNAPSHOT
```

### App Management Commands

```bash
# List all deployed apps
databricks apps list

# Get app details and status
databricks apps get your-app-name

# Get deployment details
databricks apps get-deployment your-app-name deployment-id

# Check app status
databricks apps get your-app-name
```

## Configuration

### Local Development

The app automatically detects if it's running locally and provides helpful error messages. You need to set the `SERVING_ENDPOINT` environment variable to your endpoint name (not the full URL).

**Important**: Use only the endpoint name, not the full URL. For example:
- ✅ Correct: `databricks-claude-3-7-sonnet` or `my-agent-supervisor`
- ❌ Incorrect: `https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints/databricks-claude-3-7-sonnet/invocations`

### Supported Endpoint Types

The application supports various Databricks serving endpoint types:
- `llm/v1/chat` - Standard LLM chat endpoints
- `agent/v1/chat` - Agent chat endpoints
- `agent/v2/chat` - Agent chat endpoints (v2)
- `agent/v1/supervisor` - Multi-agent supervisor endpoints
- `agent/v2/supervisor` - Multi-agent supervisor endpoints (v2)
- `agent/v1/responses` - Agent response endpoints

### Databricks Deployment

The `app.yaml` file is configured to:
- Reference the serving endpoint resource
- Set proper permissions (`CAN_QUERY`)
- Automatically inject the endpoint name via environment variables

## Project Structure

```
├── app.py                          # Main application entry point
├── app.yaml                        # Databricks app configuration
├── src/                           # Source code directory
│   ├── ui/                        # UI components
│   │   └── chatbot.py            # Modern dark-themed chatbot component
│   ├── databricks/               # Databricks integration
│   │   └── sdk_wrapper.py        # SDK wrapper utilities
│   └── cli/                      # CLI components
│       └── main.py              # CLI main module
├── scripts/                      # Utility scripts
│   ├── model_serving_utils.py   # Model serving utilities & CLI interface
│   └── demo_cli.py              # Demo CLI script
├── pyproject.toml               # Project dependencies and metadata
├── uv.lock                      # uv lock file
├── CLAUDE.md                    # Claude Code instructions
├── TROUBLESHOOTING.md           # Troubleshooting guide
└── README.md                   # This file
```

## Dependencies

All dependencies are managed through `pyproject.toml`:

- `dash==3.0.2` - Web application framework
- `dash-bootstrap-components==2.0.0` - UI components
- `mlflow>=2.21.2` - MLflow for model serving
- `python-dotenv==1.1.0` - Environment variable loading
- `databricks-sdk` - Databricks SDK
- `rich` - Rich text and beautiful formatting for CLI

## Development Commands

```bash
# Install dependencies
uv sync

# Run the app locally
uv run python app.py

# Add a new dependency
uv add package-name

# Remove a dependency
uv remove package-name

# Update dependencies
uv sync --upgrade

# Run with specific environment variables
SERVING_ENDPOINT=your-endpoint uv run python app.py
```

## CLI Utilities

The `src.cli` module provides a comprehensive CLI for testing and managing Databricks serving endpoints:

### Available Commands

```bash
# List all available serving endpoints
uv run python -m src.cli list

# Display detailed information about an endpoint
uv run python -m src.cli info my-endpoint

# Test an endpoint with a custom message
uv run python -m src.cli test my-endpoint --message "Hello, how are you?"

# Start an interactive chat session
uv run python -m src.cli chat my-endpoint

# Test with custom max tokens
uv run python -m src.cli test my-endpoint --max-tokens 200
```

### CLI Features

- **Rich UI**: Beautiful terminal interface with colors, tables, and progress indicators
- **Endpoint Validation**: Automatically checks if endpoints are supported
- **Multi-format Support**: Handles different response formats from various endpoint types
- **Interactive Chat**: Full conversation mode with chat history
- **Error Handling**: Comprehensive error messages and troubleshooting hints

### CLI Examples

```bash
# Get help for all available commands
uv run python -m src.cli --help

# List all serving endpoints in your workspace
uv run python -m src.cli list

# Get detailed information about a specific endpoint
uv run python -m src.cli info mas-84eae27f-endpoint

# Test an endpoint with a simple message
uv run python -m src.cli test mas-84eae27f-endpoint --message "What is machine learning?"

# Test with custom parameters
uv run python -m src.cli test mas-84eae27f-endpoint \
  --message "Explain Python decorators" \
  --max-tokens 500

# Start an interactive chat session
uv run python -m src.cli chat mas-84eae27f-endpoint
```

### Interactive Chat Mode

The interactive chat mode provides a full conversation experience:
- Type messages and get real-time responses
- View conversation history
- Use `/exit` to quit the chat
- Use `/clear` to clear chat history
- Use `/help` for chat commands

### Demo CLI

For quick testing, use the demo CLI script:

```bash
# Run the demo CLI (tests the CLI functionality)
uv run python scripts/demo_cli.py
```

## Troubleshooting

### Common Issues

1. **"Unable to determine serving endpoint" error**
   - Ensure `SERVING_ENDPOINT` is set to your endpoint name (not URL)
   - Check that your endpoint exists and is accessible

2. **"Endpoint Type Not Supported" error**
   - Verify your endpoint supports chat completions or is a multi-agent supervisor
   - Check the endpoint task type in Databricks UI
   - Use `uv run python -m src.cli info your-endpoint` to check compatibility

3. **Authentication issues**
   - Ensure you're logged into Databricks CLI: `databricks auth login`
   - Verify your workspace has access to the serving endpoint

### Environment Detection

The app automatically detects the environment:
- **Local**: Uses `.env` file or environment variables
- **Databricks**: Uses app.yaml resource configuration

## Contributing

1. Make your changes
2. Test locally: `uv run python app.py`
3. Test CLI utilities: `uv run python -m src.cli list`
4. Test deployment: `databricks apps deploy your-app-name --mode SNAPSHOT`
5. Commit your changes

## License

This project is licensed under the MIT License.
