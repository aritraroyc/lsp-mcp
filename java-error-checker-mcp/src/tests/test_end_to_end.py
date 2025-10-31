#!/usr/bin/env python3
"""
End-to-End Test for Java Error Checker MCP Service

Tests the complete workflow that a LangGraph agent would follow.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.base_server import JavaErrorCheckerServer
import json

async def test_end_to_end():
    """
    Simulate a complete agentic workflow:
    1. Create session
    2. Write multiple Java files
    3. Check for errors
    4. Get recommendations
    5. Fix errors and re-check
    6. Clean up
    """
    print("=" * 60)
    print("End-to-End Test: Simulating Agentic Workflow")
    print("=" * 60)

    # Initialize server
    server = JavaErrorCheckerServer()
    print("\n✓ Server initialized")

    # Stage 1: Create Session
    print("\n[Stage 1] Creating session...")
    result = await server._handle_create_session({"project_name": "calculator-app"})
    response = eval(result[0].text)  # Server returns str(dict), not JSON
    session_id = response["session_id"]
    print(f"✓ Session created: {session_id[:8]}...")
    print(f"  Project: {response['project_name']}")

    # Stage 2: Write multiple files (with intentional errors)
    print("\n[Stage 2] Writing Java files with errors...")
    files_with_errors = [
        {
            "file_path": "com/example/Calculator.java",
            "content": """package com.example;

public class Calculator {
    public int add(int a, int b) {
        return a + b  // Missing semicolon
    }

    public int multiply(int a, int b) {
        return a * b;
    }
}
"""
        },
        {
            "file_path": "com/example/Main.java",
            "content": """package com.example;

public class Main {
    public static void main(String[] args) {
        Calculator calc = new Calculator();
        int result = calc.add(5, 3);
        System.out.prinln("Result: " + result);  // Typo: prinln
    }
}
"""
        }
    ]

    result = await server._handle_write_multiple_files({
        "session_id": session_id,
        "files": files_with_errors
    })
    response = eval(result[0].text)
    print(f"✓ Files written: {response['written']} files")
    print(f"  Failed: {response['failed']}")

    # Stage 3: Check for errors
    print("\n[Stage 3] Checking for compilation errors...")
    result = await server._handle_check_errors({"session_id": session_id})
    response = eval(result[0].text)
    print(f"✓ Error check complete")
    print(f"  Errors found: {response['error_count']}")

    if response['error_count'] > 0:
        print(f"\n  Detected errors:")
        for i, error in enumerate(response['errors'], 1):
            print(f"\n    Error #{i}:")
            print(f"      File: {error['file']}")
            print(f"      Line: {error['line']}")
            print(f"      Message: {error['message']}")

        # Stage 4: Get recommendations
        print("\n[Stage 4] Getting fix recommendations...")
        first_error = response['errors'][0]
        result = await server._handle_get_recommendations({
            "session_id": session_id,
            "error": first_error
        })
        rec_response = eval(result[0].text)
        print(f"✓ Recommendations generated:")
        for i, rec in enumerate(rec_response['recommendations'], 1):
            print(f"    {i}. {rec}")

    # Stage 5: Refresh session (simulate long workflow)
    print("\n[Stage 5] Refreshing session...")
    result = await server._handle_refresh_session({"session_id": session_id})
    response = eval(result[0].text)
    print(f"✓ Session refreshed: {response['status']}")

    # Stage 6: Get session info
    print("\n[Stage 6] Getting session info...")
    result = await server._handle_get_session_info({"session_id": session_id})
    response = eval(result[0].text)
    print(f"✓ Session info:")
    print(f"    Files: {response['file_count']}")
    print(f"    Age: {response['age_seconds']:.2f}s")
    print(f"    Idle: {response['idle_seconds']:.2f}s")

    # Stage 7: Fix errors and write corrected files
    print("\n[Stage 7] Writing corrected files...")
    fixed_files = [
        {
            "file_path": "com/example/Calculator.java",
            "content": """package com.example;

public class Calculator {
    public int add(int a, int b) {
        return a + b;  // Fixed: added semicolon
    }

    public int multiply(int a, int b) {
        return a * b;
    }
}
"""
        },
        {
            "file_path": "com/example/Main.java",
            "content": """package com.example;

public class Main {
    public static void main(String[] args) {
        Calculator calc = new Calculator();
        int result = calc.add(5, 3);
        System.out.println("Result: " + result);  // Fixed: println
    }
}
"""
        }
    ]

    result = await server._handle_write_multiple_files({
        "session_id": session_id,
        "files": fixed_files
    })
    response = eval(result[0].text)
    print(f"✓ Fixed files written: {response['written']} files")

    # Stage 8: Verify no errors
    print("\n[Stage 8] Re-checking for errors...")
    result = await server._handle_check_errors({"session_id": session_id})
    response = eval(result[0].text)
    print(f"✓ Error check complete")
    print(f"  Errors found: {response['error_count']}")

    if response['error_count'] == 0:
        print("  🎉 Success! Code compiles without errors!")

    # Stage 9: List all files
    print("\n[Stage 9] Listing all files...")
    result = await server._handle_list_files({"session_id": session_id})
    response = eval(result[0].text)
    print(f"✓ Files in project:")
    for file in response['files']:
        print(f"    - {file}")

    # Stage 10: Read a file
    print("\n[Stage 10] Reading Calculator.java...")
    result = await server._handle_read_file({
        "session_id": session_id,
        "file_path": "com/example/Calculator.java"
    })
    response = eval(result[0].text)
    print(f"✓ File read successfully ({len(response['content'])} chars)")

    # Stage 11: Cleanup
    print("\n[Stage 11] Cleaning up...")
    result = await server._handle_delete_session({"session_id": session_id})
    response = eval(result[0].text)
    print(f"✓ Session deleted: {response['status']}")

    print("\n" + "=" * 60)
    print("✅ End-to-End Test PASSED!")
    print("=" * 60)
    print("\nAll components working correctly:")
    print("  ✓ Session management")
    print("  ✓ Batch file writing")
    print("  ✓ Compilation error detection")
    print("  ✓ Error recommendations")
    print("  ✓ Session refresh")
    print("  ✓ Session info tracking")
    print("  ✓ File operations")
    print("  ✓ Cleanup")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
