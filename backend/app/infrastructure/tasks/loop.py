"""One event loop per worker process, reused across every task invocation.

The DI container's async resources (the SQLAlchemy engine's connection pool,
the Redis client, the Qdrant client) are lazy singletons — created once, on
first use, and then bound to whichever event loop was running at that moment.
`asyncio.run()` creates a *new* loop and closes it after every single task; the
first task to touch one of those singletons binds it to that loop, and every
task after it runs on a different (new) loop, so asyncpg/redis-py/qdrant raise
"Future attached to a different loop" the moment they touch the same pooled
connection. Running every task on one persistent loop for the process's whole
lifetime keeps those singletons valid for as long as the worker lives.
"""
import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop


def run(coro: Coroutine[Any, Any, T]) -> T:
    return _get_loop().run_until_complete(coro)
