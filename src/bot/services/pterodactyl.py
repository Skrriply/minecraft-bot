import asyncio
import logging

import aiohttp
from config import settings

logger = logging.getLogger("PteroService")


class PterodactylService:
    """
    Service for interacting with the Pterodactyl Client API.

    Docs: https://pterodactyl-api-docs.netvpx.com/docs/api/client
    """

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """
        Initializes the class.

        Args:
            session: HTTP session for creating requests.
        """
        self.session: aiohttp.ClientSession = session
        self.headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.PTERODACTYL_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.base_url: str = f"{settings.PTERODACTYL_URL}/api/client/servers/{settings.PTERODACTYL_SERVER_ID}"

    async def get_server_state(self) -> str:
        """
        Returns the server status.

        Returns:
            The server status (e.g. "running", "starting" etc.) if successful, otherwise "unknown".
        """
        url = f"{self.base_url}/resources"

        try:
            async with self.session.get(url, headers=self.headers) as r:
                r.raise_for_status()
                data = await r.json()
                return data["attributes"]["current_state"]
        except aiohttp.ClientResponseError as e:
            logger.exception(f'API Error for "{url}": {e.status}.')
        except KeyError:
            logger.exception("Response parsing error.")
        except aiohttp.ClientConnectionError:
            logger.exception(f'"{url}" is unavailable!')

        return "unknown"

    async def send_command(self, command: str) -> None:
        """
        Sends a Minecraft command to the server.

        Args:
            command: The command that will be sent.
        """
        url = f"{self.base_url}/command"
        payload = {"command": command}

        logger.debug(f'Sending command: "{payload["command"]}"...')
        try:
            async with self.session.post(url, headers=self.headers, json=payload) as r:
                r.raise_for_status()
        except aiohttp.ClientResponseError as e:
            logger.exception(f'API Error for "{url}": {e.status}.')
        except aiohttp.ClientConnectionError:
            logger.exception(f'"{url}" is unavailable!')

    async def set_power_state(self, signal: str) -> None:
        """
        Sets the server power state.

        Args:
            signal: Power state to set (e.g. start, stop, restart, kill).
        """
        url = f"{self.base_url}/power"
        payload = {"signal": signal}

        logger.debug(f'Setting power state to: "{payload["signal"]}"...')
        try:
            async with self.session.post(url, headers=self.headers, json=payload) as r:
                if r.status == 204:  # Not an error
                    return

                r.raise_for_status()
        except aiohttp.ClientResponseError as e:
            logger.exception(f'API Error for "{url}": {e.status}.')
        except aiohttp.ClientConnectionError:
            logger.exception(f'"{url}" is unavailable!')

    async def wait_until_state(
        self, power_state: str, timeout_seconds: int = 300
    ) -> bool:
        iterations = timeout_seconds // 5
        for _ in range(iterations):
            await asyncio.sleep(5)
            if await self.get_server_state() == power_state:
                return True

        return False
