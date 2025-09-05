from mlflow.deployments import get_deploy_client
from databricks.sdk import WorkspaceClient
import argparse
import sys
import json
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.text import Text
from rich import print as rprint

def _get_endpoint_task_type(endpoint_name: str) -> str:
    """Get the task type of a serving endpoint."""
    w = WorkspaceClient()
    ep = w.serving_endpoints.get(endpoint_name)
    return ep.task

def is_endpoint_supported(endpoint_name: str) -> bool:
    """Check if the endpoint has a supported task type."""
    task_type = _get_endpoint_task_type(endpoint_name)
    supported_task_types = [
        "agent/v1/chat", 
        "agent/v2/chat", 
        "llm/v1/chat",
        "agent/v1/supervisor",  # Multi-agent supervisor endpoints
        "agent/v2/supervisor",
        "agent/v1/responses"    # Agent response endpoints
    ]
    return task_type in supported_task_types

def _validate_endpoint_task_type(endpoint_name: str) -> None:
    """Validate that the endpoint has a supported task type."""
    if not is_endpoint_supported(endpoint_name):
        raise Exception(
            f"Detected unsupported endpoint type for this basic chatbot template. "
            f"This chatbot template only supports chat completions-compatible endpoints. "
            f"For a richer chatbot template with support for all conversational endpoints on Databricks, "
            f"see https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app"
        )

def _query_endpoint(endpoint_name: str, messages: list[dict[str, str]], max_tokens) -> dict:
    """Enhanced endpoint calling with support for multi-agent supervisors."""
    _validate_endpoint_task_type(endpoint_name)
    
    try:
        # Get the endpoint task type to determine the appropriate input format
        task_type = _get_endpoint_task_type(endpoint_name)
        
        # Prepare inputs based on endpoint type
        if task_type in ["agent/v1/supervisor", "agent/v2/supervisor"]:
            # Multi-agent supervisor endpoints
            inputs = {
                'messages': messages,
                'max_tokens': max_tokens,
                'stream': False  # Disable streaming for better compatibility
            }
        elif task_type == "agent/v1/responses":
            # Agent response endpoints - expect 'input' field instead of 'messages'
            inputs = {
                'input': messages,
                'max_output_tokens': max_tokens,
                'stream': False
            }
        else:
            # Standard chat endpoints
            inputs = {
                'messages': messages,
                'max_tokens': max_tokens
            }
        
        res = get_deploy_client('databricks').predict(
            endpoint=endpoint_name,
            inputs=inputs,
        )
        
        # Handle different response formats
        if isinstance(res, dict):
            if "messages" in res:
                return res
            elif "choices" in res:
                return {"messages": [res["choices"][0]["message"]]}
            elif "content" in res:
                return res
            elif "output" in res and isinstance(res["output"], list):
                # Handle agent/v1/responses format
                output_messages = []
                for output_item in res["output"]:
                    if isinstance(output_item, dict) and "content" in output_item:
                        content_list = output_item["content"]
                        if isinstance(content_list, list) and len(content_list) > 0:
                            # Extract text content from the first content item
                            first_content = content_list[0]
                            if isinstance(first_content, dict) and "text" in first_content:
                                output_messages.append({
                                    "role": output_item.get("role", "assistant"),
                                    "content": first_content["text"]
                                })
                if output_messages:
                    return {"messages": output_messages}
                else:
                    return {"content": str(res)}
            else:
                # Return the full response for multi-agent supervisors
                return res
        else:
            # Handle non-dict responses
            return {"content": str(res)}
            
    except Exception as e:
        print(f"Error calling endpoint {endpoint_name}: {str(e)}")
        raise Exception(f"Failed to call endpoint {endpoint_name}: {str(e)}")

def query_endpoint(endpoint_name, messages, max_tokens):
    """Enhanced query endpoint that returns the full response for multi-agent support."""
    return _query_endpoint(endpoint_name, messages, max_tokens)


# CLI Interface using Rich
console = Console()

def display_endpoint_info(endpoint_name: str) -> None:
    """Display detailed information about an endpoint."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching endpoint information...", total=None)
            
            w = WorkspaceClient()
            ep = w.serving_endpoints.get(endpoint_name)
            
            # Create info table
            table = Table(title=f"Endpoint: {endpoint_name}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Name", ep.name)
            table.add_row("Task Type", ep.task)
            table.add_row("Status", str(ep.state))
            table.add_row("Creation Time", str(ep.creation_timestamp))
            table.add_row("Last Updated", str(ep.last_updated_timestamp))
            
            if hasattr(ep, 'config') and ep.config:
                try:
                    config_str = json.dumps(ep.config, indent=2, default=str)
                    table.add_row("Config", config_str)
                except:
                    table.add_row("Config", str(ep.config))
            
            console.print(table)
            
            # Check if supported
            supported = is_endpoint_supported(endpoint_name)
            status_color = "green" if supported else "red"
            status_text = "✅ Supported" if supported else "❌ Not Supported"
            
            console.print(f"\n[bold {status_color}]{status_text}[/bold {status_color}]")
            
            if not supported:
                console.print("\n[yellow]This endpoint type is not supported by the chatbot template.[/yellow]")
                console.print("Supported types: agent/v1/chat, agent/v2/chat, llm/v1/chat, agent/v1/supervisor, agent/v2/supervisor, agent/v1/responses")
                
    except Exception as e:
        console.print(f"[red]Error fetching endpoint information: {e}[/red]")

def test_endpoint_query(endpoint_name: str, message: str = None, max_tokens: int = 100) -> None:
    """Test an endpoint with a query."""
    try:
        if not message:
            message = Prompt.ask("Enter your test message", default="Hello, can you hear me?")
        
        test_messages = [{'role': 'user', 'content': message}]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing endpoint query...", total=None)
            
            response = query_endpoint(endpoint_name, test_messages, max_tokens)
            
        # Display response
        console.print("\n[bold green]✅ Query successful![/bold green]")
        
        # Format and display response
        if isinstance(response, dict):
            if 'messages' in response:
                for msg in response['messages']:
                    role = msg.get('role', 'assistant')
                    content = msg.get('content', '')
                    
                    panel_title = f"{role.title()} Response"
                    panel_color = "blue" if role == "user" else "green"
                    
                    console.print(Panel(content, title=panel_title, border_style=panel_color))
            elif 'content' in response:
                console.print(Panel(response['content'], title="Response", border_style="green"))
            else:
                # Display raw response
                response_json = json.dumps(response, indent=2)
                syntax = Syntax(response_json, "json", theme="monokai")
                console.print(Panel(syntax, title="Raw Response", border_style="yellow"))
        else:
            console.print(Panel(str(response), title="Response", border_style="green"))
            
    except Exception as e:
        console.print(f"[red]❌ Error testing endpoint: {e}[/red]")

def interactive_chat_mode(endpoint_name: str) -> None:
    """Start an interactive chat session with the endpoint."""
    console.print(f"[bold blue]Starting interactive chat with endpoint: {endpoint_name}[/bold blue]")
    console.print("[dim]Type 'quit' or 'exit' to end the session[/dim]\n")
    
    chat_history = []
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                console.print("[yellow]Goodbye![/yellow]")
                break
                
            if not user_input.strip():
                continue
                
            # Add to chat history
            chat_history.append({'role': 'user', 'content': user_input})
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("AI is thinking...", total=None)
                
                response = query_endpoint(endpoint_name, chat_history, 512)
            
            # Extract assistant response
            if isinstance(response, dict) and 'messages' in response:
                # Get the last assistant message
                assistant_messages = [msg for msg in response['messages'] if msg.get('role') == 'assistant']
                if assistant_messages:
                    assistant_response = assistant_messages[-1]['content']
                    chat_history.append({'role': 'assistant', 'content': assistant_response})
                    
                    console.print(f"\n[bold green]AI[/bold green]: {assistant_response}")
                else:
                    console.print("[red]No assistant response received[/red]")
            else:
                console.print("[red]Unexpected response format[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Chat session ended by user[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

def list_endpoints() -> None:
    """List all available serving endpoints."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching endpoints...", total=None)
            
            w = WorkspaceClient()
            endpoints = w.serving_endpoints.list()
            
        if not endpoints:
            console.print("[yellow]No serving endpoints found[/yellow]")
            return
            
        table = Table(title="Available Serving Endpoints")
        table.add_column("Name", style="cyan")
        table.add_column("Task Type", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Supported", style="magenta")
        
        for ep in endpoints:
            supported = is_endpoint_supported(ep.name)
            supported_text = "✅ Yes" if supported else "❌ No"
            table.add_row(ep.name, ep.task, str(ep.state), supported_text)
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error listing endpoints: {e}[/red]")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Databricks Model Serving Utils CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python model_serving_utils.py info my-endpoint
  python model_serving_utils.py test my-endpoint --message "Hello world"
  python model_serving_utils.py chat my-endpoint
  python model_serving_utils.py list
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Display endpoint information')
    info_parser.add_argument('endpoint_name', help='Name of the serving endpoint')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test endpoint with a query')
    test_parser.add_argument('endpoint_name', help='Name of the serving endpoint')
    test_parser.add_argument('--message', '-m', help='Test message to send')
    test_parser.add_argument('--max-tokens', '-t', type=int, default=100, help='Maximum tokens in response')
    
    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Start interactive chat session')
    chat_parser.add_argument('endpoint_name', help='Name of the serving endpoint')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all available endpoints')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'info':
            display_endpoint_info(args.endpoint_name)
        elif args.command == 'test':
            test_endpoint_query(args.endpoint_name, args.message, args.max_tokens)
        elif args.command == 'chat':
            interactive_chat_mode(args.endpoint_name)
        elif args.command == 'list':
            list_endpoints()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
