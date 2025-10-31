#!/usr/bin/env python3
"""
Remote LangGraph Agentic Workflow Example

This example demonstrates a complete agentic workflow that consumes the Java Error
Checker MCP service hosted on a REMOTE host via HTTP/SSE transport. The agentic code
can run on any machine and communicates with the MCP service over the network.

Key features:
- Remote MCP service consumption via HTTP/SSE
- Multi-stage code generation workflow
- LangGraph state management
- Error detection and auto-fix attempts
- Session lifecycle management
- Concurrent tool execution

Architecture:
┌─────────────────────────┐         ┌──────────────────────────┐
│  LangGraph Agent        │         │   MCP Service (Remote)   │
│  (This Script)          │─HTTP──→ │   server_sse.py          │
│  Any Host               │ :8000   │   Separate Host          │
└─────────────────────────┘         └──────────────────────────┘
"""

import asyncio
import json
import logging
from typing import TypedDict, Annotated
from enum import Enum

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.types import Command
except ImportError:
    print("ERROR: LangGraph not installed. Install with:")
    print("  pip install langgraph langchain-core langchain-openai")
    exit(1)

# Import the remote MCP client
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from client.langgraph_integration import JavaErrorCheckerClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# State Definition
# ============================================================================

class GenerationStage(str, Enum):
    """Stages in the code generation workflow."""
    INIT = "init"
    MODELS = "models"
    SERVICES = "services"
    CONTROLLERS = "controllers"
    MAIN = "main"
    VALIDATE = "validate"
    COMPLETE = "complete"


class WorkflowState(TypedDict):
    """State for the LangGraph workflow."""
    session_id: str
    stage: GenerationStage
    project_name: str
    generated_files: dict
    errors: dict
    error_count: int
    retry_count: int
    max_retries: int
    recommendations: list
    status: str


# ============================================================================
# Agentic Workflow
# ============================================================================

class RemoteJavaCodeGeneratorAgent:
    """
    LangGraph-based agent that generates Java code in stages and validates
    each stage by communicating with a remote MCP service.
    """

    def __init__(self, mcp_base_url: str = "http://localhost:8000", max_retries: int = 2):
        """
        Initialize the agent.

        Args:
            mcp_base_url: Base URL of the remote MCP service
            max_retries: Maximum retry attempts for error fixing
        """
        self.client = JavaErrorCheckerClient(base_url=mcp_base_url)
        self.max_retries = max_retries
        logger.info(f"Initialized agent targeting MCP service at: {mcp_base_url}")

    # ========================================================================
    # Stage: Initialization
    # ========================================================================

    async def init_session(self, state: WorkflowState) -> WorkflowState:
        """Initialize project session on remote MCP service."""
        print(f"\n{'='*70}")
        print(f"STAGE: {state['stage'].value.upper()} - Initializing Project Session")
        print(f"{'='*70}")

        project_name = state["project_name"]
        logger.info(f"Creating session for project: {project_name}")

        try:
            session_id = await self.client.create_session(project_name)
            logger.info(f"✓ Session created: {session_id}")

            state["session_id"] = session_id
            state["status"] = f"✓ Session initialized: {session_id[:8]}..."
            state["stage"] = GenerationStage.MODELS

            return state
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            state["status"] = f"✗ Initialization failed: {str(e)}"
            return state

    # ========================================================================
    # Stage 1: Generate Data Models
    # ========================================================================

    async def generate_models(self, state: WorkflowState) -> WorkflowState:
        """Stage 1: Generate data model classes."""
        print(f"\n{'='*70}")
        print(f"STAGE: {state['stage'].value.upper()} - Generating Data Models")
        print(f"{'='*70}")

        files = {
            "com/example/model/User.java": """package com.example.model;

public class User {
    private String id;
    private String name;
    private String email;

    public User(String id, String name, String email) {
        this.id = id;
        this.name = name;
        this.email = email;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}
""",
            "com/example/model/Product.java": """package com.example.model;

public class Product {
    private String id;
    private String name;
    private double price;

    public Product(String id, String name, double price) {
        this.id = id;
        this.name = name;
        this.price = price;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public double getPrice() { return price; }
    public void setPrice(double price) { this.price = price; }
}
""",
            "com/example/model/Order.java": """package com.example.model;

import java.util.ArrayList;
import java.util.List;

public class Order {
    private String id;
    private User user;
    private List<Product> products;

    public Order(String id, User user) {
        this.id = id;
        this.user = user;
        this.products = new ArrayList<>();
    }

    public String getId() { return id; }
    public User getUser() { return user; }
    public List<Product> getProducts() { return products; }

    public void addProduct(Product product) {
        products.add(product);
    }
}
"""
        }

        return await self._write_and_validate_files(state, files, GenerationStage.SERVICES)

    # ========================================================================
    # Stage 2: Generate Service Classes
    # ========================================================================

    async def generate_services(self, state: WorkflowState) -> WorkflowState:
        """Stage 2: Generate service/business logic classes."""
        print(f"\n{'='*70}")
        print(f"STAGE: {state['stage'].value.upper()} - Generating Service Classes")
        print(f"{'='*70}")

        files = {
            "com/example/service/UserService.java": """package com.example.service;

import com.example.model.User;
import java.util.HashMap;
import java.util.Map;

public class UserService {
    private Map<String, User> users = new HashMap<>();

    public void createUser(String id, String name, String email) {
        users.put(id, new User(id, name, email));
    }

    public User getUser(String id) {
        return users.get(id);
    }

    public void updateUser(String id, String name, String email) {
        User user = users.get(id);
        if (user != null) {
            user.setName(name);
            user.setEmail(email);
        }
    }

    public void deleteUser(String id) {
        users.remove(id);
    }
}
""",
            "com/example/service/ProductService.java": """package com.example.service;

import com.example.model.Product;
import java.util.HashMap;
import java.util.Map;

public class ProductService {
    private Map<String, Product> products = new HashMap<>();

    public void createProduct(String id, String name, double price) {
        products.put(id, new Product(id, name, price));
    }

    public Product getProduct(String id) {
        return products.get(id);
    }

    public void updatePrice(String id, double newPrice) {
        Product product = products.get(id);
        if (product != null) {
            product.setPrice(newPrice);
        }
    }

    public void deleteProduct(String id) {
        products.remove(id);
    }
}
""",
            "com/example/service/OrderService.java": """package com.example.service;

import com.example.model.Order;
import com.example.model.Product;
import java.util.HashMap;
import java.util.Map;

public class OrderService {
    private Map<String, Order> orders = new HashMap<>();
    private ProductService productService;

    public OrderService(ProductService productService) {
        this.productService = productService;
    }

    public void createOrder(String orderId, String userId) {
        orders.put(orderId, new Order(orderId, null));
    }

    public void addProductToOrder(String orderId, String productId) {
        Order order = orders.get(orderId);
        Product product = productService.getProduct(productId);
        if (order != null && product != null) {
            order.addProduct(product);
        }
    }

    public Order getOrder(String orderId) {
        return orders.get(orderId);
    }
}
"""
        }

        return await self._write_and_validate_files(state, files, GenerationStage.CONTROLLERS)

    # ========================================================================
    # Stage 3: Generate Controllers
    # ========================================================================

    async def generate_controllers(self, state: WorkflowState) -> WorkflowState:
        """Stage 3: Generate controller classes."""
        print(f"\n{'='*70}")
        print(f"STAGE: {state['stage'].value.upper()} - Generating Controllers")
        print(f"{'='*70}")

        files = {
            "com/example/controller/UserController.java": """package com.example.controller;

import com.example.service.UserService;

public class UserController {
    private UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    public void handleCreateUser(String id, String name, String email) {
        userService.createUser(id, name, email);
    }

    public void handleGetUser(String id) {
        userService.getUser(id);
    }

    public void handleUpdateUser(String id, String name, String email) {
        userService.updateUser(id, name, email);
    }

    public void handleDeleteUser(String id) {
        userService.deleteUser(id);
    }
}
""",
            "com/example/controller/ProductController.java": """package com.example.controller;

import com.example.service.ProductService;

public class ProductController {
    private ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    public void handleCreateProduct(String id, String name, double price) {
        productService.createProduct(id, name, price);
    }

    public void handleGetProduct(String id) {
        productService.getProduct(id);
    }

    public void handleUpdatePrice(String id, double newPrice) {
        productService.updatePrice(id, newPrice);
    }

    public void handleDeleteProduct(String id) {
        productService.deleteProduct(id);
    }
}
"""
        }

        return await self._write_and_validate_files(state, files, GenerationStage.MAIN)

    # ========================================================================
    # Stage 4: Generate Main Application
    # ========================================================================

    async def generate_main(self, state: WorkflowState) -> WorkflowState:
        """Stage 4: Generate main application class."""
        print(f"\n{'='*70}")
        print(f"STAGE: {state['stage'].value.upper()} - Generating Main Application")
        print(f"{'='*70}")

        files = {
            "com/example/Application.java": """package com.example;

import com.example.service.UserService;
import com.example.service.ProductService;
import com.example.service.OrderService;
import com.example.controller.UserController;
import com.example.controller.ProductController;

public class Application {
    private UserService userService;
    private ProductService productService;
    private OrderService orderService;
    private UserController userController;
    private ProductController productController;

    public Application() {
        this.userService = new UserService();
        this.productService = new ProductService();
        this.orderService = new OrderService(productService);
        this.userController = new UserController(userService);
        this.productController = new ProductController(productService);
    }

    public void start() {
        System.out.println("Application started successfully");
    }

    public static void main(String[] args) {
        Application app = new Application();
        app.start();
    }
}
"""
        }

        return await self._write_and_validate_files(state, files, GenerationStage.VALIDATE)

    # ========================================================================
    # Stage 5: Final Validation
    # ========================================================================

    async def validate(self, state: WorkflowState) -> WorkflowState:
        """Stage 5: Final validation of the complete project."""
        print(f"\n{'='*70}")
        print(f"STAGE: {state['stage'].value.upper()} - Final Validation")
        print(f"{'='*70}")

        try:
            logger.info("Running final compilation check...")
            errors = await self.client.check_errors()

            if errors and errors.get("error_count", 0) > 0:
                logger.warning(f"Found {errors['error_count']} compilation errors")
                state["errors"] = errors
                state["error_count"] = errors.get("error_count", 0)
                state["status"] = f"✗ Validation failed with {state['error_count']} errors"
                state["stage"] = GenerationStage.COMPLETE
            else:
                logger.info("✓ All files compiled successfully!")
                state["error_count"] = 0
                state["status"] = "✓ Project validated successfully"
                state["stage"] = GenerationStage.COMPLETE

            return state
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            state["status"] = f"✗ Validation error: {str(e)}"
            state["stage"] = GenerationStage.COMPLETE
            return state

    # ========================================================================
    # Completion
    # ========================================================================

    async def finalize(self, state: WorkflowState) -> WorkflowState:
        """Finalize the workflow and clean up."""
        print(f"\n{'='*70}")
        print(f"WORKFLOW COMPLETE")
        print(f"{'='*70}")

        if state.get("session_id"):
            try:
                session_info = await self.client.get_session_info()
                print(f"\n📊 Session Statistics:")
                print(f"   Session ID: {state['session_id'][:8]}...")
                print(f"   Project: {state['project_name']}")
                print(f"   Total Files: {session_info.get('file_count', 'N/A')}")
                print(f"   Errors Found: {state.get('error_count', 0)}")
            except Exception as e:
                logger.warning(f"Could not retrieve session info: {e}")

        return state

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _write_and_validate_files(
        self,
        state: WorkflowState,
        files: dict,
        next_stage: GenerationStage
    ) -> WorkflowState:
        """
        Helper to write files and validate them on remote MCP service.

        Args:
            state: Current workflow state
            files: Dict of {file_path: content}
            next_stage: Stage to transition to after validation

        Returns:
            Updated state
        """
        try:
            # Prepare files for batch write
            files_list = [
                {"file_path": path, "content": content}
                for path, content in files.items()
            ]

            logger.info(f"Writing {len(files_list)} files to remote MCP service...")
            write_result = await self.client.write_multiple_files(files_list)

            if write_result.get("status") == "success":
                written = write_result.get("written", 0)
                logger.info(f"✓ Successfully wrote {written} files")
                state["generated_files"].update(files)
            else:
                logger.error(f"Write failed: {write_result.get('message')}")
                state["status"] = f"✗ File write failed"
                return state

            # Refresh session to extend timeout
            await self.client.refresh_session()
            logger.info("✓ Session timeout extended")

            # Check for errors
            logger.info("Checking for compilation errors...")
            errors = await self.client.check_errors()

            if errors and errors.get("error_count", 0) > 0:
                logger.warning(f"Found {errors['error_count']} errors in this stage")
                state["errors"] = errors
                state["error_count"] = errors.get("error_count", 0)
                state["retry_count"] = 0

                # Try to get recommendations
                if errors.get("errors"):
                    first_error = errors["errors"][0]
                    try:
                        recs = await self.client.get_recommendations(first_error)
                        state["recommendations"] = recs.get("recommendations", [])
                        logger.info(f"Recommendations: {recs}")
                    except Exception as e:
                        logger.warning(f"Could not get recommendations: {e}")

                state["status"] = f"⚠ Errors found in {state['stage'].value} stage"
                return state
            else:
                logger.info(f"✓ {state['stage'].value.capitalize()} stage validated successfully")
                state["error_count"] = 0
                state["status"] = f"✓ {state['stage'].value.capitalize()} stage complete"
                state["stage"] = next_stage
                return state

        except Exception as e:
            logger.error(f"Error in stage {state['stage'].value}: {e}")
            state["status"] = f"✗ Stage failed: {str(e)}"
            return state


# ============================================================================
# LangGraph Workflow Setup
# ============================================================================

def create_workflow(mcp_base_url: str = "http://localhost:8000") -> StateGraph:
    """
    Create the LangGraph workflow for remote Java code generation.

    Args:
        mcp_base_url: Base URL of the remote MCP service

    Returns:
        Compiled StateGraph
    """
    agent = RemoteJavaCodeGeneratorAgent(mcp_base_url=mcp_base_url)

    # Create graph
    graph = StateGraph(WorkflowState)

    # Add nodes
    graph.add_node("init", agent.init_session)
    graph.add_node("models", agent.generate_models)
    graph.add_node("services", agent.generate_services)
    graph.add_node("controllers", agent.generate_controllers)
    graph.add_node("main", agent.generate_main)
    graph.add_node("validate", agent.validate)
    graph.add_node("finalize", agent.finalize)

    # Add edges
    graph.add_edge(START, "init")
    graph.add_edge("init", "models")
    graph.add_edge("models", "services")
    graph.add_edge("services", "controllers")
    graph.add_edge("controllers", "main")
    graph.add_edge("main", "validate")
    graph.add_edge("validate", "finalize")
    graph.add_edge("finalize", END)

    # Compile
    return graph.compile()


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """Main entry point for the workflow."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Remote LangGraph Java Code Generation Workflow"
    )
    parser.add_argument(
        "--mcp-url",
        default="http://localhost:8000",
        help="Base URL of the remote MCP service (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--project-name",
        default="RemoteJavaProject",
        help="Name of the Java project (default: RemoteJavaProject)"
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"REMOTE LANGGRAPH JAVA CODE GENERATION WORKFLOW")
    print(f"{'='*70}")
    print(f"MCP Service URL: {args.mcp_url}")
    print(f"Project Name: {args.project_name}")
    print(f"{'='*70}\n")

    # Create initial state
    initial_state: WorkflowState = {
        "session_id": "",
        "stage": GenerationStage.INIT,
        "project_name": args.project_name,
        "generated_files": {},
        "errors": {},
        "error_count": 0,
        "retry_count": 0,
        "max_retries": 2,
        "recommendations": [],
        "status": "Starting workflow"
    }

    try:
        # Create and run workflow
        workflow = create_workflow(mcp_base_url=args.mcp_url)

        logger.info("Starting workflow execution...")
        result = await workflow.ainvoke(initial_state)

        # Print final report
        print(f"\n{'='*70}")
        print(f"WORKFLOW EXECUTION SUMMARY")
        print(f"{'='*70}")
        print(f"Status: {result['status']}")
        print(f"Files Generated: {len(result['generated_files'])}")
        print(f"Compilation Errors: {result['error_count']}")
        print(f"Final Stage: {result['stage'].value}")
        print(f"{'='*70}\n")

        return result

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
