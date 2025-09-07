#!/usr/bin/env python3
"""
Demo script showing the Rich CLI functionality for model_serving_utils.py
"""

import subprocess
import sys

def run_command(cmd):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    print("🚀 Databricks Model Serving Utils CLI Demo")
    print("=" * 50)
    
    # Test help command
    print("\n1. Testing help command:")
    print("Command: python scripts/model_serving_utils.py --help")
    returncode, stdout, stderr = run_command("python scripts/model_serving_utils.py --help")
    if returncode == 0:
        print("✅ Help command works!")
        print(stdout[:200] + "..." if len(stdout) > 200 else stdout)
    else:
        print(f"❌ Help command failed: {stderr}")
    
    # Test info command
    print("\n2. Testing info command:")
    print("Command: python scripts/model_serving_utils.py info mas-84eae27f-endpoint")
    returncode, stdout, stderr = run_command("python scripts/model_serving_utils.py info mas-84eae27f-endpoint")
    if returncode == 0:
        print("✅ Info command works!")
        print("Endpoint information displayed successfully")
    else:
        print(f"❌ Info command failed: {stderr}")
    
    # Test test command
    print("\n3. Testing test command:")
    print("Command: python scripts/model_serving_utils.py test mas-84eae27f-endpoint --message 'Hello'")
    returncode, stdout, stderr = run_command("python scripts/model_serving_utils.py test mas-84eae27f-endpoint --message 'Hello'")
    if returncode == 0:
        print("✅ Test command works!")
        print("Endpoint query test successful")
    else:
        print(f"❌ Test command failed: {stderr}")
    
    print("\n🎉 CLI Demo completed!")
    print("\nAvailable commands:")
    print("  • python scripts/model_serving_utils.py info <endpoint>     - Show endpoint details")
    print("  • python scripts/model_serving_utils.py test <endpoint>     - Test endpoint with query")
    print("  • python scripts/model_serving_utils.py chat <endpoint>     - Interactive chat mode")
    print("  • python scripts/model_serving_utils.py list                - List all endpoints")

if __name__ == "__main__":
    main()
