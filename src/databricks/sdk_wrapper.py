from mlflow.deployments import get_deploy_client
from databricks.sdk import WorkspaceClient
from typing import List, Dict, Any, Optional


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


def get_endpoint_info(endpoint_name: str) -> dict:
    """Get detailed information about a serving endpoint."""
    w = WorkspaceClient()
    ep = w.serving_endpoints.get(endpoint_name)
    return {
        'name': ep.name,
        'task_type': ep.task,
        'state': ep.state,
        'creation_timestamp': ep.creation_timestamp,
        'last_updated_timestamp': ep.last_updated_timestamp,
        'config': ep.config,
        'supported': is_endpoint_supported(ep.name)
    }


def list_all_endpoints() -> List[dict]:
    """List all available serving endpoints with their information."""
    w = WorkspaceClient()
    endpoints = w.serving_endpoints.list()
    
    endpoint_list = []
    for ep in endpoints:
        endpoint_list.append({
            'name': ep.name,
            'task_type': ep.task,
            'state': ep.state,
            'supported': is_endpoint_supported(ep.name)
        })
    
    return endpoint_list