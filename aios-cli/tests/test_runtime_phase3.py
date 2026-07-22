from unittest.mock import AsyncMock, MagicMock

from aios.runtime.runtime import Runtime, RuntimeConfig


class TestRuntimeMission:
    async def test_run_mission_delegates_to_planner_and_executor(self):
        mock_tool_registry = AsyncMock()
        mock_tool_registry.list = lambda: []
        config = RuntimeConfig(tool_registry=mock_tool_registry)
        runtime = Runtime(config)

        # Mock dependencies since we aren't initializing provider/registry
        mock_planner = AsyncMock()
        from aios.runtime.models import Plan, PlanStatus, Step
        mock_planner.plan = AsyncMock(return_value=Plan(id="123", goal="Test mission", status=PlanStatus.COMPLETED, steps=[Step(id="1", description="Do something", expected_outcome="Done")]))
        mock_planner.replan = AsyncMock(return_value=None)
        
        mock_executor = AsyncMock()
        mock_executor.tool_registry = MagicMock()
        mock_executor.tool_registry.list.return_value = []
        # Mock executor to return a final state indicating completion on the first run
        from aios.runtime.models import AgentState
        mock_executor.run = AsyncMock(return_value=AgentState.COMPLETED)
        
        mock_context = AsyncMock()

        runtime._planner = mock_planner
        runtime._executor = mock_executor
        runtime._context_manager = mock_context
        runtime._initialized = True
        
        from aios.runtime.mission_engine.engine import MissionEngine
        runtime._mission_engine = MissionEngine(
            planner=mock_planner,
            executor=mock_executor,
            context_manager=mock_context,
            event_bus=runtime.event_bus,
            max_iterations_per_step=10,
        )

        # Run mission
        mock_conversation = MagicMock()

        events = []
        async for event in runtime.run_mission("Test mission", conversation=mock_conversation):
            events.append(event)

        # Verify planner was called
        mock_planner.plan.assert_called_once()
        
        # Verify executor was called
        mock_executor.run.assert_called_once()
