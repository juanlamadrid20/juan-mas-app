import os
import dash
import dash_bootstrap_components as dbc
from dash import html
from DatabricksChatbot import DatabricksChatbot
from model_serving_utils import is_endpoint_supported
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# Determine if we're running locally or on Databricks
is_databricks_env = os.getenv('DATABRICKS_RUNTIME_VERSION') is not None

# Get serving endpoint configuration
serving_endpoint = os.getenv('SERVING_ENDPOINT')

if not serving_endpoint:
    if is_databricks_env:
        error_msg = (
            "Unable to determine serving endpoint for Databricks deployment. "
            "Ensure your app.yaml includes a serving endpoint resource named 'serving_endpoint' "
            "with CAN_QUERY permissions. See: "
            "https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app#deploy-the-databricks-app"
        )
    else:
        error_msg = (
            "Unable to determine serving endpoint for local development. "
            "Set the SERVING_ENDPOINT environment variable to your endpoint name (e.g., 'databricks-claude-3-7-sonnet'). "
            "You can also create a .env file with: SERVING_ENDPOINT=your-endpoint-name"
        )
    raise AssertionError(error_msg)

# Check if the endpoint is supported
endpoint_supported = is_endpoint_supported(serving_endpoint)

# Initialize the Dash app with a clean theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# Define the app layout based on endpoint support
if not endpoint_supported:
    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2('Chat with Databricks AI', className='mb-3'),
                dbc.Alert([
                    html.H5("Endpoint Type Not Supported", className="alert-heading mb-3"),
                    html.P(f"The endpoint '{serving_endpoint}' is not compatible with this basic chatbot template.", 
                           className="mb-2"),
                    html.P("This template only supports chat completions-compatible endpoints.", 
                           className="mb-3"),
                    html.Div([
                        html.P([
                            "For a richer chatbot template that supports all conversational endpoints on Databricks, ",
                            "please visit the ",
                            html.A("Databricks documentation", 
                                   href="https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app",
                                   target="_blank",
                                   className="alert-link"),
                            "."
                        ], className="mb-0")
                    ])
                ], color="info", className="mt-4")
            ], width={'size': 8, 'offset': 2})
        ])
    ], fluid=True)
else:
    # Create the chatbot component with a specified height
    chatbot = DatabricksChatbot(app=app, endpoint_name=serving_endpoint, height='600px')
    
    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col(chatbot.layout, width={'size': 8, 'offset': 2})
        ])
    ], fluid=True)

if __name__ == '__main__':
    app.run(debug=True)
