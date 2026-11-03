"""
Phase 3 end-to-end agent loop test.
Tests: AgentEngine with real Gemini function calling, file creation, tool logging.
"""
import asyncio
import os
import tempfile
import sys

# Ensure workspace path is clean
ws = os.path.join(tempfile.gettempdir(), "devpilot_test_ws")
os.makedirs(ws, exist_ok=True)

async def test_agent_loop():
    from app.agent.engine import AgentEngine
    from app.tools.registry import ToolRegistry

    registry = ToolRegistry()
    engine = AgentEngine(workspace_root=ws, tool_registry=registry, db=None)

    print(f"[TEST] Workspace: {ws}")
    print(f"[TEST] Tools available: {len(registry._tools)}")
    print("[TEST] Sending prompt to agent...")

    result = await engine.run(
        prompt=(
            "Create a Python file named fibonacci.py with a function called fibonacci(n) "
            "that returns the nth Fibonacci number using recursion. "
            "Also create a test file test_fibonacci.py that tests the function for n=0,1,5,10."
        ),
        max_iterations=8,
    )

    print("\n=== REPLY (first 600 chars) ===")
    print(result["reply"][:600])

    print("\n=== TOOL CALLS LOG ===")
    for tc in result["tool_calls_log"]:
        success = tc["result"].get("success", False)
        print(f"  [iter {tc['iteration']}] {tc['tool']}({list(tc['args'].keys())}) -> {'OK' if success else 'FAILED'}")
        if not success:
            print(f"    ERROR: {tc['result'].get('error', 'unknown')}")

    print("\n=== FILES CHANGED ===")
    for f in result["files_changed"]:
        print(f"  - {f}")

    print("\n=== EXECUTION LOGS ===")
    for log in result["logs"]:
        print(f"  {log}")

    # Verify files were created
    fib_file = os.path.join(ws, "fibonacci.py")
    test_file = os.path.join(ws, "test_fibonacci.py")
    created_fib = os.path.exists(fib_file)
    created_test = os.path.exists(test_file)

    print(f"\n=== FILE VERIFICATION ===")
    print(f"  fibonacci.py created: {created_fib}")
    print(f"  test_fibonacci.py created: {created_test}")

    if created_fib:
        with open(fib_file) as f:
            print(f"\n--- fibonacci.py ---\n{f.read()}")

    assert len(result["tool_calls_log"]) > 0, "Expected at least one tool call"
    assert result["reply"], "Expected a non-empty reply"
    print("\n[PASS] Phase 3 agent loop test PASSED!")

if __name__ == "__main__":
    asyncio.run(test_agent_loop())
