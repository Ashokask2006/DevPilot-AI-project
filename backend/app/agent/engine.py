"""
AgentEngine — Advanced Gemini Function-Calling Agent Loop for DevPilot AI.

Implements a multi-step agentic loop:
1. Build Gemini tool schemas from ToolRegistry.
2. Start a Gemini chat session with tools + system instruction.
3. Send the user prompt → receive response.
4. If function_calls present → execute tool → send back result → loop.
5. Repeat until no more function calls or max_iterations reached.
6. Persist ToolExecution records to the database.
7. Return structured result: reply, tool_calls_log, logs, files_changed.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.agent.prompts import DEVPILOT_SYSTEM_INSTRUCTION
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    Autonomous agent that orchestrates Gemini function-calling with real tools.
    """

    def __init__(
        self,
        workspace_root: str,
        tool_registry: ToolRegistry,
        db=None,
    ):
        self.workspace_root = workspace_root
        self.registry = tool_registry
        self.db = db
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        prompt: str,
        conversation_id: int | None = None,
        project_id: int | None = None,
        task_id: int | None = None,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """
        Execute the agentic loop for the given user prompt.

        Returns:
            {
                "reply": str,               # Final Gemini text response
                "tool_calls_log": list,     # List of {tool, args, result} dicts
                "logs": list[str],          # Human-readable log lines
                "files_changed": list[str], # Files touched during execution
            }
        """
        logs: list[str] = []
        tool_calls_log: list[dict] = []
        files_changed: list[str] = []
        reply = ""

        logs.append(f"[AgentEngine] Starting agent loop — model: {self.model}")
        logs.append(f"[AgentEngine] Workspace: {self.workspace_root}")
        logs.append(f"[AgentEngine] Prompt: {prompt[:120]}...")

        # Build Gemini tool list from registry
        gemini_tools = self._build_gemini_tools()
        logs.append(f"[AgentEngine] Registered {len(self.registry.get_tool_definitions())} tools")

        # Compose system instruction
        system_instruction = self._build_system_instruction()

        # Create chat session
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=gemini_tools,
            temperature=0.2,
        )

        try:
            chat = self.client.chats.create(model=self.model, config=config)
        except Exception as e:
            logs.append(f"[AgentEngine] ERROR creating chat session: {e}")
            return {
                "reply": f"Failed to initialise AI session: {e}",
                "tool_calls_log": tool_calls_log,
                "logs": logs,
                "files_changed": files_changed,
            }

        # Send initial prompt
        current_message: Any = prompt
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logs.append(f"[AgentEngine] Iteration {iteration}/{max_iterations}")

            try:
                response = chat.send_message(current_message)
            except Exception as e:
                logs.append(f"[AgentEngine] ERROR sending message: {e}")
                reply = f"Agent error during iteration {iteration}: {e}"
                break

            # Collect function calls from all candidate parts
            fn_calls = self._extract_function_calls(response)

            if not fn_calls:
                # No more tool calls — extract final text reply
                reply = self._extract_text(response)
                logs.append(f"[AgentEngine] Final reply received ({len(reply)} chars)")
                break

            # Execute each function call and build response parts
            response_parts: list[types.Part] = []

            for fc in fn_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}

                logs.append(f"[AgentEngine] Calling tool: {tool_name}({list(tool_args.keys())})")

                # Execute tool
                result = self._execute_tool(tool_name, tool_args)

                # Track files changed
                if result.get("success") and tool_name in ("create_file", "edit_file", "delete_file"):
                    fp = tool_args.get("file_path", "")
                    if fp and fp not in files_changed:
                        files_changed.append(fp)
                if result.get("success") and tool_name == "batch_edit_files":
                    for change in result.get("changes", []):
                        fp = change.get("file_path", "")
                        if fp and fp not in files_changed:
                            files_changed.append(fp)

                logs.append(
                    f"[AgentEngine] Tool '{tool_name}' result: "
                    f"{'success' if result.get('success') else 'FAILED'}"
                )

                # Record in log
                tool_calls_log.append(
                    {
                        "iteration": iteration,
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                # Persist to DB if available
                self._persist_tool_execution(
                    task_id=task_id,
                    tool_name=tool_name,
                    tool_input=tool_args,
                    tool_output=result,
                )

                # Build Gemini function response part
                response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response=result,
                    )
                )

            # Send all tool results back in one message
            current_message = response_parts

        else:
            logs.append(f"[AgentEngine] WARNING: Reached max_iterations ({max_iterations})")
            reply = reply or "Agent reached maximum iteration limit. Partial results may be available."

        return {
            "reply": reply,
            "tool_calls_log": tool_calls_log,
            "logs": logs,
            "files_changed": files_changed,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_gemini_tools(self) -> list[types.Tool]:
        """Convert ToolRegistry definitions to Gemini Tool objects."""
        definitions = self.registry.get_tool_definitions()
        function_declarations = []

        for defn in definitions:
            params = defn.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])

            # Build property schemas
            gemini_properties = {}
            for prop_name, prop_info in properties.items():
                ptype = prop_info.get("type", "STRING").upper()

                if ptype == "BOOLEAN":
                    gemini_properties[prop_name] = types.Schema(
                        type=types.Type.BOOLEAN,
                        description=prop_info.get("description", ""),
                    )
                elif ptype == "INTEGER":
                    gemini_properties[prop_name] = types.Schema(
                        type=types.Type.INTEGER,
                        description=prop_info.get("description", ""),
                    )
                elif ptype == "ARRAY":
                    gemini_properties[prop_name] = types.Schema(
                        type=types.Type.ARRAY,
                        description=prop_info.get("description", ""),
                        items=types.Schema(type=types.Type.OBJECT),
                    )
                else:
                    gemini_properties[prop_name] = types.Schema(
                        type=types.Type.STRING,
                        description=prop_info.get("description", ""),
                    )

            # Build parameter schema
            if gemini_properties:
                param_schema = types.Schema(
                    type=types.Type.OBJECT,
                    properties=gemini_properties,
                    required=required if required else None,
                )
            else:
                param_schema = types.Schema(type=types.Type.OBJECT, properties={})

            function_declarations.append(
                types.FunctionDeclaration(
                    name=defn["name"],
                    description=defn.get("description", ""),
                    parameters=param_schema,
                )
            )

        return [types.Tool(function_declarations=function_declarations)]

    def _build_system_instruction(self) -> str:
        """Build the full system instruction for the agent."""
        return (
            DEVPILOT_SYSTEM_INSTRUCTION
            + f"\n\n## Current Workspace\n`{self.workspace_root}`\n\n"
            "When writing code, ALWAYS use the file tools (create_file, edit_file, batch_edit_files) "
            "to save code to disk rather than only returning code in your reply. "
            "Use run_command to install dependencies or run tests. "
            "Use get_project_structure to understand the codebase before making changes."
        )

    def _extract_function_calls(self, response) -> list:
        """Extract all function calls from a Gemini response."""
        fn_calls = []
        try:
            if hasattr(response, "function_calls") and response.function_calls:
                fn_calls = list(response.function_calls)
        except Exception:
            pass

        if not fn_calls:
            # Fallback: check candidates → content → parts
            try:
                for candidate in response.candidates or []:
                    for part in candidate.content.parts or []:
                        if hasattr(part, "function_call") and part.function_call:
                            fn_calls.append(part.function_call)
            except Exception:
                pass

        return fn_calls

    def _extract_text(self, response) -> str:
        """Extract text content from a Gemini response."""
        try:
            if hasattr(response, "text") and response.text:
                return response.text
        except Exception:
            pass

        # Fallback: scan parts
        try:
            for candidate in response.candidates or []:
                parts_text = []
                for part in candidate.content.parts or []:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
                if parts_text:
                    return "\n".join(parts_text)
        except Exception:
            pass

        return "(No text response from model)"

    def _execute_tool(self, tool_name: str, args: dict) -> dict:
        """Execute a tool via the registry with workspace isolation."""
        # Tools that do NOT take workspace_root as first arg
        no_workspace_tools: set[str] = set()

        if tool_name in no_workspace_tools:
            return self.registry._tools[tool_name](**args)

        return self.registry.execute_tool(tool_name, self.workspace_root, args)

    def _persist_tool_execution(
        self,
        task_id: int | None,
        tool_name: str,
        tool_input: dict,
        tool_output: dict,
    ) -> None:
        """Persist a ToolExecution record to the database."""
        if self.db is None or task_id is None:
            return

        try:
            import json
            from app.models.models import ToolExecution

            record = ToolExecution(
                task_id=task_id,
                tool_name=tool_name,
                tool_input=json.dumps(tool_input),
                tool_output=json.dumps(tool_output),
                success=tool_output.get("success", False),
            )
            self.db.add(record)
            self.db.commit()
        except Exception as exc:
            logger.warning(f"Failed to persist tool execution record: {exc}")
