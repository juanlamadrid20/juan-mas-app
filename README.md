# Databricks Chatbot App

A Databricks chatbot application that works seamlessly in both local development and Databricks deployment environments.

## Features

- 🤖 Interactive chatbot interface using Dash
- 🔄 Seamless local development and Databricks deployment
- 🎨 Modern, responsive UI with Databricks branding
- ⚡ Real-time chat with typing indicators
- 🔒 Secure endpoint access with proper permissions

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Databricks workspace access
- A Databricks serving endpoint (e.g., Claude 3.5 Sonnet)

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

# Option 2: Create a .env file
echo "SERVING_ENDPOINT=databricks-claude-3-7-sonnet" > .env
```

Run the application locally:

```bash
uv run python app.py
```

The app will be available at `http://localhost:8050`

### 3. Databricks Deployment

Deploy to Databricks as an app:

```bash
# Package the app
uv run databricks app bundle

# Deploy to your workspace
uv run databricks app deploy
```

## Configuration

### Local Development

The app automatically detects if it's running locally and provides helpful error messages. You need to set the `SERVING_ENDPOINT` environment variable to your endpoint name (not the full URL).

**Important**: Use only the endpoint name, not the full URL. For example:
- ✅ Correct: `databricks-claude-3-7-sonnet`
- ❌ Incorrect: `https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints/databricks-claude-3-7-sonnet/invocations`

### Databricks Deployment

The `app.yaml` file is configured to:
- Reference the serving endpoint resource
- Set proper permissions (`CAN_QUERY`)
- Automatically inject the endpoint name via environment variables

## Project Structure

```
├── app.py                 # Main application entry point
├── app.yaml              # Databricks app configuration
├── DatabricksChatbot.py  # Chatbot component implementation
├── model_serving_utils.py # Model serving utilities
├── pyproject.toml        # Project dependencies and metadata
├── requirements.txt      # Legacy requirements (for reference)
├── uv.lock              # uv lock file
└── README.md            # This file
```

## Dependencies

All dependencies are managed through `pyproject.toml`:

- `dash==3.0.2` - Web application framework
- `dash-bootstrap-components==2.0.0` - UI components
- `mlflow>=2.21.2` - MLflow for model serving
- `python-dotenv==1.1.0` - Environment variable loading
- `databricks-sdk` - Databricks SDK

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

## Troubleshooting

### Common Issues

1. **"Unable to determine serving endpoint" error**
   - Ensure `SERVING_ENDPOINT` is set to your endpoint name (not URL)
   - Check that your endpoint exists and is accessible

2. **"Endpoint Type Not Supported" error**
   - Verify your endpoint supports chat completions
   - Check the endpoint task type in Databricks UI

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
3. Test deployment: `uv run databricks app bundle && uv run databricks app deploy`
4. Commit your changes

## License

This project is licensed under the MIT License.
