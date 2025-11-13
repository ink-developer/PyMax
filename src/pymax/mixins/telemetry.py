import asyncio
import random
import time

from pymax.exceptions import Error
from pymax.interfaces import ClientProtocol
from pymax.navigation import Navigation
from pymax.payloads import (
    NavigationEventParams,
    NavigationEventPayload,
    NavigationPayload,
)
from pymax.static.enum import Opcode


class TelemetryMixin(ClientProtocol):
    async def _send_navigation_event(
        self, events: list[NavigationEventPayload]
    ) -> None:
        try:
            payload = NavigationPayload(events=events).model_dump(by_alias=True)
            data = await self._send_and_wait(
                opcode=Opcode.LOG,
                payload=payload,
            )
            payload_data = data.get("payload", {})
            if payload_data and payload_data.get("error"):
                error = payload_data.get("error")
                self.logger.error("Navigation event error: %s", error)
        except Exception:
            self.logger.warning("Failed to send navigation event", exc_info=True)
            return

    async def _send_cold_start(self) -> None:
        if not self.me:
            self.logger.error("Cannot send cold start, user not set")
            return

        payload = NavigationEventPayload(
            event="COLD_START",
            time=int(time.time() * 1000),
            user_id=self.me.id,
            params=NavigationEventParams(
                action_id=self._action_id,
                screen_to=Navigation.get_screen_id("chats_list_tab"),
                screen_from=1,
                source_id=1,
                session_id=self._session_id,
            ),
        )

        self._action_id += 1

        await self._send_navigation_event([payload])

    async def _send_random_navigation(self) -> None:
        if not self.me:
            self.logger.error("Cannot send navigation event, user not set")
            return

        screen_from = self._current_screen
        screen_to = Navigation.get_random_navigation(screen_from)

        self._action_id += 1
        self._current_screen = screen_to

        payload = NavigationEventPayload(
            event="NAV",
            time=int(time.time() * 1000),
            user_id=self.me.id,
            params=NavigationEventParams(
                action_id=self._action_id,
                screen_from=Navigation.get_screen_id(screen_from),
                screen_to=Navigation.get_screen_id(screen_to),
                source_id=1,
                session_id=self._session_id,
            ),
        )

        await self._send_navigation_event([payload])

    def _get_random_sleep_time(self) -> int:
        # TODO: вынести в статик
        sleep_options = [
            (1000, 3000),
            (300, 1000),
            (60, 300),
            (5, 60),
            (5, 20),
        ]

        weights = [0.05, 0.10, 0.15, 0.20, 0.50]

        low, high = random.choices(  # nosec B311
            sleep_options, weights=weights, k=1
        )[0]
        return random.randint(low, high)  # nosec B311

    async def _start(self) -> None:
        if not self.is_connected:
            self.logger.error("Cannot start telemetry, client not connected")
            return

        await self._send_cold_start()

        try:
            while self.is_connected:
                await self._send_random_navigation()
                await asyncio.sleep(self._get_random_sleep_time())

        except asyncio.CancelledError:
            self.logger.debug("Telemetry task cancelled")
        except Exception:
            self.logger.warning("Telemetry task failed", exc_info=True)
