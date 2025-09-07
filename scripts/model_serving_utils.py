# Backwards compatibility facade - imports from modular components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.databricks import (
    _get_endpoint_task_type,
    is_endpoint_supported,
    _validate_endpoint_task_type,
    _query_endpoint,
    query_endpoint,
    get_endpoint_info,
    list_all_endpoints
)

from src.cli import (
    display_endpoint_info,
    test_endpoint_query,
    interactive_chat_mode,
    list_endpoints,
    main
)


if __name__ == "__main__":
    main()
