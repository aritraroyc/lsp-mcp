"""
Unit tests for Java Error Checker MCP Service
"""

import unittest
import tempfile
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_manager import SessionManager
from core.jdtls_client import JDTLSClient


class TestSessionManager(unittest.TestCase):
    """Test SessionManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_manager = SessionManager(base_workspace_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_session(self):
        """Test session creation."""
        session_id = self.session_manager.create_session("test-project")
        self.assertIsNotNone(session_id)

        session = self.session_manager.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.project_name, "test-project")

    def test_write_and_read_file(self):
        """Test writing and reading files."""
        session_id = self.session_manager.create_session()

        # Write file
        content = "public class Test { }"
        success = self.session_manager.write_file(
            session_id,
            "com/example/Test.java",
            content
        )
        self.assertTrue(success)

        # Read file
        read_content = self.session_manager.read_file(
            session_id,
            "com/example/Test.java"
        )
        self.assertEqual(read_content, content)

    def test_list_files(self):
        """Test listing files."""
        session_id = self.session_manager.create_session()

        # Write multiple files
        self.session_manager.write_file(
            session_id,
            "com/example/Test1.java",
            "public class Test1 { }"
        )
        self.session_manager.write_file(
            session_id,
            "com/example/Test2.java",
            "public class Test2 { }"
        )

        # List files
        files = self.session_manager.list_files(session_id)
        self.assertEqual(len(files), 2)
        self.assertTrue(any("Test1.java" in f for f in files))
        self.assertTrue(any("Test2.java" in f for f in files))

    def test_delete_session(self):
        """Test session deletion."""
        session_id = self.session_manager.create_session()
        self.assertIsNotNone(self.session_manager.get_session(session_id))

        # Delete session
        success = self.session_manager.delete_session(session_id)
        self.assertTrue(success)
        self.assertIsNone(self.session_manager.get_session(session_id))

    def test_workspace_path(self):
        """Test getting workspace path."""
        session_id = self.session_manager.create_session()
        workspace_path = self.session_manager.get_workspace_path(session_id)

        self.assertIsNotNone(workspace_path)
        self.assertTrue(workspace_path.exists())
        self.assertTrue(workspace_path.is_dir())


class TestJDTLSClient(unittest.TestCase):
    """Test JDTLSClient functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.jdtls_client = JDTLSClient()

    def test_parse_javac_errors(self):
        """Test parsing javac error output."""
        error_output = """
Test.java:5: error: ';' expected
        return a + b
                    ^
Test.java:8: error: cannot find symbol
        System.out.prinln("test");
                  ^
  symbol:   method prinln(String)
  location: variable out of type PrintStream
2 errors
"""
        errors = self.jdtls_client._parse_javac_errors(
            error_output,
            Path("/tmp")
        )

        self.assertEqual(len(errors), 2)

        # Check first error
        self.assertEqual(errors[0]['line'], 5)
        self.assertIn("';' expected", errors[0]['message'])
        self.assertEqual(errors[0]['severity'], 'error')

        # Check second error
        self.assertEqual(errors[1]['line'], 8)
        self.assertIn("cannot find symbol", errors[1]['message'])

    def test_generate_recommendations_semicolon(self):
        """Test recommendation generation for missing semicolon."""
        from core.error_recommendation_engine import ErrorRecommendationEngine

        engine = ErrorRecommendationEngine()
        error = {
            "message": "';' expected",
            "file": "Test.java",
            "line": 5
        }

        recommendations = engine.get_recommendations(error)
        self.assertTrue(len(recommendations) > 0)
        self.assertTrue(
            any("semicolon" in r.lower() for r in recommendations)
        )

    def test_generate_recommendations_cannot_find_symbol(self):
        """Test recommendation generation for cannot find symbol."""
        from core.error_recommendation_engine import ErrorRecommendationEngine

        engine = ErrorRecommendationEngine()
        error = {
            "message": "cannot find symbol: variable test",
            "file": "Test.java",
            "line": 10
        }

        recommendations = engine.get_recommendations(error)
        self.assertTrue(len(recommendations) > 0)
        self.assertTrue(
            any("import" in r.lower() or "declared" in r.lower()
                for r in recommendations)
        )


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
