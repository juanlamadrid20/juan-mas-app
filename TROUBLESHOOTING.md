# Databricks App Troubleshooting Guide

## Issue: Chat Shows "AI is thinking" Without Processing

### Problem Description
When deploying a Databricks app with a chatbot interface, users experienced an issue where the chat interface would show "AI is thinking..." indefinitely without actually processing the user's input or returning a response.

### Root Cause Analysis

The issue was caused by **endpoint compatibility problems** with the chatbot template. Specifically:

1. **Unsupported Endpoint Type**: The serving endpoint `mas-84eae27f-endpoint` had task type `agent/v1/responses`
2. **Missing Support**: The chatbot template only supported these endpoint types:
   - `agent/v1/chat`
   - `agent/v2/chat` 
   - `llm/v1/chat`
   - `agent/v1/supervisor`
   - `agent/v2/supervisor`
3. **Input Format Mismatch**: The `agent/v1/responses` endpoint expected different input parameters
4. **Response Format Differences**: The response structure was different and not properly parsed

### Troubleshooting Steps

#### Step 1: Identify the Endpoint Type
```python
from model_serving_utils import _get_endpoint_task_type

try:
    task_type = _get_endpoint_task_type('mas-84eae27f-endpoint')
    print(f'Endpoint task type: {task_type}')
except Exception as e:
    print(f'Error getting task type: {e}')
```

**Result**: `agent/v1/responses`

#### Step 2: Test Endpoint Support
```python
from model_serving_utils import is_endpoint_supported

serving_endpoint = 'mas-84eae27f-endpoint'
supported = is_endpoint_supported(serving_endpoint)
print(f'Endpoint supported: {supported}')
```

**Result**: `False` (initially)

#### Step 3: Test Endpoint Query (Before Fix)
```python
from model_serving_utils import query_endpoint

test_messages = [{'role': 'user', 'content': 'Hello, can you hear me?'}]
try:
    response = query_endpoint(serving_endpoint, test_messages, 100)
    print(f'Response: {response}')
except Exception as e:
    print(f'Error: {e}')
```

**Result**: 
```
Error: 400 Client Error: Failed to enforce schema of data '{'messages': [{'role': 'user', 'content': 'Hello, can you hear me?'}], 'max_tokens': 100}' with schema '['context': {conversation_id: string (optional), user_id: string (optional)} (optional), 'custom_inputs': Map(str -> Any) (optional), 'input': Array(Any) (required), 'max_output_tokens': long (optional), 'metadata': Map(str -> DataType.string) (optional), 'parallel_tool_calls': boolean (optional), 'reasoning': {effort: string (optional), generate_summary: string (optional)} (optional), 'store': boolean (optional), 'stream': boolean (optional), 'temperature': double (optional), 'text': Any (optional), 'tool_choice': Any (optional), 'tools': Array({type: string (required)}) (optional), 'top_p': double (optional), 'truncation': string (optional), 'user': string (optional)]'. Error: Model is missing inputs ['input']. Note that there were extra inputs: ['messages', 'max_tokens']
```

### Solution Implementation

#### 1. Add Support for `agent/v1/responses` Endpoint Type

**File**: `model_serving_utils.py`

```python
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
```

#### 2. Fix Input Format for `agent/v1/responses`

The endpoint expects different input parameters:

```python
elif task_type == "agent/v1/responses":
    # Agent response endpoints - expect 'input' field instead of 'messages'
    inputs = {
        'input': messages,
        'max_output_tokens': max_tokens,
        'stream': False
    }
```

#### 3. Add Response Parsing for `agent/v1/responses` Format

The response structure is different and requires special parsing:

```python
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
```

### Testing Scripts

#### Complete Endpoint Test Script
```python
import os
from model_serving_utils import is_endpoint_supported, query_endpoint

# Test with the actual endpoint from app.yaml
serving_endpoint = 'mas-84eae27f-endpoint'
print(f'Testing endpoint: {serving_endpoint}')

try:
    # Test if endpoint is supported
    supported = is_endpoint_supported(serving_endpoint)
    print(f'Endpoint supported: {supported}')
    
    if supported:
        # Test a simple query
        test_messages = [{'role': 'user', 'content': 'Hello, can you hear me?'}]
        print('Testing endpoint query...')
        response = query_endpoint(serving_endpoint, test_messages, 100)
        print(f'Response: {response}')
        
        # Test the chatbot's response parsing
        if isinstance(response, dict) and 'messages' in response:
            print(f'Parsed message: {response["messages"][0]["content"]}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
```

#### Full Chatbot Integration Test
```python
import os
os.environ['SERVING_ENDPOINT'] = 'mas-84eae27f-endpoint'

# Test the full chatbot functionality
from DatabricksChatbot import DatabricksChatbot
import dash

app = dash.Dash(__name__)
chatbot = DatabricksChatbot(app=app, endpoint_name='mas-84eae27f-endpoint')

# Test the _call_model_endpoint method directly
test_messages = [{'role': 'user', 'content': 'Hello, can you hear me?'}]
try:
    response = chatbot._call_model_endpoint(test_messages)
    print(f'Chatbot response: {response}')
    print('✅ Chatbot is working correctly!')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
```

### Verification Results

After implementing the fixes:

1. **Endpoint Support**: ✅ `True`
2. **Query Execution**: ✅ Successful
3. **Response Parsing**: ✅ Properly formatted
4. **Full Integration**: ✅ Chatbot working correctly

**Sample Working Response**:
```
Hello! Yes, I can hear you clearly. I'm Juan, your multi-domain assistant that can help with questions about sales operations data (like opportunities, pipelines, and sales territories) as well as Databricks usage and consumption information.

How can I help you today? Feel free to ask me about:
- Sales opportunities and pipeline information
- Sales performance across territories or representatives
- Databricks usage and consumption metrics
- Any other questions related to these domains

Is there something specific you'd like to know about either sales operations or Databricks consumption?
```

### Common Endpoint Types and Their Requirements

| Endpoint Type | Input Field | Token Parameter | Response Format |
|---------------|-------------|-----------------|-----------------|
| `llm/v1/chat` | `messages` | `max_tokens` | `choices[].message` |
| `agent/v1/chat` | `messages` | `max_tokens` | `choices[].message` |
| `agent/v2/chat` | `messages` | `max_tokens` | `choices[].message` |
| `agent/v1/supervisor` | `messages` | `max_tokens` | `messages[]` |
| `agent/v2/supervisor` | `messages` | `max_tokens` | `messages[]` |
| `agent/v1/responses` | `input` | `max_output_tokens` | `output[].content[].text` |

### Prevention Strategies

1. **Endpoint Type Validation**: Always check the endpoint task type before deployment
2. **Comprehensive Testing**: Test with actual endpoint queries during development
3. **Error Handling**: Implement proper error handling and logging
4. **Documentation**: Document endpoint-specific requirements and formats

### Files Modified

- `model_serving_utils.py`: Updated to support `agent/v1/responses` endpoint type
  - Added endpoint type to supported list
  - Fixed input format for `agent/v1/responses`
  - Added response parsing for `agent/v1/responses` format

### Deployment Notes

After implementing these fixes:
1. Commit the changes to your repository
2. Redeploy the app using Databricks CLI or workspace interface
3. Test the chat functionality in the deployed app
4. Monitor for any additional endpoint-specific issues

### Additional Resources

- [Databricks Serving Endpoints Documentation](https://docs.databricks.com/aws/en/serving-endpoints/index.html)
- [Agent Framework Documentation](https://docs.databricks.com/aws/en/generative-ai/agent-framework/index.html)
- [Chat App Template Documentation](https://docs.databricks.com/aws/en/generative-ai/agent-framework/chat-app)
