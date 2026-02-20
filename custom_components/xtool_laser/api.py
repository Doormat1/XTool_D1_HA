"""API client for xTool laser devices."""

from __future__ import annotations

import asyncio
import contextlib
import json
import random
import socket
import time
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp
from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_PORT, DEFAULT_WS_PORT


class XToolApiError(Exception):
    """Raised when xTool API communication fails."""


class XToolApiClient:
    """Simple xTool HTTP/WebSocket client."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        self._hass = hass
        self._host = host.strip()
        self._session = async_get_clientsession(hass)
        self._ws_task: asyncio.Task[None] | None = None
        self._ws_stop = asyncio.Event()

    @property
    def host(self) -> str:
        """Return configured host."""
        return self._host

    @property
    def base_url(self) -> str:
        """Return base HTTP API URL."""
        return f"http://{self._host}:{DEFAULT_PORT}"

    @property
    def ws_url(self) -> str:
        """Return WebSocket URL."""
        return f"ws://{self._host}:{DEFAULT_WS_PORT}"

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with self._session.get(url, params=params, timeout=10) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (TimeoutError, ClientError, aiohttp.ContentTypeError, ValueError) as err:
            raise XToolApiError(f"Request failed for {url}: {err}") from err

    async def async_ping(self) -> bool:
        """Return whether device is reachable."""
        payload = await self._get_json("/ping")
        return payload.get("result") == "ok"

    async def async_get_machine_type(self) -> str:
        """Get machine model string."""
        payload = await self._get_json("/getmachinetype")
        return str(payload.get("type", "Unknown xTool"))

    async def async_get_mac(self) -> str | None:
        """Return device MAC address if available."""
        payload = await self._get_json("/system", params={"action": "mac"})
        mac = payload.get("mac")
        return str(mac) if mac else None

    async def async_get_progress(self) -> dict[str, Any]:
        """Get active job progress details."""
        return await self._get_json("/progress")

    async def async_get_working_state(self) -> str:
        """Get current working state code as string."""
        payload = await self._get_json("/system", params={"action": "get_working_sta"})
        return str(payload.get("working", "0"))

    async def async_get_peripheral_status(self) -> dict[str, Any]:
        """Get safety/peripheral status payload."""
        return await self._get_json("/peripherystatus")

    async def async_get_snapshot(self) -> dict[str, Any]:
        """Fetch a combined device snapshot for entities."""
        progress, working_state, peripheral, machine_type = await asyncio.gather(
            self.async_get_progress(),
            self.async_get_working_state(),
            self.async_get_peripheral_status(),
            self.async_get_machine_type(),
        )

        return {
            "progress": float(progress.get("progress", 0.0)),
            "working": int(progress.get("working", 0)),
            "line": int(progress.get("line", 0)),
            "working_state": working_state,
            "machine_type": machine_type,
            "peripheral_status": peripheral,
        }

    async def async_cnc_action(self, action: str) -> bool:
        """Run CNC control action (pause, resume, stop)."""
        payload = await self._get_json("/cnc/data", params={"action": action})
        return payload.get("result") == "ok"

    async def async_discover_devices(self, timeout: int = 3) -> list[dict[str, Any]]:
        """Discover xTool devices via UDP broadcast."""
        return await self._hass.async_add_executor_job(self._discover_devices_sync, timeout)

    @staticmethod
    def _discover_devices_sync(timeout: int) -> list[dict[str, Any]]:
        """Perform blocking UDP discovery using protocol on port 20000."""
        request_id = random.randint(100000, 999999)
        payload = json.dumps({"requestId": request_id}).encode("utf-8")
        found: dict[str, dict[str, Any]] = {}

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", 20000))
            sock.sendto(payload, ("255.255.255.255", 20000))

            end_time = time.monotonic() + max(timeout, 1)
            while time.monotonic() < end_time:
                remaining = end_time - time.monotonic()
                sock.settimeout(remaining)
                try:
                    data, _ = sock.recvfrom(4096)
                except TimeoutError:
                    break

                try:
                    message = json.loads(data.decode("utf-8", errors="ignore"))
                except json.JSONDecodeError:
                    continue

                if message.get("requestId") != request_id:
                    continue

                host = str(message.get("ip", "")).strip()
                if not host:
                    continue

                found[host] = {
                    "host": host,
                    "name": str(message.get("name", "xTool Laser")),
                    "version": str(message.get("version", "")),
                }
        except OSError:
            return []
        finally:
            sock.close()

        return list(found.values())

    async def async_start_ws(
        self, on_message: Callable[[str], Awaitable[None]]
    ) -> None:
        """Start persistent WebSocket listener task."""
        if self._ws_task and not self._ws_task.done():
            return

        self._ws_stop.clear()
        self._ws_task = self._hass.loop.create_task(self._ws_loop(on_message))

    async def async_stop_ws(self) -> None:
        """Stop WebSocket listener task."""
        self._ws_stop.set()
        if self._ws_task is not None:
            self._ws_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ws_task
            self._ws_task = None

    async def _ws_loop(self, on_message: Callable[[str], Awaitable[None]]) -> None:
        """Maintain WebSocket connection and forward messages."""
        while not self._ws_stop.is_set():
            try:
                async with self._session.ws_connect(self.ws_url, heartbeat=30, timeout=15) as ws:
                    async for msg in ws:
                        if self._ws_stop.is_set():
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await on_message(msg.data.strip())
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
            except (TimeoutError, ClientError):
                pass

            if self._ws_stop.is_set():
                return

            await asyncio.sleep(5)
