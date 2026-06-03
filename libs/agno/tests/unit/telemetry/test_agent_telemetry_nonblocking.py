import asyncio
import time
from threading import Event
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agno.api.agent import acreate_agent_run, create_agent_run
from agno.api.schemas.agent import AgentRunCreate


def test_create_agent_run_returns_before_http_post_completes():
    """Sync telemetry returns immediately while the HTTP request runs in the background."""
    run = AgentRunCreate(session_id="session-id", run_id="run-id")
    post_started = Event()

    def slow_post(*args, **kwargs):
        post_started.set()
        time.sleep(2)

    mock_client = MagicMock()
    mock_client.post.side_effect = slow_post
    mock_client_context = MagicMock()
    mock_client_context.__enter__.return_value = mock_client

    with patch("agno.api.agent.api.Client", return_value=mock_client_context):
        start_time = time.perf_counter()
        create_agent_run(run)
        elapsed = time.perf_counter() - start_time

        assert elapsed < 0.1
        assert post_started.wait(timeout=1)


@pytest.mark.asyncio
async def test_acreate_agent_run_returns_before_http_post_completes():
    """Async telemetry returns immediately while the HTTP request runs in the background."""
    run = AgentRunCreate(session_id="session-id", run_id="run-id")
    post_started = asyncio.Event()
    created_tasks = []
    original_create_task = asyncio.create_task

    async def slow_post(*args, **kwargs):
        post_started.set()
        await asyncio.sleep(2)

    def create_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    mock_client = AsyncMock()
    mock_client.post.side_effect = slow_post
    mock_client_context = AsyncMock()
    mock_client_context.__aenter__.return_value = mock_client

    with (
        patch("agno.api.agent.api.AsyncClient", return_value=mock_client_context),
        patch("agno.api.agent.asyncio.create_task", side_effect=create_task),
    ):
        start_time = time.perf_counter()
        await acreate_agent_run(run)
        elapsed = time.perf_counter() - start_time

        assert elapsed < 0.1
        await asyncio.wait_for(post_started.wait(), timeout=1)

    for task in created_tasks:
        task.cancel()
    await asyncio.gather(*created_tasks, return_exceptions=True)
