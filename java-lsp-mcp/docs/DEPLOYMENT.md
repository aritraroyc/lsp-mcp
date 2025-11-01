# Deployment & Examples Guide

Comprehensive guide to deploying the Java Error Checker MCP Service and using it in various scenarios.

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [LangGraph Integration](#langgraph-integration)
6. [Examples & Use Cases](#examples--use-cases)
7. [Monitoring & Debugging](#monitoring--debugging)

## Deployment Options

### Overview

| Option | Transport | Use Case | Scalability |
|--------|-----------|----------|-------------|
| **stdio** | Local stdin/stdout | Claude Desktop, local clients | Single client |
| **HTTP/SSE** | HTTP REST + SSE | Remote agents, web clients | Horizontal |
| **Docker** | HTTP/SSE in container | Containerized deployments | Container orchestration |
| **Kubernetes** | HTTP/SSE in K8s | Cloud-native, high availability | Kubernetes cluster |

## Local Development

### 1. Setup Development Environment

```bash
# Clone repository
git clone https://github.com/anthropics/java-error-checker-mcp.git
cd java-error-checker-mcp

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify Java
java -version
javac -version
```

### 2. Run Stdio Server (Claude Desktop)

```bash
# Start server
python src/server/server.py

# In another terminal, test with example client
python src/examples/example_client.py

# Or interactive mode
python src/examples/example_client.py --interactive
```

### 3. Run HTTP/SSE Server (Remote Access)

```bash
# Start server on localhost:8000
python src/server/server_sse.py

# Health check
curl http://localhost:8000/health

# Test tool call
curl -X POST http://localhost:8000/sse \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "create_session",
      "arguments": {"project_name": "test"}
    },
    "id": 1
  }'
```

### 4. Development Tips

**Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
python src/server/server.py
tail -f /tmp/java-error-checker-mcp.log
```

**Use different workspace directory:**
```bash
export JDTLS_WORKSPACE_DIR=/path/to/workspaces
python src/server/server.py
```

**Profile with different Java versions:**
```bash
# Test with Java 11
JAVA_HOME=/usr/lib/jvm/java-11-openjdk java -version
JAVA_HOME=/usr/lib/jvm/java-11-openjdk python src/server/server.py
```

## Docker Deployment

### 1. Build Docker Image

```bash
# Dockerfile already included in repository
docker build -t java-error-checker:latest .

# Build with specific Java version
docker build --build-arg JAVA_VERSION=17 -t java-error-checker:java17 .
```

### 2. Run Container

```bash
# Basic run
docker run -p 8000:8000 java-error-checker:latest

# With environment variables
docker run -p 8000:8000 \
  -e JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
  -e LOG_LEVEL=INFO \
  java-error-checker:latest

# With volume mount for persistent workspaces
docker run -p 8000:8000 \
  -v jdtls-workspaces:/tmp/jdtls-workspaces \
  java-error-checker:latest

# With custom workspace directory
docker run -p 8000:8000 \
  -e JDTLS_WORKSPACE_DIR=/workspaces \
  -v /local/workspaces:/workspaces \
  java-error-checker:latest
```

### 3. Docker Compose

```bash
# Start with docker-compose
docker-compose up

# Rebuild and start
docker-compose up --build

# Stop containers
docker-compose down

# View logs
docker-compose logs -f server
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  java-error-checker:
    build: .
    ports:
      - "8000:8000"
    environment:
      - JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
      - LOG_LEVEL=INFO
      - JDTLS_WORKSPACE_DIR=/tmp/jdtls-workspaces
    volumes:
      - jdtls-workspaces:/tmp/jdtls-workspaces
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  jdtls-workspaces:
```

## Cloud Deployment

### 1. AWS ECS

```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker tag java-error-checker:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/java-error-checker:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/java-error-checker:latest

# Create ECS task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create ECS service
aws ecs create-service --cluster my-cluster --service-name java-error-checker --task-definition java-error-checker --desired-count 2
```

### 2. Google Cloud Run

```bash
# Configure gcloud
gcloud config set project PROJECT_ID

# Build with Cloud Build
gcloud builds submit --tag gcr.io/PROJECT_ID/java-error-checker

# Deploy to Cloud Run
gcloud run deploy java-error-checker \
  --image gcr.io/PROJECT_ID/java-error-checker \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --allow-unauthenticated

# Get service URL
gcloud run services describe java-error-checker --region us-central1
```

### 3. Kubernetes (Helm)

```bash
# Create namespace
kubectl create namespace java-error-checker

# Create ConfigMap for environment variables
kubectl create configmap java-error-checker-config \
  --from-literal=LOG_LEVEL=INFO \
  --from-literal=JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
  -n java-error-checker

# Deploy using Helm
helm install java-error-checker ./helm-chart \
  --namespace java-error-checker \
  --values custom-values.yaml

# Check deployment
kubectl get pods -n java-error-checker
kubectl logs -n java-error-checker -l app=java-error-checker -f
```

**helm-chart/values.yaml:**
```yaml
replicaCount: 3

image:
  repository: gcr.io/project-id/java-error-checker
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80
  targetPort: 8000

resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
```

## LangGraph Integration

### 1. Simple LangGraph Workflow

```python
from langgraph.graph import StateGraph
from langchain_core.language_model import BaseLanguageModel
from typing import TypedDict
from langgraph_integration import JavaErrorCheckerClient, JavaProjectSession

class CodeGenState(TypedDict):
    project_name: str
    stage: str
    code: str
    errors: list
    feedback: str

async def generate_code(state: CodeGenState, llm: BaseLanguageModel) -> CodeGenState:
    """Generate Java code using LLM."""
    prompt = f"Generate Java code for {state['project_name']}"
    response = await llm.ainvoke(prompt)
    return {**state, "code": response.content, "stage": "generated"}

async def check_errors(state: CodeGenState, client: JavaErrorCheckerClient) -> CodeGenState:
    """Check compilation errors."""
    async with JavaProjectSession(client, state["project_name"]) as session:
        await session.write_file("Main.java", state["code"])
        errors = await session.check_errors()
    return {**state, "errors": errors["errors"], "stage": "checked"}

async def fix_errors(state: CodeGenState, llm: BaseLanguageModel) -> CodeGenState:
    """Fix errors using LLM."""
    if not state["errors"]:
        return {**state, "stage": "complete"}

    error_summary = "\n".join([
        f"{e['file']}:{e['line']} - {e['message']}"
        for e in state["errors"]
    ])
    prompt = f"Fix these Java compilation errors:\n{error_summary}\nCode:\n{state['code']}"
    response = await llm.ainvoke(prompt)
    return {**state, "code": response.content, "stage": "fixed"}

# Build graph
graph = StateGraph(CodeGenState)
graph.add_node("generate", lambda s: generate_code(s, llm))
graph.add_node("check", lambda s: check_errors(s, client))
graph.add_node("fix", lambda s: fix_errors(s, llm))

graph.add_edge("generate", "check")
graph.add_conditional_edges(
    "check",
    lambda s: "fix" if s["errors"] else "complete",
    {"fix": "fix", "complete": "__end__"}
)
graph.add_edge("fix", "check")

graph.set_entry_point("generate")
runnable = graph.compile()

# Run workflow
result = await runnable.ainvoke({"project_name": "calculator", "stage": "start", "code": "", "errors": [], "feedback": ""})
```

### 2. Agentic Multi-Stage Workflow

```python
from langgraph.graph import StateGraph
from langgraph_integration import create_langgraph_tools
import json

# Create tools
java_tools = create_langgraph_tools(base_url="http://localhost:8000")

# Tool functions
create_session_tool = java_tools[0]  # create_java_session
write_files_tool = java_tools[1]    # write_java_files
check_errors_tool = java_tools[2]   # check_java_errors

class ProjectState(TypedDict):
    project_name: str
    session_id: str
    stage: int
    generated_files: dict
    compilation_errors: list
    status: str

async def stage_models(state: ProjectState) -> ProjectState:
    """Stage 1: Generate data models."""
    # Use LLM to generate models
    models = {
        "src/main/java/User.java": "public class User { ... }",
        "src/main/java/Product.java": "public class Product { ... }"
    }

    # Write files
    result = await write_files_tool(state["session_id"], models)

    # Check errors
    errors_result = await check_errors_tool(state["session_id"])

    return {**state, "stage": 2, "generated_files": models, "compilation_errors": errors_result["errors"]}

async def stage_services(state: ProjectState) -> ProjectState:
    """Stage 2: Generate business logic."""
    services = {
        "src/main/java/UserService.java": "...",
        "src/main/java/ProductService.java": "..."
    }

    await write_files_tool(state["session_id"], services)
    errors_result = await check_errors_tool(state["session_id"])

    return {**state, "stage": 3, "compilation_errors": errors_result["errors"]}

async def stage_controllers(state: ProjectState) -> ProjectState:
    """Stage 3: Generate REST controllers."""
    controllers = {
        "src/main/java/UserController.java": "...",
        "src/main/java/ProductController.java": "..."
    }

    await write_files_tool(state["session_id"], controllers)
    errors_result = await check_errors_tool(state["session_id"])

    if errors_result["errors"]:
        state["status"] = "needs_fixes"
    else:
        state["status"] = "complete"

    return {**state, "stage": 4, "compilation_errors": errors_result["errors"]}

# Build workflow
graph = StateGraph(ProjectState)
graph.add_node("models", stage_models)
graph.add_node("services", stage_services)
graph.add_node("controllers", stage_controllers)

graph.add_edge("models", "services")
graph.add_edge("services", "controllers")
graph.set_entry_point("models")

workflow = graph.compile()

# Execute
initial_state = {
    "project_name": "ecommerce-api",
    "session_id": await create_session_tool("ecommerce-api"),
    "stage": 1,
    "generated_files": {},
    "compilation_errors": [],
    "status": "in_progress"
}

result = await workflow.ainvoke(initial_state)
print(f"Final status: {result['status']}")
print(f"Errors: {result['compilation_errors']}")
```

## Examples & Use Cases

### Use Case 1: Simple Compilation Validation

```python
import asyncio
from langgraph_integration import JavaErrorCheckerClient, JavaProjectSession

async def validate_code():
    client = JavaErrorCheckerClient(base_url="http://localhost:8000")

    # Create session
    session_id = await client.create_session("validation-project")

    # Write code
    java_code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""
    await client.write_file(session_id, "HelloWorld.java", java_code)

    # Check errors
    result = await client.check_errors(session_id)

    if result["error_count"] == 0:
        print("✓ Code compiles successfully!")
    else:
        print("✗ Found compilation errors:")
        for error in result["errors"]:
            print(f"  {error['file']}:{error['line']} - {error['message']}")

    # Cleanup
    await client.delete_session(session_id)

asyncio.run(validate_code())
```

### Use Case 2: Multi-File Project with Error Recovery

```python
import asyncio
from langgraph_integration import JavaErrorCheckerClient

async def build_project():
    client = JavaErrorCheckerClient(base_url="http://localhost:8000")
    session_id = await client.create_session("myapp")

    # Stage 1: Write initial files
    files = {
        "com/example/Utils.java": """
public class Utils {
    public static void greet(String name) {
        System.out.println("Hello, " + name);
    }
}
""",
        "com/example/Main.java": """
public class Main {
    public static void main(String[] args) {
        Utils.greet("World");
    }
}
"""
    }

    await client.write_multiple_files(session_id, [
        {"file_path": k, "content": v} for k, v in files.items()
    ])

    # Check for errors
    errors = (await client.check_errors(session_id))["errors"]

    if errors:
        print("Errors found, getting recommendations...")
        for error in errors:
            recs = await client.get_recommendations(session_id, error)
            print(f"\nError: {error['message']}")
            print("Recommendations:")
            for rec in recs["recommendations"]:
                print(f"  - {rec}")

    # Cleanup
    await client.delete_session(session_id)

asyncio.run(build_project())
```

### Use Case 3: Test Suite Validation

```python
import asyncio
from langgraph_integration import JavaErrorCheckerClient

async def validate_tests():
    client = JavaErrorCheckerClient(base_url="http://localhost:8000")
    session_id = await client.create_session("test-project")

    # Write production code
    await client.write_file(session_id, "Calculator.java", """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }
}
""")

    # Write test code
    await client.write_file(session_id, "src/test/java/CalculatorTest.java", """
public class CalculatorTest {
    Calculator calc = new Calculator();

    void testAdd() {
        assert calc.add(2, 2) == 4;
    }

    void testSubtract() {
        assert calc.subtract(5, 3) == 2;
    }
}
""")

    # Validate compilation
    result = await client.check_errors(session_id)

    if result["error_count"] == 0:
        print("✓ All tests compile successfully!")
    else:
        print("✗ Test compilation failed")
        for error in result["errors"]:
            print(f"  {error['file']}:{error['line']} - {error['message']}")

    await client.delete_session(session_id)

asyncio.run(validate_tests())
```

## Monitoring & Debugging

### 1. Enable Detailed Logging

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Or modify in code
import logging
logging.basicConfig(level=logging.DEBUG)

# Watch logs
tail -f /tmp/java-error-checker-mcp.log
```

### 2. Inspect Workspace

```bash
# List all sessions
ls -la /tmp/jdtls-workspaces/

# Inspect specific session
ls -la /tmp/jdtls-workspaces/SESSION_ID/

# View workspace structure
tree /tmp/jdtls-workspaces/SESSION_ID/
```

### 3. Health Checks

```bash
# HTTP/SSE server health
curl http://localhost:8000/health

# Check Java installation
java -version
javac -version

# Check JDTLS
ls -la ~/.local/share/jdtls/
```

### 4. Performance Monitoring

```python
import time
from langgraph_integration import JavaErrorCheckerClient

async def benchmark():
    client = JavaErrorCheckerClient(base_url="http://localhost:8000")

    # Measure session creation
    start = time.time()
    session_id = await client.create_session("perf-test")
    create_time = time.time() - start

    # Measure file write
    start = time.time()
    await client.write_file(session_id, "Test.java", "public class Test {}")
    write_time = time.time() - start

    # Measure error check
    start = time.time()
    await client.check_errors(session_id)
    check_time = time.time() - start

    print(f"Create session: {create_time:.3f}s")
    print(f"Write file: {write_time:.3f}s")
    print(f"Check errors: {check_time:.3f}s")

    await client.delete_session(session_id)

asyncio.run(benchmark())
```

### 5. Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Java not found | "java: command not found" | Install JDK, set JAVA_HOME |
| Port in use | "Address already in use" | Use different port or kill existing process |
| Workspace bloat | Disk space issues | Run cleanup: `manager.cleanup_old_sessions()` |
| Session timeout | Session not found | Call `refresh_session()` during long workflows |
| Memory issues | Out of memory errors | Increase JVM memory: `JDTLS_MEMORY=2G` |
| JDTLS path issues | Compilation fails | Verify JDTLS path or rely on javac |
