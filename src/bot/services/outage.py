import logging
from datetime import datetime

import aiohttp
from config import settings
from models import OutageResponse

logger = logging.getLogger("OutageService")


class OutageService:
    """Service for interacting with Svitlo.live API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """
        Initializes the class.

        Args:
            session: HTTP session for creating requests.
        """
        self.session: aiohttp.ClientSession = session

    async def check_outage_at(self, check_time: datetime) -> bool:
        """
        Checks whether the shutdown is scheduled at the specified time.

        Args:
            time: Time for which will be checked.

        Returns:
            `True` if a shutdown is scheduled, otherwise `False`.
        """
        try:
            async with self.session.get(settings.OUTAGE_API_URL) as r:
                r.raise_for_status()
                raw_data = await r.json()

            data = OutageResponse(**raw_data)

            # 1. Retrieves region data
            region = next(
                (reg for reg in data.regions if reg.cpu == settings.REGION_CPU), None
            )
            if not region or not region.schedule:
                return False

            # 2. Retrieves group schedule data
            group_schedule = region.schedule.get(settings.GROUP_ID)
            if not group_schedule:
                return False

            # 3. Creates schedule
            date_key = check_time.strftime("%Y-%m-%d")
            minute = 0 if check_time.minute < 30 else 30
            time_key = f"{check_time.hour:02d}:{minute:02d}"

            day_schedule = group_schedule.get(date_key)
            if not day_schedule:
                return False

            return day_schedule.get(time_key, 0) >= 2
        except aiohttp.ClientResponseError as e:
            logger.error(f"API Error for {settings.OUTAGE_API_URL}: {e.status}.")
        except Exception:
            logger.exception("Unexcepted error!")

        return False
