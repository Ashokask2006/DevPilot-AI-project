"""
Tool Registry for DevPilot AI.
Provides unified dispatch, validation, and schema definitions for all agent tools.
"""

from typing import Dict, Any, Callable, List
from app.tools import filesystem, terminal, git_tools


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._register_default_tools()

    def register(self, name: str, func: Callable):
        self._tools[name] = func

    def _register_default_tools(self):
        # Filesystem
        self.register("list_files", filesystem.list_files)
        self.register("read_file", filesystem.read_file)
        self.register("create_file", filesystem.create_file)
        self.register("edit_file", filesystem.edit_file)
        self.register("delete_file", filesystem.delete_file)
        self.register("create_directory", filesystem.create_directory)
        self.register("search_files", filesystem.search_files)
        self.register("get_project_structure", filesystem.get_project_structure)
        self.register("batch_edit_files", filesystem.batch_edit_files)

        # Terminal & Execution
        self.register("run_command", terminal.run_command)
        self.register("run_tests", terminal.run_tests)
        self.register("analyse_errors", terminal.analyse_errors)
        self.register("fix_errors", terminal.fix_errors)

        # Git
        self.register("git_status", git_tools.git_status)
        self.register("git_diff", git_tools.git_diff)

    def execute_tool(self, tool_name: str, workspace_root: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely execute a tool by name with workspace isolation.
        """
        if tool_name not in self._tools:
            return {
                "success": False,
                "error": f"Unknown tool '{tool_name}'. Available tools: {list(self._tools.keys())}"
            }

        func = self._tools[tool_name]
        try:
            # Inject workspace_root as first positional argument
            return func(workspace_root, **arguments)
        except TypeError as e:
            return {"success": False, "error": f"Invalid arguments for {tool_name}: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Execution error in {tool_name}: {str(e)}"}

    def get_tool_definitions(self) -> list:
        """
        Return Gemini-compatible function schemas for all registered tools.
        """
        return [
            {
                "name": "list_files",
                "description": "List files and directories in the project workspace or subfolder.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "subpath": {"type": "STRING", "description": "Relative directory path (e.g. '.' or 'src')"}
                    }
                }
            },
            {
                "name": "read_file",
                "description": "Read content of an existing source file.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "file_path": {"type": "STRING", "description": "Relative path to the file"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "create_file",
                "description": "Create a new source file or overwrite an existing one with full content.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "file_path": {"type": "STRING", "description": "Relative path of file to create"},
                        "content": {"type": "STRING", "description": "Full file contents"},
                        "overwrite": {"type": "BOOLEAN", "description": "Whether to overwrite existing file"}
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "edit_file",
                "description": "Modify an existing file by replacing a unique exact target snippet with replacement code.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "file_path": {"type": "STRING", "description": "Relative path of file to edit"},
                        "target": {"type": "STRING", "description": "Exact text snippet to be replaced"},
                        "replacement": {"type": "STRING", "description": "New replacement text"}
                    },
                    "required": ["file_path", "target", "replacement"]
                }
            },
            {
                "name": "delete_file",
                "description": "Delete a file from workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "file_path": {"type": "STRING", "description": "Relative path of file to delete"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "create_directory",
                "description": "Create a new directory within workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "dir_path": {"type": "STRING", "description": "Relative path of directory to create"}
                    },
                    "required": ["dir_path"]
                }
            },
            {
                "name": "search_files",
                "description": "Search code, functions, or text across workspace files.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Text or symbol to find"},
                        "pattern": {"type": "STRING", "description": "File glob pattern e.g. '*.py' or '*.ts'"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_project_structure",
                "description": "Generate an ASCII folder hierarchy of the project.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "batch_edit_files",
                "description": (
                    "Create or edit multiple files in a single atomic batch. "
                    "Use this when you need to scaffold several files at once (e.g. an entire module). "
                    "Each entry needs 'file_path' and 'content'; optional 'mode': 'overwrite' (default) or 'replace' (also needs 'target')."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "edits": {
                            "type": "ARRAY",
                            "description": "List of file edit objects. Each has file_path, content, and optional mode/target."
                        }
                    },
                    "required": ["edits"]
                }
            },
            {
                "name": "run_command",
                "description": "Run an approved shell command in the workspace terminal sandbox.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {"type": "STRING", "description": "Shell command to run"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "run_tests",
                "description": "Execute the test suite in the project workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "test_cmd": {"type": "STRING", "description": "Optional custom test command"}
                    }
                }
            },
            {
                "name": "analyse_errors",
                "description": "Analyse error output or logs to identify root causes and suggest fixes.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "error_output": {"type": "STRING", "description": "Error text, traceback, or log to analyse"}
                    },
                    "required": ["error_output"]
                }
            },
            {
                "name": "fix_errors",
                "description": "Apply a targeted exact-text replacement to fix an error in a source file.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "file_path": {"type": "STRING", "description": "Relative path of the file to fix"},
                        "target": {"type": "STRING", "description": "Exact text snippet to replace"},
                        "replacement": {"type": "STRING", "description": "Corrected replacement text"}
                    },
                    "required": ["file_path", "target", "replacement"]
                }
            },
            {
                "name": "git_status",
                "description": "Check current Git status in workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "git_diff",
                "description": "Check Git diff of modified files in workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "file_path": {"type": "STRING", "description": "Optional specific file to diff"}
                    }
                }
            }
        ]


tool_registry = ToolRegistry()
