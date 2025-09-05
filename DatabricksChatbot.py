import dash
from dash import html, Input, Output, State, dcc, callback_context
import dash_bootstrap_components as dbc
import re
import json
from model_serving_utils import query_endpoint, is_endpoint_supported

class DatabricksChatbot:
    def __init__(self, app, endpoint_name, height='600px'):
        self.app = app
        self.endpoint_name = endpoint_name
        self.height = height
        self.layout = self._create_layout()
        self._create_callbacks()
        self._add_custom_css()

    def _create_layout(self):
        return html.Div([
            # Header with title and status
            html.Div([
                html.H2('AI Assistant', className='chat-title mb-2'),
                html.Div([
                    html.Span('●', className='status-indicator', id='status-indicator'),
                    html.Span('Connected', className='status-text', id='status-text')
                ], className='status-container mb-3')
            ], className='chat-header'),
            
            # Chat container
            dbc.Card([
                dbc.CardBody([
                    html.Div(id='chat-history', className='chat-history'),
                ], className='d-flex flex-column chat-body')
            ], className='chat-card mb-3'),
            
            # Input area
            html.Div([
                dbc.InputGroup([
                    dbc.Input(
                        id='user-input', 
                        placeholder='Ask me anything...', 
                        type='text',
                        className='chat-input',
                        autoComplete='off'
                    ),
                    dbc.Button(
                        'Send', 
                        id='send-button', 
                        color='primary', 
                        n_clicks=0, 
                        className='send-button',
                        disabled=False
                    ),
                ], className='input-group mb-2'),
                
                # Action buttons
                html.Div([
                    dbc.Button(
                        'Clear Chat', 
                        id='clear-button', 
                        color='outline-secondary', 
                        size='sm',
                        n_clicks=0, 
                        className='action-button'
                    ),
                    dbc.Button(
                        'Export Chat', 
                        id='export-button', 
                        color='outline-info', 
                        size='sm',
                        n_clicks=0, 
                        className='action-button'
                    ),
                ], className='action-buttons')
            ], className='input-container'),
            
            # Hidden stores and components
            dcc.Store(id='assistant-trigger'),
            dcc.Store(id='chat-history-store', data=[]),
            dcc.Store(id='clear-confirmation-trigger'),
            html.Div(id='dummy-output', style={'display': 'none'}),
            html.Div(id='scroll-trigger', style={'display': 'none'}),
            
            # Clear confirmation modal
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Clear Chat History")),
                dbc.ModalBody([
                    html.P("Are you sure you want to clear all chat history? This action cannot be undone."),
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancel", id="clear-cancel", className="ms-auto", n_clicks=0),
                    dbc.Button("Clear Chat", id="clear-confirm", color="danger", n_clicks=0),
                ]),
            ], id="clear-modal", is_open=False),
            
        ], className='d-flex flex-column chat-container')

    def _create_callbacks(self):
        # User input callback - handles user input and triggers assistant response
        @self.app.callback(
            Output('chat-history-store', 'data'),
            Output('chat-history', 'children'),
            Output('user-input', 'value'),
            Output('assistant-trigger', 'data'),
            Output('send-button', 'disabled'),
            Output('status-indicator', 'className'),
            Output('status-text', 'children'),
            Input('send-button', 'n_clicks'),
            Input('user-input', 'n_submit'),
            Input('clear-confirm', 'n_clicks'),
            State('user-input', 'value'),
            State('chat-history-store', 'data'),
            prevent_initial_call=True
        )
        def handle_user_input(send_clicks, user_submit, clear_clicks, user_input, chat_history):
            ctx = callback_context
            if not ctx.triggered:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            # Handle clear chat
            if trigger_id == 'clear-confirm' and clear_clicks:
                return [], [], dash.no_update, dash.no_update, dash.no_update, 'status-indicator connected', 'Connected'
            
            # Handle user input
            if trigger_id in ['send-button', 'user-input'] and (send_clicks or user_submit):
                if not user_input or not user_input.strip():
                    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

                chat_history = chat_history or []
                chat_history.append({'role': 'user', 'content': user_input.strip()})
                chat_display = self._format_chat_display(chat_history)
                chat_display.append(self._create_typing_indicator())

                return chat_history, chat_display, '', {'trigger': True}, True, 'status-indicator connected', 'Connected'
            
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Assistant response callback - handles AI responses
        @self.app.callback(
            Output('chat-history-store', 'data', allow_duplicate=True),
            Output('chat-history', 'children', allow_duplicate=True),
            Output('send-button', 'disabled', allow_duplicate=True),
            Output('status-indicator', 'className', allow_duplicate=True),
            Output('status-text', 'children', allow_duplicate=True),
            Input('assistant-trigger', 'data'),
            State('chat-history-store', 'data'),
            prevent_initial_call=True
        )
        def handle_assistant_response(trigger, chat_history):
            if not trigger or not trigger.get('trigger'):
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            chat_history = chat_history or []
            if (not chat_history or not isinstance(chat_history[-1], dict)
                    or 'role' not in chat_history[-1]
                    or chat_history[-1]['role'] != 'user'):
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

            try:
                assistant_response = self._call_model_endpoint(chat_history)
                chat_history.append({
                    'role': 'assistant',
                    'content': assistant_response
                })
                status_class = 'status-indicator connected'
                status_text = 'Connected'
            except Exception as e:
                error_message = f'Error: {str(e)}'
                print(f'Error calling model endpoint: {error_message}')
                chat_history.append({
                    'role': 'assistant',
                    'content': error_message
                })
                status_class = 'status-indicator error'
                status_text = 'Error'

            chat_display = self._format_chat_display(chat_history)
            return chat_history, chat_display, False, status_class, status_text

        # Clear modal callback
        @self.app.callback(
            Output('clear-modal', 'is_open'),
            Input('clear-button', 'n_clicks'),
            Input('clear-cancel', 'n_clicks'),
            Input('clear-confirm', 'n_clicks'),
            prevent_initial_call=True
        )
        def toggle_clear_modal(clear_clicks, cancel_clicks, confirm_clicks):
            ctx = callback_context
            if not ctx.triggered:
                return False
            
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if trigger_id == 'clear-button':
                return True
            elif trigger_id in ['clear-cancel', 'clear-confirm']:
                return False
            return False

        # Export chat callback
        @self.app.callback(
            Output('dummy-output', 'children'),
            Input('export-button', 'n_clicks'),
            State('chat-history-store', 'data'),
            prevent_initial_call=True
        )
        def export_chat(export_clicks, chat_history):
            if export_clicks and chat_history:
                export_content = self._create_export_content(chat_history)
                print("Export content:")
                print(export_content)
                return html.Div("Chat exported to console (check server logs)", 
                              style={'color': 'green', 'fontSize': '12px', 'textAlign': 'center'})
            return dash.no_update

    def _call_model_endpoint(self, messages, max_tokens=512):
        """Enhanced endpoint calling with support for multi-agent responses"""
        try:
            print(f'Calling model endpoint: {self.endpoint_name}')
            response = query_endpoint(self.endpoint_name, messages, max_tokens)
            
            # Handle different response formats from multi-agent supervisors
            if isinstance(response, dict):
                if 'messages' in response:
                    # Extract content from the last assistant message
                    assistant_messages = [msg for msg in response['messages'] if msg.get('role') == 'assistant']
                    if assistant_messages:
                        return assistant_messages[-1]['content']
                    else:
                        # Fallback: return the first message content
                        if response['messages']:
                            return response['messages'][0].get('content', str(response['messages'][0]))
                elif 'content' in response:
                    return response['content']
                elif 'choices' in response:
                    return response['choices'][0]['message']['content']
            
            return str(response)
        except Exception as e:
            print(f'Error calling model endpoint: {str(e)}')
            raise

    def _format_multi_agent_response(self, messages):
        """Format multi-agent supervisor responses"""
        if not messages:
            return "No response received from agents."
        
        formatted_response = []
        for i, msg in enumerate(messages):
            if isinstance(msg, dict) and 'content' in msg:
                agent_name = msg.get('agent', f'Agent {i+1}')
                content = msg['content']
                formatted_response.append(f"**{agent_name}:**\n{content}")
        
        return "\n\n".join(formatted_response)

    def _format_chat_display(self, chat_history):
        """Enhanced chat display with advanced formatting"""
        formatted_messages = []
        
        for msg in chat_history:
            if isinstance(msg, dict) and 'role' in msg:
                role = msg['role']
                content = msg['content']
                
                # Format the content with markdown support
                formatted_content = self._format_message_content(content)
                
                message_div = html.Div([
                    html.Div(
                        formatted_content,
                        className=f"chat-message {role}-message"
                    )
                ], className=f"message-container {role}-container")
                
                formatted_messages.append(message_div)
        
        return formatted_messages

    def _format_message_content(self, content):
        """Format message content with markdown-style formatting"""
        if not content:
            return html.Span("(empty message)")
        
        # Split content into lines for processing
        lines = content.split('\n')
        formatted_elements = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_elements.append(html.Br())
                continue
            
            # Check for table format (basic detection)
            if '|' in line and line.count('|') >= 2:
                formatted_elements.append(self._create_table_from_line(line))
            # Check for bullet points
            elif line.startswith('- ') or line.startswith('* '):
                formatted_elements.append(html.Li(line[2:], className='chat-bullet'))
            # Check for numbered lists
            elif re.match(r'^\d+\.\s', line):
                formatted_elements.append(html.Li(line[3:], className='chat-numbered'))
            # Check for bold text
            elif '**' in line:
                formatted_elements.append(self._format_bold_text(line))
            # Check for italic text
            elif '*' in line:
                formatted_elements.append(self._format_italic_text(line))
            # Regular paragraph
            else:
                formatted_elements.append(html.P(line, className='chat-paragraph'))
        
        return html.Div(formatted_elements, className='message-content')

    def _create_table_from_line(self, line):
        """Create a Bootstrap table from a pipe-separated line"""
        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
        if len(cells) < 2:
            return html.P(line, className='chat-paragraph')
        
        table_cells = [html.Td(cell) for cell in cells]
        return dbc.Table([
            html.Tr(table_cells)
        ], size='sm', striped=True, bordered=True, hover=True, className='chat-table')

    def _format_bold_text(self, text):
        """Format bold text (**text**)"""
        parts = text.split('**')
        elements = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Odd indices are bold text
                elements.append(html.Strong(part))
            else:
                elements.append(html.Span(part))
        return html.Span(elements, className='chat-paragraph')

    def _format_italic_text(self, text):
        """Format italic text (*text*)"""
        parts = text.split('*')
        elements = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Odd indices are italic text
                elements.append(html.Em(part))
            else:
                elements.append(html.Span(part))
        return html.Span(elements, className='chat-paragraph')

    def _create_typing_indicator(self):
        """Enhanced typing indicator"""
        return html.Div([
            html.Div([
                html.Div([
                    html.Div(className='typing-dot'),
                    html.Div(className='typing-dot'),
                    html.Div(className='typing-dot')
                ], className='typing-animation'),
                html.Span('AI is thinking...', className='typing-text')
            ], className='chat-message assistant-message typing-message')
        ], className='message-container assistant-container')

    def _create_export_content(self, chat_history):
        """Create export content for chat history"""
        export_lines = ["Chat History Export", "=" * 50, ""]
        
        for msg in chat_history:
            if isinstance(msg, dict) and 'role' in msg:
                role = msg['role'].title()
                content = msg['content']
                export_lines.append(f"{role}: {content}")
                export_lines.append("")
        
        return "\n".join(export_lines)

    def _add_custom_css(self):
        custom_css = '''
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }
        
        .chat-container {
            max-width: 900px;
            margin: 20px auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            height: calc(100vh - 40px);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-header {
            padding: 20px 30px 10px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            background: rgba(255, 255, 255, 0.8);
        }
        
        .chat-title {
            font-size: 28px;
            font-weight: 700;
            color: #1a1a1a;
            margin: 0;
            text-align: center;
        }
        
        .status-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #10b981;
            animation: pulse 2s infinite;
        }
        
        .status-indicator.error {
            background-color: #ef4444;
        }
        
        .status-text {
            font-size: 14px;
            color: #6b7280;
            font-weight: 500;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .chat-card {
            border: none;
            background: transparent;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            margin: 0;
        }
        
        .chat-body {
            flex-grow: 1;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .chat-history {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px 30px;
            scroll-behavior: smooth;
        }
        
        .chat-history::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-history::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.05);
            border-radius: 3px;
        }
        
        .chat-history::-webkit-scrollbar-thumb {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 3px;
        }
        
        .message-container {
            display: flex;
            margin-bottom: 20px;
            animation: fadeInUp 0.3s ease-out;
        }
        
        .user-container {
            justify-content: flex-end;
        }
        
        .assistant-container {
            justify-content: flex-start;
        }
        
        .chat-message {
            max-width: 75%;
            padding: 16px 20px;
            border-radius: 18px;
            font-size: 15px;
            line-height: 1.5;
            word-wrap: break-word;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .user-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 6px;
        }
        
        .assistant-message {
            background: white;
            color: #1a1a1a;
            border: 1px solid rgba(0, 0, 0, 0.05);
            border-bottom-left-radius: 6px;
        }
        
        .typing-message {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(0, 0, 0, 0.05);
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 120px;
        }
        
        .typing-animation {
            display: flex;
            gap: 4px;
        }
        
        .typing-dot {
            width: 6px;
            height: 6px;
            background-color: #667eea;
            border-radius: 50%;
            animation: typing-bounce 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(1) { animation-delay: 0s; }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        
        .typing-text {
            font-size: 13px;
            color: #6b7280;
            font-style: italic;
        }
        
        @keyframes typing-bounce {
            0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message-content {
            line-height: 1.6;
        }
        
        .chat-paragraph {
            margin: 0 0 8px 0;
            font-size: 15px;
        }
        
        .chat-bullet, .chat-numbered {
            margin: 4px 0;
            padding-left: 8px;
        }
        
        .chat-table {
            margin: 12px 0;
            font-size: 14px;
        }
        
        .input-container {
            padding: 20px 30px;
            background: rgba(255, 255, 255, 0.8);
            border-top: 1px solid rgba(0, 0, 0, 0.05);
        }
        
        .chat-input {
            border-radius: 25px;
            border: 2px solid rgba(0, 0, 0, 0.1);
            padding: 12px 20px;
            font-size: 15px;
            transition: all 0.2s ease;
        }
        
        .chat-input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            outline: none;
        }
        
        .send-button {
            border-radius: 25px;
            padding: 12px 24px;
            font-weight: 600;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            transition: all 0.2s ease;
        }
        
        .send-button:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        
        .send-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .action-buttons {
            display: flex;
            gap: 12px;
            justify-content: center;
            margin-top: 12px;
        }
        
        .action-button {
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .action-button:hover {
            transform: translateY(-1px);
        }
        
        .input-group {
            flex-wrap: nowrap;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .chat-container {
                margin: 10px;
                height: calc(100vh - 20px);
                border-radius: 15px;
            }
            
            .chat-header, .input-container {
                padding: 15px 20px;
            }
            
            .chat-history {
                padding: 15px 20px;
            }
            
            .chat-title {
                font-size: 24px;
            }
            
            .chat-message {
                max-width: 85%;
                padding: 14px 16px;
                font-size: 14px;
            }
            
            .action-buttons {
                flex-direction: column;
                gap: 8px;
            }
        }
        
        /* Modal styling */
        .modal-content {
            border-radius: 15px;
            border: none;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
        }
        
        .modal-header {
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            padding: 20px 25px 15px;
        }
        
        .modal-body {
            padding: 20px 25px;
        }
        
        .modal-footer {
            border-top: 1px solid rgba(0, 0, 0, 0.05);
            padding: 15px 25px 20px;
        }
        '''
        
        self.app.index_string = self.app.index_string.replace(
            '</head>',
            f'<style>{custom_css}</style></head>'
        )

        # Auto-scroll callback
        self.app.clientside_callback(
            """
            function(children) {
                var chatHistory = document.getElementById('chat-history');
                if(chatHistory) {
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                }
                return '';
            }
            """,
            Output('scroll-trigger', 'children'),
            Input('chat-history', 'children'),
            prevent_initial_call=True
        )
