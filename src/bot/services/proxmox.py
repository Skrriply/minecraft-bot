import logging

import aiohttp
from config import settings

logger = logging.getLogger("ProxmoxService")


class ProxmoxService:
    def __init__(self, session: aiohttp.ClientSession):
        self.session: aiohttp.ClientSession = session
        token: str = f"PVEAPIToken={settings.PROXMOX_USER}!{settings.PROXMOX_TOKEN_ID}={settings.PROXMOX_TOKEN_SECRET}"
        self.headers: dict[str, str] = {
            "Authorization": token,
            "Accept": "application/json",
        }
        self.base_url: str = settings.PROXMOX_URL

    async def shutdown_host(self) -> bool:
        url = f"{self.base_url}/api2/json/nodes/{settings.PROXMOX_NODE}/status"
        payload = {"command": "shutdown"}

        try:
            async with self.session.post(
                url, headers=self.headers, data=payload, ssl=False
            ) as r:
                r.raise_for_status()
                logger.info("Proxmox shutdown initiated.")
                return True
        except aiohttp.ClientResponseError as e:
            logger.exception(f'API Error for "{url}": {e.status}.')
        except aiohttp.ClientConnectionError:
            logger.exception(f'"{url}" is unavailable!')

        return False
