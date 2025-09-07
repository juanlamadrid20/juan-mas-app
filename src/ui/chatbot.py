import dash
from dash import html, Input, Output, State, dcc, callback_context
import dash_bootstrap_components as dbc
import re
import json
from ..databricks.sdk_wrapper import query_endpoint, is_endpoint_supported

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
            # Main chat interface
            html.Div([
                # Header
                html.Div([
                    html.Div([
                        html.H3('AI Assistant', className='chat-header-title'),
                        html.Div([
                            html.Span('●', className='status-indicator', id='status-indicator'),
                            html.Span('Connected', className='status-text', id='status-text')
                        ], className='status-container')
                    ], className='chat-header-content')
                ], className='chat-header'),
                
                # Chat messages area
                html.Div([
                    html.Div(id='chat-history', className='chat-history'),
                ], className='chat-messages-container'),
                
                # Input area
                html.Div([
                    html.Div([
                        dbc.Input(
                            id='user-input', 
                            placeholder='Type a message here...', 
                            type='text',
                            className='chat-input',
                            autoComplete='off'
                        ),
                        dbc.Button(
                            html.I(className='fas fa-paper-plane'),
                            id='send-button', 
                            n_clicks=0, 
                            className='send-button',
                            disabled=False
                        ),
                    ], className='input-container-inner'),
                    
                    # Action buttons (hidden by default, can be toggled)
                    html.Div([
                        dbc.Button(
                            '🗑️ Clear', 
                            id='clear-button', 
                            n_clicks=0, 
                            className='action-button'
                        ),
                        dbc.Button(
                            '📁 Export', 
                            id='export-button', 
                            n_clicks=0, 
                            className='action-button'
                        ),
                    ], className='action-buttons', style={'display': 'none'})
                ], className='input-area'),
            ], className='main-chat-container'),
            
            # Hidden stores and components
            dcc.Store(id='assistant-trigger'),
            dcc.Store(id='chat-history-store', data=[]),
            dcc.Store(id='clear-confirmation-trigger'),
            html.Div(id='dummy-output', style={'display': 'none'}),
            html.Div(id='scroll-trigger', style={'display': 'none'}),
            html.Div(id='input-visibility-trigger', style={'display': 'none'}),
            
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
        @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css');
        
        * {
            box-sizing: border-box;
        }
        
        /* Only apply dark theme to chat container and its children */
        .main-chat-container {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a1e;
            color: #ffffff;
        }
        
        .chat-container {
            background: #1a1a1e;
            height: calc(100vh - 200px);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
            width: 100%;
        }
        
        .main-chat-container {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 200px);
            background: #1a1a1e;
            border-radius: 0;
            min-height: 0;
            max-height: calc(100vh - 200px);
        }
        
        .main-chat-container .chat-header {
            padding: 20px 24px;
            border-bottom: 1px solid #2d2d32;
            background: #1a1a1e;
            flex-shrink: 0;
        }
        
        .main-chat-container .chat-header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .main-chat-container .chat-header-title {
            font-size: 20px;
            font-weight: 600;
            color: #ffffff;
            margin: 0;
        }
        
        .main-chat-container .status-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .main-chat-container .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #22c55e;
            animation: pulse 2s infinite;
        }
        
        .main-chat-container .status-indicator.error {
            background-color: #ef4444;
        }
        
        .main-chat-container .status-text {
            font-size: 14px;
            color: #9ca3af;
            font-weight: 500;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .main-chat-container .chat-messages-container {
            flex: 1;
            overflow: hidden;
            background: #1a1a1e;
            min-height: 0;
            display: flex;
            flex-direction: column;
        }
        
        .main-chat-container .chat-history {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            scroll-behavior: smooth;
            box-sizing: border-box;
            min-height: 0;
        }
        
        .main-chat-container .chat-history::-webkit-scrollbar {
            width: 6px;
        }
        
        .main-chat-container .chat-history::-webkit-scrollbar-track {
            background: transparent;
        }
        
        .main-chat-container .chat-history::-webkit-scrollbar-thumb {
            background: #3f3f46;
            border-radius: 3px;
        }
        
        .main-chat-container .chat-history::-webkit-scrollbar-thumb:hover {
            background: #52525b;
        }
        
        .main-chat-container .message-container {
            display: flex;
            margin-bottom: 16px;
            animation: fadeInUp 0.3s ease-out;
        }
        
        .main-chat-container .user-container {
            justify-content: flex-end;
        }
        
        .main-chat-container .assistant-container {
            justify-content: flex-start;
        }
        
        .main-chat-container .chat-message {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 16px;
            font-size: 14px;
            line-height: 1.4;
            word-wrap: break-word;
            position: relative;
        }
        
        .main-chat-container .user-message {
            background: #3b82f6;
            color: white;
            border-bottom-right-radius: 4px;
        }
        
        .main-chat-container .assistant-message {
            background: #2d2d32;
            color: #ffffff;
            border-bottom-left-radius: 4px;
        }
        
        .main-chat-container .typing-message {
            background: #2d2d32;
            color: #9ca3af;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 120px;
        }
        
        .main-chat-container .typing-animation {
            display: flex;
            gap: 4px;
        }
        
        .main-chat-container .typing-dot {
            width: 6px;
            height: 6px;
            background-color: #9ca3af;
            border-radius: 50%;
            animation: typing-bounce 1.4s infinite ease-in-out;
        }
        
        .main-chat-container .typing-dot:nth-child(1) { animation-delay: 0s; }
        .main-chat-container .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .main-chat-container .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        
        .main-chat-container .typing-text {
            font-size: 13px;
            color: #9ca3af;
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
        
        .main-chat-container .message-content {
            line-height: 1.6;
        }
        
        .main-chat-container .chat-paragraph {
            margin: 0 0 8px 0;
            font-size: 15px;
        }
        
        .main-chat-container .chat-bullet, .main-chat-container .chat-numbered {
            margin: 4px 0;
            padding-left: 8px;
        }
        
        .main-chat-container .chat-table {
            margin: 12px 0;
            font-size: 14px;
        }
        
        .main-chat-container .input-area {
            padding: 20px 24px;
            background: #1a1a1e;
            border-top: 1px solid #2d2d32;
            flex-shrink: 0;
            position: relative;
            z-index: 100;
        }
        
        .main-chat-container .input-container-inner {
            display: flex;
            align-items: center;
            gap: 12px;
            background: #2d2d32;
            border-radius: 24px;
            padding: 8px 8px 8px 20px;
        }
        
        .main-chat-container .chat-input {
            flex: 1;
            background: transparent;
            border: none;
            color: #ffffff;
            font-size: 14px;
            padding: 8px 0;
            outline: none;
        }
        
        .main-chat-container .chat-input::placeholder {
            color: #9ca3af;
        }
        
        .main-chat-container .chat-input:focus {
            outline: none;
        }
        
        .main-chat-container .send-button {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #3b82f6;
            border: none;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .main-chat-container .send-button:hover:not(:disabled) {
            background: #2563eb;
            transform: scale(1.05);
        }
        
        .main-chat-container .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .main-chat-container .send-button i {
            font-size: 14px;
        }
        
        .action-buttons {
            display: flex;
            gap: 12px;
            justify-content: center;
            margin-top: 12px;
        }
        
        .action-button {
            background: #2d2d32;
            color: #9ca3af;
            border: 1px solid #3f3f46;
            border-radius: 16px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .action-button:hover {
            background: #3f3f46;
            color: #ffffff;
        }
        
        .main-chat-container .input-group {
            flex-wrap: nowrap;
        }
        
        /* Responsive design for chat container only */
        @media (max-width: 768px) {
            .main-chat-container .chat-header, .main-chat-container .input-area {
                padding: 16px 20px;
            }
            
            .main-chat-container .chat-history {
                padding: 16px 20px;
            }
            
            .main-chat-container .chat-header-title {
                font-size: 18px;
            }
            
            .main-chat-container .chat-message {
                max-width: 85%;
                padding: 10px 14px;
                font-size: 14px;
            }
            
            .main-chat-container .action-buttons {
                flex-direction: row;
                gap: 8px;
            }
        }
        
        /* Modal styling - scoped to chat modals only */
        .main-chat-container .modal-content {
            background: #2d2d32;
            border: 1px solid #3f3f46;
            border-radius: 12px;
            color: #ffffff;
        }
        
        .main-chat-container .modal-header {
            border-bottom: 1px solid #3f3f46;
            padding: 20px 24px 16px;
        }
        
        .main-chat-container .modal-body {
            padding: 16px 24px;
        }
        
        .main-chat-container .modal-footer {
            border-top: 1px solid #3f3f46;
            padding: 16px 24px 20px;
        }
        
        .main-chat-container .modal-title {
            color: #ffffff;
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
        
        # Input visibility callback - ensures input is visible on page load
        self.app.clientside_callback(
            """
            function(_) {
                setTimeout(function() {
                    var userInput = document.getElementById('user-input');
                    var inputArea = document.querySelector('.input-area');
                    if(userInput && inputArea) {
                        // Ensure input area is visible
                        inputArea.scrollIntoView({ behavior: 'smooth', block: 'end' });
                        // Focus the input
                        userInput.focus();
                    }
                }, 100);
                return '';
            }
            """,
            Output('input-visibility-trigger', 'children'),
            Input('user-input', 'id'),
            prevent_initial_call=False
        )
