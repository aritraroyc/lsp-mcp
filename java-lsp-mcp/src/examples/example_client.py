#!/usr/bin/env python3
"""
Example MCP Client for Java Error Checker Service

This script demonstrates how to use the Java Error Checker MCP service
to check Java code for compilation errors.
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Example Java code with intentional errors
JAVA_CODE_WITH_ERRORS = """
package com.example;

public class Calculator {
    public int add(int a, int b) {
        return a + b
    }

    public int multiply(int a, int b) {
        return a * b;
    }

    public void printResult() {
        System.out.prinln("Result");  // Typo: prinln instead of println
    }

    public static void main(String[] args) {
        Calculator calc = new Calculator();
        int result = calc.add(5, 10);
        calc.printResult();
    }
}
"""

JAVA_CODE_CORRECT = """
package com.example;

public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int multiply(int a, int b) {
        return a * b;
    }

    public void printResult(int result) {
        System.out.println("Result: " + result);
    }

    public static void main(String[] args) {
        Calculator calc = new Calculator();
        int result = calc.add(5, 10);
        calc.printResult(result);
    }
}
"""


async def run_example():
    """Run the example client."""
    print("=" * 60)
    print("Java Error Checker MCP Client Example")
    print("=" * 60)

    # Get the path to the server script
    server_path = Path(__file__).parent.parent / "server" / "server.py"

    # Set up server parameters
    server_params = StdioServerParameters(
        command="python3",
        args=[str(server_path)],
        env=None
    )

    print(f"\n1. Connecting to MCP server at: {server_path}")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            print("   ✓ Connected to MCP server")

            # List available tools
            print("\n2. Listing available tools...")
            tools = await session.list_tools()
            print(f"   ✓ Found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"     - {tool.name}: {tool.description}")

            # Create a session
            print("\n3. Creating a new Java project session...")
            result = await session.call_tool(
                "create_session",
                arguments={"project_name": "calculator-example"}
            )
            response = eval(result.content[0].text)
            session_id = response["session_id"]
            print(f"   ✓ Session created: {session_id}")

            # Write Java file with errors
            print("\n4. Writing Java file with intentional errors...")
            result = await session.call_tool(
                "write_java_file",
                arguments={
                    "session_id": session_id,
                    "file_path": "com/example/Calculator.java",
                    "content": JAVA_CODE_WITH_ERRORS
                }
            )
            response = eval(result.content[0].text)
            print(f"   ✓ File written: {response['file_path']}")

            # List files
            print("\n5. Listing files in workspace...")
            result = await session.call_tool(
                "list_files",
                arguments={"session_id": session_id}
            )
            response = eval(result.content[0].text)
            print(f"   ✓ Found {response['file_count']} file(s):")
            for file in response['files']:
                print(f"     - {file}")

            # Check for errors
            print("\n6. Checking for compilation errors...")
            result = await session.call_tool(
                "check_errors",
                arguments={"session_id": session_id}
            )
            response = eval(result.content[0].text)
            print(f"   ✓ Error check complete")
            print(f"   ✓ Found {response['error_count']} error(s)")

            if response['error_count'] > 0:
                print("\n   Errors found:")
                for i, error in enumerate(response['errors'], 1):
                    print(f"\n   Error #{i}:")
                    print(f"     File: {error['file']}")
                    print(f"     Line: {error['line']}, Column: {error['column']}")
                    print(f"     Severity: {error['severity']}")
                    print(f"     Message: {error['message']}")
                    if 'code' in error:
                        print(f"     Code: {error['code']}")

                # Get recommendations for first error
                print("\n7. Getting recommendations for first error...")
                result = await session.call_tool(
                    "get_recommendations",
                    arguments={
                        "session_id": session_id,
                        "error": response['errors'][0]
                    }
                )
                rec_response = eval(result.content[0].text)
                print("   ✓ Recommendations:")
                for rec in rec_response['recommendations']:
                    print(f"     - {rec}")

            # Write corrected Java file
            print("\n8. Writing corrected Java file...")
            result = await session.call_tool(
                "write_java_file",
                arguments={
                    "session_id": session_id,
                    "file_path": "com/example/Calculator.java",
                    "content": JAVA_CODE_CORRECT
                }
            )
            print("   ✓ Corrected file written")

            # Check errors again
            print("\n9. Checking for errors again...")
            result = await session.call_tool(
                "check_errors",
                arguments={"session_id": session_id}
            )
            response = eval(result.content[0].text)
            print(f"   ✓ Error check complete")
            print(f"   ✓ Found {response['error_count']} error(s)")

            if response['error_count'] == 0:
                print("   🎉 No errors! Code compiles successfully!")

            # Clean up
            print("\n10. Cleaning up session...")
            result = await session.call_tool(
                "delete_session",
                arguments={"session_id": session_id}
            )
            print("   ✓ Session deleted")

            print("\n" + "=" * 60)
            print("Example completed successfully!")
            print("=" * 60)


async def interactive_mode():
    """Run in interactive mode."""
    print("=" * 60)
    print("Java Error Checker MCP Client - Interactive Mode")
    print("=" * 60)

    server_path = Path(__file__).parent / "server.py"
    server_params = StdioServerParameters(
        command="python3",
        args=[str(server_path)],
        env=None
    )

    print(f"\nConnecting to MCP server at: {server_path}")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✓ Connected to MCP server\n")

            # Create a session
            result = await session.call_tool(
                "create_session",
                arguments={"project_name": "interactive-session"}
            )
            response = eval(result.content[0].text)
            session_id = response["session_id"]
            print(f"✓ Session created: {session_id}\n")

            print("Commands:")
            print("  write <file_path>  - Write Java code (multi-line input)")
            print("  check             - Check for compilation errors")
            print("  list              - List all files")
            print("  read <file_path>  - Read a file")
            print("  quit              - Exit and clean up")
            print()

            while True:
                try:
                    command = input(">>> ").strip()

                    if command == "quit":
                        break

                    elif command == "check":
                        result = await session.call_tool(
                            "check_errors",
                            arguments={"session_id": session_id}
                        )
                        response = eval(result.content[0].text)
                        print(f"\nFound {response['error_count']} error(s)")
                        for error in response['errors']:
                            print(f"  {error['file']}:{error['line']} - {error['message']}")
                        print()

                    elif command == "list":
                        result = await session.call_tool(
                            "list_files",
                            arguments={"session_id": session_id}
                        )
                        response = eval(result.content[0].text)
                        print(f"\nFiles ({response['file_count']}):")
                        for file in response['files']:
                            print(f"  {file}")
                        print()

                    elif command.startswith("write "):
                        file_path = command[6:].strip()
                        print("Enter Java code (type END on a new line to finish):")
                        lines = []
                        while True:
                            line = input()
                            if line == "END":
                                break
                            lines.append(line)
                        content = "\n".join(lines)

                        result = await session.call_tool(
                            "write_java_file",
                            arguments={
                                "session_id": session_id,
                                "file_path": file_path,
                                "content": content
                            }
                        )
                        print("✓ File written\n")

                    elif command.startswith("read "):
                        file_path = command[5:].strip()
                        result = await session.call_tool(
                            "read_file",
                            arguments={
                                "session_id": session_id,
                                "file_path": file_path
                            }
                        )
                        response = eval(result.content[0].text)
                        if response['status'] == 'success':
                            print(f"\n{response['content']}\n")
                        else:
                            print(f"\nError: {response['message']}\n")

                    else:
                        print("Unknown command\n")

                except EOFError:
                    break
                except Exception as e:
                    print(f"Error: {e}\n")

            # Clean up
            print("\nCleaning up...")
            await session.call_tool(
                "delete_session",
                arguments={"session_id": session_id}
            )
            print("✓ Session deleted")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(run_example())


if __name__ == "__main__":
    main()
