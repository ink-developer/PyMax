import asyncio
import traceback
from collections.abc import Awaitable, Callable
from typing import Any

from pymax.protocols import ClientProtocol


class SchedulerMixin(ClientProtocol):
    async def _run_periodic(
        self, func: Callable[[], Any | Awaitable[Any]], interval: float
    ) -> None:
        while True:
            try:
                result = func()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                tb = traceback.format_exc()
                self.logger.error(f"Error in scheduled task {func}: {e}")
                raise
            await asyncio.sleep(interval)

    async def _start_scheduled_tasks(self) -> None:
        for func, interval in self._scheduled_tasks:
            task = asyncio.create_task(self._run_periodic(func, interval))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
