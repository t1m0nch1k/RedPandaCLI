import asyncio
from pathlib import Path

from aios.cli.main import _build_registry, get_provider_and_model
from aios.core.models import Conversation
from aios.runtime.runtime import Runtime, RuntimeConfig


async def main():
    # 1. Get the actual provider and tool registry
    provider_obj, settings, provider_name, model_name = get_provider_and_model(None, None)
    tool_registry = _build_registry(settings)
    
    # 2. Build the runtime configuration
    config = RuntimeConfig(
        workspace_root=Path.cwd(),
        provider=provider_obj,
        tool_registry=tool_registry,
        max_iterations=15,
        permission_profile="yolo",
        system_prompt="You are a self-improving AI. Accomplish the user's goal by using the provided tools."
    )
    
    # Enable logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 3. Create conversation
    conversation = Conversation(provider=provider_name, model=model_name)
    
    # 4. Instantiate Runtime
    async with Runtime(config) as runtime:
        goal = "Add a simple function named `hello_self_improvement` to `src/aios/runtime/runtime.py` that returns the string 'Self-improvement successful!'. Also add a unit test for it in `tests/test_runtime_phase3.py`."
        
        print(f"--- Starting Mission ---\nGoal: {goal}\n")
        
        # 5. Run mission
        async for event in runtime.run_mission(goal, conversation):
            event_type = event.get("event")
            if event_type == "planning":
                print("[Planning started]")
            elif event_type == "plan_created":
                print(f"[Plan Created] {len(event['plan'].steps)} steps")
                for s in event["plan"].steps:
                    print(f"  - {s.description}")
            elif event_type == "step_started":
                print(f"\n[Step Started] {event['step'].description}")
            elif event_type == "step_completed":
                print(f"[Step Completed] Result: {event['result']}")
            elif event_type == "error":
                print(f"[Error] {event['message']}")
            elif event_type == "mission_completed":
                print("\n--- Mission Completed ---")
            else:
                print(f"[Event] {event_type}")

if __name__ == "__main__":
    asyncio.run(main())
