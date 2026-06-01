from unittest.mock import MagicMock

import pytest

pytest.importorskip("ag_ui", reason="ag_ui not installed")

from agno.os.interfaces.agui.router import run_agent, run_team


class FakeRunInput:
    def __init__(self, *, context=None, state=None):
        self.messages = [MagicMock(role="user", content="test")]
        self.thread_id = "test-thread"
        self.run_id = "test-run"
        self.forwarded_props = None
        self.state = state
        self.context = context


class CaptureKwargsTeam:
    def __init__(self):
        self.captured_kwargs = {}

    async def arun(self, **kwargs):
        self.captured_kwargs = kwargs
        return
        yield


class CaptureKwargsAgent:
    def __init__(self):
        self.captured_kwargs = {}

    async def arun(self, **kwargs):
        self.captured_kwargs = kwargs
        return
        yield


@pytest.mark.asyncio
async def test_run_team_passes_stream_events_not_stream_steps():
    fake_team = CaptureKwargsTeam()
    run_input = FakeRunInput()

    events = []
    async for event in run_team(fake_team, run_input):
        events.append(event)

    assert fake_team.captured_kwargs.get("stream") is True
    assert fake_team.captured_kwargs.get("stream_events") is True
    assert "stream_steps" not in fake_team.captured_kwargs


@pytest.mark.asyncio
async def test_run_agent_passes_stream_events():
    fake_agent = CaptureKwargsAgent()
    run_input = FakeRunInput()

    events = []
    async for event in run_agent(fake_agent, run_input):
        events.append(event)

    assert fake_agent.captured_kwargs.get("stream") is True
    assert fake_agent.captured_kwargs.get("stream_events") is True
    assert "stream_steps" not in fake_agent.captured_kwargs


# ---------------------------------------------------------------------------
# AG-UI readable context flow (PR for issue #7805)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_agent_no_context_omits_add_dependencies_to_context_kwarg():
    """When no AGUI context is sent, the kwarg should NOT be passed —
    preserves the agent's own `add_dependencies_to_context` configuration.
    """
    fake_agent = CaptureKwargsAgent()
    run_input = FakeRunInput(context=None)

    events = []
    async for event in run_agent(fake_agent, run_input):
        events.append(event)

    assert "add_dependencies_to_context" not in fake_agent.captured_kwargs
    assert "dependencies" not in fake_agent.captured_kwargs


@pytest.mark.asyncio
async def test_run_agent_with_context_injects_dependencies_and_forces_kwarg():
    """When AGUI context is present, it should be merged into dependencies
    (preserving any agent.dependencies) and `add_dependencies_to_context=True`
    should be passed."""
    fake_agent = CaptureKwargsAgent()
    fake_agent.dependencies = {"existing_dep": "preserved"}
    context = [MagicMock(description="user_name", value="Alice")]
    run_input = FakeRunInput(context=context)

    events = []
    async for event in run_agent(fake_agent, run_input):
        events.append(event)

    assert fake_agent.captured_kwargs.get("add_dependencies_to_context") is True
    deps = fake_agent.captured_kwargs.get("dependencies")
    assert deps is not None
    assert deps["existing_dep"] == "preserved"
    assert deps["agui_context"] == [{"description": "user_name", "value": "Alice"}]
    # session_state must remain untouched (no agui_context pollution)
    session_state = fake_agent.captured_kwargs.get("session_state")
    assert session_state is None or "agui_context" not in session_state


@pytest.mark.asyncio
async def test_run_team_merges_agui_context_into_dependencies():
    """Team path mirrors agent: context flows into dependencies (not
    session_state) and add_dependencies_to_context=True is forced."""
    fake_team = CaptureKwargsTeam()
    context = [MagicMock(description="team_mode", value="route")]
    run_input = FakeRunInput(context=context)

    events = []
    async for event in run_team(fake_team, run_input):
        events.append(event)

    assert fake_team.captured_kwargs.get("add_dependencies_to_context") is True
    deps = fake_team.captured_kwargs.get("dependencies")
    assert deps is not None
    assert deps["agui_context"] == [{"description": "team_mode", "value": "route"}]
    # session_state must remain untouched
    session_state = fake_team.captured_kwargs.get("session_state")
    assert session_state is None or "agui_context" not in session_state
