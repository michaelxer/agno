import asyncio
import threading

from agno.api.api import api
from agno.api.routes import ApiRoutes
from agno.api.schemas.agent import AgentRunCreate
from agno.utils.log import log_debug


def create_agent_run(run: AgentRunCreate) -> None:
    """Telemetry recording for Agent runs - non-blocking."""

    def _send() -> None:
        with api.Client() as api_client:
            try:
                api_client.post(
                    ApiRoutes.RUN_CREATE,
                    json=run.model_dump(exclude_none=True),
                )
            except Exception as e:
                log_debug(f"Could not create Agent run: {e}")

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


async def acreate_agent_run(run: AgentRunCreate) -> None:
    """Telemetry recording for async Agent runs - non-blocking."""

    async def _send() -> None:
        async with api.AsyncClient() as api_client:
            try:
                await api_client.post(
                    ApiRoutes.RUN_CREATE,
                    json=run.model_dump(exclude_none=True),
                )
            except Exception as e:
                log_debug(f"Could not create Agent run: {e}")

    asyncio.create_task(_send())
