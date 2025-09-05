import os
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback
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

# Get dashboard URLs from environment variables
dashboard_urls = {
    'dashboard_1': os.getenv('DASHBOARD_1_URL'),
    'dashboard_2': os.getenv('DASHBOARD_2_URL'),
    'dashboard_3': os.getenv('DASHBOARD_3_URL'),
    'dashboard_4': os.getenv('DASHBOARD_4_URL')
}

# Filter out None and empty values and create dashboard configs
dashboard_configs = []
for i, (key, url) in enumerate(dashboard_urls.items(), 1):
    if url and url.strip():  # Check for both None and empty strings
        dashboard_configs.append({
            'id': f'dashboard_{i}',
            'label': f'Dashboard {i}',
            'url': url
        })

# Initialize the Dash app with a clean theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

def create_dashboard_iframe(dashboard_url, dashboard_id):
    """Create an iframe component for dashboard embedding"""
    return html.Div([
        html.Iframe(
            src=dashboard_url,
            style={
                'width': '100%',
                'height': 'calc(100vh - 200px)',
                'border': 'none',
                'borderRadius': '8px',
                'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'
            },
            allow='fullscreen',
            id=f'iframe-{dashboard_id}'
        )
    ], id=f'iframe-container-{dashboard_id}')

def create_setup_instructions():
    """Create setup instructions when dashboard URLs are missing"""
    return dbc.Alert([
        html.H5("Dashboard Setup Required", className="alert-heading mb-3"),
        html.P("To view dashboards, please configure the following environment variables in your app.yaml:", 
               className="mb-3"),
        html.Pre([
            "env:\n",
            "  - name: \"DASHBOARD_1_URL\"\n",
            "    value: \"https://your-workspace.cloud.databricks.com/embed/dashboardsv3/your-dashboard-id\"\n",
            "  - name: \"DASHBOARD_2_URL\"\n",
            "    value: \"https://your-workspace.cloud.databricks.com/embed/dashboardsv3/your-dashboard-id\"\n",
            "  - name: \"DASHBOARD_3_URL\"\n",
            "    value: \"https://your-workspace.cloud.databricks.com/embed/dashboardsv3/your-dashboard-id\"\n",
            "  - name: \"DASHBOARD_4_URL\"\n",
            "    value: \"https://your-workspace.cloud.databricks.com/embed/dashboardsv3/your-dashboard-id\""
        ], className="bg-light p-3 rounded mb-3"),
        html.P([
            "Replace the URLs with your actual Databricks dashboard embed URLs. ",
            "You can find these URLs in your Databricks workspace under ",
            html.Strong("Dashboards > Share > Embed"),
            "."
        ], className="mb-0")
    ], color="info", className="mt-4")

def create_error_fallback():
    """Create error fallback UI for failed dashboard loads"""
    return dbc.Alert([
        html.H5("Dashboard Loading Error", className="alert-heading mb-3"),
        html.P("Unable to load the dashboard. This could be due to:", className="mb-2"),
        html.Ul([
            html.Li("Network connectivity issues"),
            html.Li("Invalid dashboard URL"),
            html.Li("Dashboard permissions"),
            html.Li("Dashboard is temporarily unavailable")
        ], className="mb-3"),
        dbc.Button("Retry", color="primary", className="me-2", id="retry-btn"),
        dbc.Button("Refresh Page", color="secondary", id="refresh-btn")
    ], color="warning", className="mt-4")

# Define the app layout based on endpoint support and dashboard availability
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
    # Create the chatbot component
    chatbot = DatabricksChatbot(app=app, endpoint_name=serving_endpoint, height='600px')
    
    # Create tab content based on available dashboards
    tab_content = []
    
    # Add chatbot tab
    tab_content.append(
        dbc.Tab(
            label="AI Chat",
            tab_id="chat-tab",
            children=[
                dbc.Container([
                    dbc.Row([
                        dbc.Col(chatbot.layout, width={'size': 8, 'offset': 2})
                    ])
                ], fluid=True)
            ]
        )
    )
    
    # Add dashboard tabs
    if dashboard_configs:
        for config in dashboard_configs:
            tab_content.append(
                dbc.Tab(
                    label=config['label'],
                    tab_id=config['id'],
                    children=[
                        dbc.Container([
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        dbc.Spinner(
                                            create_dashboard_iframe(config['url'], config['id']),
                                            color="primary",
                                            spinner_style={"width": "3rem", "height": "3rem"}
                                        )
                                    ], id=f"dashboard-content-{config['id']}")
                                ], width=12)
                            ])
                        ], fluid=True, style={'padding': '20px'})
                    ]
                )
            )
    else:
        # Add setup instructions tab if no dashboards are configured
        tab_content.append(
            dbc.Tab(
                label="Dashboards",
                tab_id="dashboard-setup",
                children=[
                    dbc.Container([
                        dbc.Row([
                            dbc.Col([
                                html.H2('Databricks Dashboards', className='mb-4'),
                                create_setup_instructions()
                            ], width={'size': 10, 'offset': 1})
                        ])
                    ], fluid=True)
                ]
            )
        )
    
    # Create the main layout with tabs
    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1('Databricks AI & Analytics Hub', className='text-center mb-4'),
                dbc.Tabs(
                    id="main-tabs",
                    active_tab="chat-tab",
                    children=tab_content,
                    className="mb-4"
                ),
                html.Div(id="tab-content")
            ], width=12)
        ])
    ], fluid=True, style={'padding': '20px'})

# Callback for handling tab content updates
@callback(
    Output('tab-content', 'children'),
    [Input('main-tabs', 'active_tab')]
)
def update_tab_content(active_tab):
    """Update tab content when switching tabs"""
    return ""

if __name__ == '__main__':
    app.run(debug=True)
