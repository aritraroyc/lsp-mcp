"""
JDTLS (Eclipse JDT Language Server) Client

Manages communication with the Eclipse JDT Language Server for Java compilation checking.
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile

logger = logging.getLogger(__name__)


class JDTLSClient:
    """Client for interacting with Eclipse JDT Language Server."""

    def __init__(self, jdtls_path: Optional[str] = None, java_home: Optional[str] = None):
        """
        Initialize JDTLS client.

        Args:
            jdtls_path: Path to JDTLS installation
            java_home: JAVA_HOME path
        """
        self.jdtls_path = Path(jdtls_path) if jdtls_path else self._find_jdtls()
        self.java_home = Path(java_home) if java_home else self._find_java_home()
        self.process: Optional[subprocess.Popen] = None
        self.message_id = 0

    def _find_jdtls(self) -> Optional[Path]:
        """Try to find JDTLS installation."""
        # Common installation paths
        common_paths = [
            Path.home() / ".local/share/jdtls",
            Path("/usr/local/share/jdtls"),
            Path("/opt/jdtls"),
        ]

        for path in common_paths:
            if path.exists():
                return path

        logger.warning("JDTLS not found in common paths")
        return None

    def _find_java_home(self) -> Optional[Path]:
        """Try to find JAVA_HOME."""
        import os

        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            return Path(java_home)

        # Try to find java executable
        try:
            result = subprocess.run(
                ["which", "java"],
                capture_output=True,
                text=True,
                check=True
            )
            java_path = Path(result.stdout.strip())
            # Resolve symlinks and go up to find JAVA_HOME
            java_path = java_path.resolve()
            return java_path.parent.parent
        except Exception as e:
            logger.warning(f"Could not find JAVA_HOME: {e}")
            return None

    async def start_server(self, workspace_path: Path, data_dir: Optional[Path] = None):
        """
        Start the JDTLS server for a workspace.

        Args:
            workspace_path: Path to the Java project workspace
            data_dir: Path to store JDTLS data (cache, metadata)
        """
        if not self.jdtls_path or not self.jdtls_path.exists():
            raise RuntimeError("JDTLS not found. Please install JDTLS and configure the path.")

        if not self.java_home or not self.java_home.exists():
            raise RuntimeError("JAVA_HOME not found. Please install Java and set JAVA_HOME.")

        # Use temp directory for data if not specified
        if data_dir is None:
            data_dir = Path(tempfile.mkdtemp(prefix="jdtls-data-"))

        data_dir.mkdir(parents=True, exist_ok=True)

        # Build command to start JDTLS
        java_executable = self.java_home / "bin" / "java"

        # Find the JDTLS launcher jar
        launcher_jar = self._find_launcher_jar()
        if not launcher_jar:
            raise RuntimeError("JDTLS launcher JAR not found")

        # Find the configuration directory
        config_dir = self._find_config_dir()
        if not config_dir:
            raise RuntimeError("JDTLS config directory not found")

        command = [
            str(java_executable),
            "-Declipse.application=org.eclipse.jdt.ls.core.id1",
            "-Dosgi.bundles.defaultStartLevel=4",
            "-Declipse.product=org.eclipse.jdt.ls.core.product",
            "-Dlog.level=ALL",
            "-noverify",
            "-Xmx1G",
            "-jar", str(launcher_jar),
            "-configuration", str(config_dir),
            "-data", str(data_dir)
        ]

        logger.info(f"Starting JDTLS with command: {' '.join(command)}")
        logger.info(f"Workspace: {workspace_path}")

        # Note: In a real implementation, we would start the process and communicate via stdin/stdout
        # For this implementation, we'll use the language server protocol
        self.workspace_path = workspace_path
        self.data_dir = data_dir
        self.command = command

    def _find_launcher_jar(self) -> Optional[Path]:
        """Find the JDTLS launcher JAR."""
        if not self.jdtls_path:
            return None

        plugins_dir = self.jdtls_path / "plugins"
        if not plugins_dir.exists():
            return None

        # Look for org.eclipse.equinox.launcher_*.jar
        launcher_jars = list(plugins_dir.glob("org.eclipse.equinox.launcher_*.jar"))
        return launcher_jars[0] if launcher_jars else None

    def _find_config_dir(self) -> Optional[Path]:
        """Find the JDTLS configuration directory."""
        if not self.jdtls_path:
            return None

        config_dir = self.jdtls_path / "config_linux"
        if config_dir.exists():
            return config_dir

        config_dir = self.jdtls_path / "config_mac"
        if config_dir.exists():
            return config_dir

        config_dir = self.jdtls_path / "config_win"
        if config_dir.exists():
            return config_dir

        return None

    async def check_compilation_errors(self, workspace_path: Path) -> List[Dict[str, Any]]:
        """
        Check for compilation errors in the workspace using javac.

        This is a simplified implementation that uses javac directly instead of
        running a full JDTLS server. For production use, you would want to
        implement full LSP communication with JDTLS.

        Args:
            workspace_path: Path to the Java project workspace

        Returns:
            List of compilation errors/warnings
        """
        errors = []

        # Find all Java files
        java_files = list(workspace_path.rglob("*.java"))

        if not java_files:
            logger.info("No Java files found in workspace")
            return []

        logger.info(f"Found {len(java_files)} Java files")

        # Create a temporary directory for compilation output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir)

            # Try to compile all Java files
            for java_file in java_files:
                try:
                    result = await self._compile_file(java_file, workspace_path, temp_output)
                    if result:
                        errors.extend(result)
                except Exception as e:
                    logger.error(f"Error compiling {java_file}: {e}")
                    errors.append({
                        "file": str(java_file.relative_to(workspace_path)),
                        "line": 0,
                        "column": 0,
                        "severity": "error",
                        "message": f"Compilation failed: {str(e)}"
                    })

        return errors

    async def _compile_file(
        self,
        java_file: Path,
        workspace_path: Path,
        output_dir: Path
    ) -> List[Dict[str, Any]]:
        """
        Compile a single Java file and extract errors.

        Args:
            java_file: Path to the Java file
            workspace_path: Root workspace path
            output_dir: Directory for compiled output

        Returns:
            List of compilation errors
        """
        errors = []

        # Build classpath (include src/main/java)
        src_dir = workspace_path / "src" / "main" / "java"
        classpath = str(src_dir)

        # Run javac
        command = [
            "javac",
            "-d", str(output_dir),
            "-cp", classpath,
            "-Xlint:all",
            str(java_file)
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                # Parse compilation errors from stderr
                error_output = stderr.decode('utf-8')
                parsed_errors = self._parse_javac_errors(error_output, workspace_path)
                errors.extend(parsed_errors)
            else:
                logger.info(f"Successfully compiled {java_file.name}")

        except FileNotFoundError:
            logger.error("javac not found. Please install Java JDK.")
            errors.append({
                "file": str(java_file.relative_to(workspace_path)),
                "line": 0,
                "column": 0,
                "severity": "error",
                "message": "javac compiler not found. Please install Java JDK."
            })
        except Exception as e:
            logger.error(f"Error running javac: {e}")
            errors.append({
                "file": str(java_file.relative_to(workspace_path)),
                "line": 0,
                "column": 0,
                "severity": "error",
                "message": f"Compilation error: {str(e)}"
            })

        return errors

    def _parse_javac_errors(self, error_output: str, workspace_path: Path) -> List[Dict[str, Any]]:
        """
        Parse javac error output.

        Args:
            error_output: javac stderr output
            workspace_path: Root workspace path

        Returns:
            List of parsed errors
        """
        errors = []
        lines = error_output.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # javac error format: file.java:line: error: message
            if '.java:' in line and (':' in line):
                try:
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        file_path = parts[0].strip()
                        line_num = int(parts[1].strip())
                        severity = parts[2].strip()
                        message = parts[3].strip()

                        # Try to make file path relative
                        try:
                            rel_path = Path(file_path).relative_to(workspace_path)
                            file_path = str(rel_path)
                        except:
                            pass

                        errors.append({
                            "file": file_path,
                            "line": line_num,
                            "column": 0,
                            "severity": severity.lower() if severity in ["error", "warning"] else "error",
                            "message": message
                        })

                        # Next line might contain the code snippet
                        i += 1
                        if i < len(lines):
                            code_line = lines[i].strip()
                            if code_line:
                                errors[-1]["code"] = code_line

                        # Next line might contain the error pointer (^)
                        i += 1
                        if i < len(lines) and '^' in lines[i]:
                            pointer_line = lines[i]
                            column = pointer_line.index('^')
                            errors[-1]["column"] = column

                except (ValueError, IndexError) as e:
                    logger.debug(f"Could not parse error line: {line} - {e}")

            i += 1

        return errors

    async def stop_server(self):
        """Stop the JDTLS server."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
