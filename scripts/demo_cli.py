#!/usr/bin/env python3
"""
Demo script showing the Rich CLI functionality for src.cli module

This script tests the various CLI commands available in the model serving utilities.
Make sure you're authenticated with Databricks CLI before running:
    databricks auth login

Usage:
    uv run python scripts/demo_cli.py

The CLI module is properly organized in src/cli/ and can be run with:
    uv run python -m src.cli <command>
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
    print("Command: uv run python -m src.cli --help")
    returncode, stdout, stderr = run_command("uv run python -m src.cli --help")
    if returncode == 0:
        print("✅ Help command works!")
        print(stdout[:200] + "..." if len(stdout) > 200 else stdout)
    else:
        print(f"❌ Help command failed: {stderr}")
    
    # Test list command
    print("\n2. Testing list command:")
    print("Command: uv run python -m src.cli list")
    returncode, stdout, stderr = run_command("uv run python -m src.cli list")
    if returncode == 0:
        print("✅ List command works!")
        print("Available endpoints displayed successfully")
    else:
        print(f"❌ List command failed: {stderr}")
        print("Note: This may fail if you're not authenticated with Databricks CLI")
    
    # Test info command
    print("\n3. Testing info command:")
    print("Command: uv run python -m src.cli info mas-84eae27f-endpoint")
    returncode, stdout, stderr = run_command("uv run python -m src.cli info mas-84eae27f-endpoint")
    if returncode == 0:
        print("✅ Info command works!")
        print("Endpoint information displayed successfully")
    else:
        print(f"❌ Info command failed: {stderr}")
        print("Note: Replace 'mas-84eae27f-endpoint' with your actual endpoint name")
    
    # Test test command
    print("\n4. Testing test command:")
    print("Command: uv run python -m src.cli test mas-84eae27f-endpoint --message 'Hello, this is a test message'")
    returncode, stdout, stderr = run_command("uv run python -m src.cli test mas-84eae27f-endpoint --message 'Hello, this is a test message'")
    if returncode == 0:
        print("✅ Test command works!")
        print("Endpoint query test successful")
    else:
        print(f"❌ Test command failed: {stderr}")
        print("Note: This requires a valid endpoint name and proper authentication")
    
    print("\n🎉 CLI Demo completed!")
    print("\n📋 Available CLI Commands:")
    print("  • uv run python -m src.cli list                    - List all endpoints")
    print("  • uv run python -m src.cli info <endpoint>         - Show endpoint details")
    print("  • uv run python -m src.cli test <endpoint>         - Test endpoint with query")
    print("  • uv run python -m src.cli chat <endpoint>         - Interactive chat mode")
    print("\n💡 Tips:")
    print("  • Use --help with any command for detailed usage information")
    print("  • Make sure you're authenticated: databricks auth login")
    print("  • Replace <endpoint> with your actual serving endpoint name")
    print("  • Use your endpoint from app.yaml or .env file for testing")

if __name__ == "__main__":
    main()
