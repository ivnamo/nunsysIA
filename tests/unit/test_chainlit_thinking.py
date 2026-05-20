import asyncio

from app.schemas.query import QueryResponse
from chainlit_app import main as chainlit_main


class DummyMessage:
    def __init__(self) -> None:
        self.content = ""
        self.updates: list[str] = []

    async def update(self) -> None:
        self.updates.append(self.content)


def test_thinking_message_cycles_frames() -> None:
    assert chainlit_main._thinking_message(0).startswith("Pensando\n")
    assert chainlit_main._thinking_message(1).startswith("Pensando.\n")
    assert chainlit_main._thinking_message(2).startswith("Pensando..\n")
    assert chainlit_main._thinking_message(3).startswith("Pensando...\n")
    assert chainlit_main._thinking_message(4).startswith("Pensando\n")


def test_thinking_indicator_updates_until_operation_finishes() -> None:
    async def run() -> None:
        original_interval = chainlit_main._THINKING_UPDATE_SECONDS
        chainlit_main._THINKING_UPDATE_SECONDS = 0.001
        message = DummyMessage()

        try:
            response = await chainlit_main._run_with_thinking_indicator(
                operation=slow_query(),
                message=message,  # type: ignore[arg-type]
            )
        finally:
            chainlit_main._THINKING_UPDATE_SECONDS = original_interval

        assert response.answer == "OK"
        assert message.updates
        assert message.updates[0].startswith("Pensando.")

    asyncio.run(run())


def test_thinking_indicator_does_not_delay_fast_operation() -> None:
    async def run() -> None:
        message = DummyMessage()

        response = await chainlit_main._run_with_thinking_indicator(
            operation=fast_query(),
            message=message,  # type: ignore[arg-type]
        )

        assert response.answer == "Rapida"
        assert message.updates == []

    asyncio.run(run())


async def slow_query() -> QueryResponse:
    await asyncio.sleep(0.005)
    return QueryResponse(answer="OK", status="completed")


async def fast_query() -> QueryResponse:
    return QueryResponse(answer="Rapida", status="completed")
