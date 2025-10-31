#!/usr/bin/env python3
"""
LangGraph Agent Example for Java Code Generation

Demonstrates how to consume the Java Error Checker MCP service from a
LangGraph agent running remotely.

This example creates a LangGraph agent that:
1. Generates Java code based on requirements
2. Uses the MCP service to validate compilation
3. Iteratively fixes errors based on recommendations
4. Produces a working Java project
"""

import asyncio
import json
import os
import sys
from typing import Annotated, TypedDict, Sequence
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

sys.path.insert(0, str(Path(__file__).parent.parent))

from client.langgraph_integration import JavaErrorCheckerClient, JavaProjectSession


# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")


# Global MCP client
mcp_client = JavaErrorCheckerClient(base_url=MCP_SERVER_URL)


# Define LangGraph state
class AgentState(TypedDict):
    """State for the Java code generation agent."""
    messages: Sequence[BaseMessage]
    requirements: str
    session_id: str
    current_files: list
    errors: list
    iteration: int
    max_iterations: int


# Define tools for the agent
@tool
async def create_java_project_session(project_name: str) -> str:
    """Create a new Java project session in the MCP service."""
    session_id = await mcp_client.create_session(project_name)
    return json.dumps({
        "status": "success",
        "session_id": session_id,
        "message": f"Created session {session_id} for project {project_name}"
    })


@tool
async def write_java_code(files_data: str) -> str:
    """
    Write Java code files to the project session.

    Args:
        files_data: JSON string with array of {file_path, content} objects
            Example: '[{"file_path": "com/example/Main.java", "content": "package com.example;..."}]'
    """
    files = json.loads(files_data)
    result = await mcp_client.write_multiple_files(files)
    return json.dumps(result)


@tool
async def validate_java_code() -> str:
    """Check the Java code for compilation errors."""
    result = await mcp_client.check_errors()
    return json.dumps(result)


@tool
async def get_fix_suggestions(error_data: str) -> str:
    """
    Get recommendations for fixing a compilation error.

    Args:
        error_data: JSON string with error object {file, line, message}
    """
    error = json.loads(error_data)
    result = await mcp_client.get_recommendations(error)
    return json.dumps(result)


@tool
async def list_project_files() -> str:
    """List all Java files in the current project."""
    result = await mcp_client.list_files()
    return json.dumps(result)


@tool
async def refresh_project_session() -> str:
    """Refresh the project session to extend timeout."""
    result = await mcp_client.refresh_session()
    return json.dumps(result)


# Tool list for LangGraph
tools = [
    create_java_project_session,
    write_java_code,
    validate_java_code,
    get_fix_suggestions,
    list_project_files,
    refresh_project_session,
]


# Create LLM with tools
llm = ChatOpenAI(
    model="gpt-4",
    api_key=OPENAI_API_KEY,
    temperature=0
).bind_tools(tools)


# Define graph nodes
def agent_node(state: AgentState) -> AgentState:
    """
    Agent reasoning node - decides what to do next.
    """
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": messages + [response]}


def tool_node(state: AgentState) -> AgentState:
    """
    Tool execution node - executes tool calls.
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Execute tool calls
    tool_results = []
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            # Find and execute the tool
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            for t in tools:
                if t.name == tool_name:
                    result = asyncio.run(t.func(**tool_args))
                    tool_results.append(ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"]
                    ))
                    break

    return {"messages": messages + tool_results}


def should_continue(state: AgentState) -> str:
    """
    Routing function - decides whether to continue or end.
    """
    messages = state["messages"]
    last_message = messages[-1]

    # If there are tool calls, continue to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # Otherwise, end
    return "end"


# Build the graph
def create_agent_graph():
    """Create the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


# Example usage
async def run_java_generation_agent(requirements: str):
    """
    Run the Java code generation agent.

    Args:
        requirements: Natural language description of what to build
    """
    print("="*60)
    print("LangGraph Java Code Generation Agent")
    print("="*60)
    print(f"\nRequirements: {requirements}\n")

    # Create the agent graph
    app = create_agent_graph()

    # Initialize state
    initial_state = {
        "messages": [
            HumanMessage(content=f"""You are a Java code generation expert.

Your task: {requirements}

Follow these steps:
1. Create a Java project session using create_java_project_session
2. Generate the required Java classes
3. Write them using write_java_code (write multiple files at once)
4. Validate using validate_java_code
5. If there are errors, get fix suggestions and regenerate
6. Refresh the session periodically
7. Repeat until code compiles successfully

Generate clean, well-structured Java code with proper package structure.""")
        ],
        "requirements": requirements,
        "session_id": "",
        "current_files": [],
        "errors": [],
        "iteration": 0,
        "max_iterations": 5,
    }

    # Run the agent
    try:
        final_state = await app.ainvoke(initial_state)

        print("\n" + "="*60)
        print("Agent Execution Complete")
        print("="*60)

        # Print final messages
        for msg in final_state["messages"][-3:]:
            if isinstance(msg, AIMessage):
                print(f"\nAgent: {msg.content}")
            elif isinstance(msg, ToolMessage):
                result = json.loads(msg.content)
                print(f"\nTool Result: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"\nError during agent execution: {e}")
        raise


# Simpler example without LangGraph (just using the client directly)
async def simple_agent_example():
    """
    Simplified example using just the MCP client without LangGraph.

    This demonstrates the basic workflow that a LangGraph agent would follow.
    """
    print("="*60)
    print("Simple Java Generation Example (No LangGraph)")
    print("="*60)

    async with JavaProjectSession(mcp_client, "calculator-app") as client:
        print("\n✓ Session created")

        # Stage 1: Generate model classes
        print("\nStage 1: Generating Calculator class...")
        files = [
            {
                "file_path": "com/example/Calculator.java",
                "content": """package com.example;

public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }

    public int multiply(int a, int b) {
        return a * b;
    }

    public double divide(int a, int b) {
        if (b == 0) {
            throw new IllegalArgumentException("Cannot divide by zero");
        }
        return (double) a / b;
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

        System.out.println("Addition: 5 + 3 = " + calc.add(5, 3));
        System.out.println("Subtraction: 5 - 3 = " + calc.subtract(5, 3));
        System.out.println("Multiplication: 5 * 3 = " + calc.multiply(5, 3));
        System.out.println("Division: 10 / 2 = " + calc.divide(10, 2));
    }
}
"""
            }
        ]

        result = await client.write_multiple_files(files)
        print(f"✓ Wrote {result['written']} files")

        # Check for errors
        print("\nChecking for compilation errors...")
        errors = await client.check_errors()

        if errors["error_count"] == 0:
            print("✓ No compilation errors! Code is valid.")
        else:
            print(f"⚠ Found {errors['error_count']} error(s):")
            for error in errors["errors"]:
                print(f"  - {error['file']}:{error['line']} - {error['message']}")

                # Get recommendations
                recs = await client.get_recommendations(error)
                print(f"    Recommendations:")
                for rec in recs["recommendations"]:
                    print(f"      • {rec}")

        # Get session info
        print("\nSession Info:")
        info = await client.get_session_info()
        print(f"  Files: {info['file_count']}")
        print(f"  Age: {info['age_seconds']:.1f}s")

    print("\n✓ Session cleaned up automatically")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="LangGraph Java Generation Agent")
    parser.add_argument(
        "--mode",
        choices=["simple", "langgraph"],
        default="simple",
        help="Run mode: simple (no LangGraph) or langgraph (full agent)"
    )
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="MCP server URL"
    )
    args = parser.parse_args()

    # Update global client URL
    global mcp_client
    mcp_client = JavaErrorCheckerClient(base_url=args.server)

    # Check if server is healthy
    try:
        health = await mcp_client.health_check()
        print(f"✓ Connected to MCP server: {health['service']}")
        print(f"  Transport: {health['transport']}")
    except Exception as e:
        print(f"✗ Failed to connect to MCP server at {args.server}")
        print(f"  Error: {e}")
        print(f"\nMake sure the server is running:")
        print(f"  python server_sse.py --host 0.0.0.0 --port 8000")
        return

    # Run the appropriate mode
    if args.mode == "simple":
        await simple_agent_example()
    else:
        # LangGraph mode
        if OPENAI_API_KEY == "your-api-key-here":
            print("\n⚠ Warning: OPENAI_API_KEY not set")
            print("Set it with: export OPENAI_API_KEY=your-key-here")
            print("\nRunning simple mode instead...")
            await simple_agent_example()
        else:
            await run_java_generation_agent(
                "Create a simple calculator application with add, subtract, multiply, and divide methods"
            )


if __name__ == "__main__":
    asyncio.run(main())
