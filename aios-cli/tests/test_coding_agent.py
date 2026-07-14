from __future__ import annotations

from pathlib import Path

import pytest

from collections.abc import AsyncIterator

from aios.core.models import Conversation, StreamChunk
from aios.executor.coding_agent import CodingAgent
from aios.providers.base import LLMProvider
from aios.tools.registry import ToolRegistry
from aios.workspace import WorkspaceContext


class MockProvider(LLMProvider):
    def __init__(self, responses: list):
        super().__init__(base_url="http://mock", api_key="", model="mock-model")
        self.responses = responses
        self.current_index = 0

    async def chat(self, messages, tools=None, **kwargs):
        if self.current_index < len(self.responses):
            resp = self.responses[self.current_index]
            self.current_index += 1
            return resp
        return {"content": "Task completed.", "tool_calls": []}

    async def complete(self, prompt, **kwargs):
        return "Mock completion"

    async def list_models(self):
        return ["mock-model"]

    async def stream(self, messages, **kwargs):
        # Not used in agent.run
        yield "Streaming not implemented in mock"

    async def health_check(self): return True
    async def has_model(self, model): return True

    async def stream_chat(self, messages, temperature=0.2, tools=None) -> AsyncIterator[StreamChunk]:
        # Used when streaming is enabled in engine.run()
        resp = await self.chat(messages, temperature=temperature, tools=tools)
        content = resp.get("content")
        if content:
            yield StreamChunk(type="content", content=content)
        tool_calls = resp.get("tool_calls")
        if tool_calls:
            yield StreamChunk(type="tool_call", tool_calls=tool_calls)
        yield StreamChunk(type="done")

@pytest.mark.asyncio
async def test_coding_agent_confirmation_flow(tmp_path: Path):
    # Setup
    tool_registry = ToolRegistry(WorkspaceContext(tmp_path))
    # We use a real FilesystemTool but point it to tmp_path via mock or by changing cwd if possible.
    # For simplicity, we'll mock the tool execution or use a temporary file.
    
    # Create a dummy file for the agent to edit
    test_file = tmp_path / "hello.py"
    test_file.write_text("print('hello')")

    # Mock LLM responses:
    # 1. Request to read file
    # 2. Request to replace text
    # 3. Final answer
    responses = [
        {
            "content": "I will read the file first.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "filesystem",
                        "arguments": {"action": "read_file", "path": str(test_file)}
                    }
                }
            ]
        },
        {
            "content": "Now I will change the text.",
            "tool_calls": [
                {
                    "id": "call_2",
                    "function": {
                        "name": "filesystem",
                        "arguments": {
                            "action": "replace_text", 
                            "path": str(test_file), 
                            "old_text": "print('hello')", 
                            "new_text": "print('world')"
                        }
                    }
                }
            ]
        },
        {
            "content": "Done!",
            "tool_calls": []
        }
    ]
    
    provider = MockProvider(responses)
    
    # Mock confirmation callback: Always say YES
    async def confirm_yes(name, args): return True
    
    conversation = Conversation(provider="mock", model="mock")
    agent = CodingAgent(provider, tool_registry, confirmation_callback=confirm_yes)
    
    result = await agent.run(conversation)
    
    assert "Done!" in result
    assert test_file.read_text() == "print('world')"

@pytest.mark.asyncio
async def test_coding_agent_denied_action(tmp_path: Path):
    # Setup
    tool_registry = ToolRegistry(WorkspaceContext(tmp_path))
    test_file = tmp_path / "secret.txt"
    test_file.write_text("secret data")

    responses = [
        {
            "content": "I will delete the secret file.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "filesystem",
                        "arguments": {"action": "delete", "path": str(test_file)}
                    }
                }
            ]
        },
        {
            "content": "The user denied me, so I'll stop.",
            "tool_calls": []
        }
    ]
    
    provider = MockProvider(responses)
    
    # Mock confirmation callback: Always say NO
    async def confirm_no(name, args): return False
    
    conversation = Conversation(provider="mock", model="mock")
    agent = CodingAgent(provider, tool_registry, confirmation_callback=confirm_no)
    
    result = await agent.run(conversation)
    
    assert "The user denied me" in result
    assert test_file.exists() # File should NOT be deleted

@pytest.mark.asyncio
async def test_coding_agent_safe_action_no_confirm(tmp_path: Path):
    # Setup
    tool_registry = ToolRegistry(WorkspaceContext(tmp_path))
    # Create a folder and some files
    proj_dir = tmp_path / "my_proj"
    proj_dir.mkdir()
    (proj_dir / "a.py").write_text("a")
    (proj_dir / "b.py").write_text("b")

    responses = [
        {
            "content": "Listing files.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "filesystem",
                        "arguments": {"action": "list_files", "path": str(proj_dir)}
                    }
                }
            ]
        },
        {
            "content": "Finished.",
            "tool_calls": []
        }
    ]
    
    provider = MockProvider(responses)
    
    # Confirmation callback that tracks calls
    confirmed_calls = []
    async def confirm_track(name, args):
        confirmed_calls.append(name)
        return True
    
    conversation = Conversation(provider="mock", model="mock")
    agent = CodingAgent(provider, tool_registry, confirmation_callback=confirm_track)
    
    await agent.run(conversation)
    
    # list_files should NOT trigger a confirmation
    assert len(confirmed_calls) == 0
