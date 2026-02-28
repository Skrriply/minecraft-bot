from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from enum import Enum
from http import HTTPMethod
from typing import TYPE_CHECKING, Any

from camoufox.async_api import AsyncCamoufox
from core.config import settings
from pydantic import BaseModel
from services.base import BaseAPIClient

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

    from core.cache import CacheManager
    from playwright.async_api import Cookie, Route

logger = logging.getLogger(__name__)


class PowerStatus(str, Enum):
    """The possible states of electrical power."""

    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class OutageScheduleResponse(BaseModel):
    """The parsed power outage schedule"""

    current_status: PowerStatus | None = None
    next_outage_time: str | None = None
    next_power_on_time: str | None = None


class DTEKScraperService(BaseAPIClient):
    """Service for scraping and parsing DTEK power outage schedules."""

    DTEK_URLS: dict[str, str] = {
        "kem": "https://www.dtek-kem.com.ua",  # Київ
        "krem": "https://www.dtek-krem.com.ua",  # Київська обл.
        "dnem": "https://www.dtek-dnem.com.ua",  # Дніпровська обл.
        "oem": "https://www.dtek-oem.com.ua",  # Одеська обл.
        "dem": "https://www.dtek-dem.com.ua",  # Донецька обл.
    }
    IGNORED_COOKIE_ATTRIBUTES: set[str] = {
        "expires",
        "path",
        "comment",
        "domain",
        "max-age",
        "secure",
        "httponly",
        "version",
        "samesite",
    }
    RAW_STATUS_MAPPING: dict[str, tuple[PowerStatus, PowerStatus]] = {
        "yes": (PowerStatus.YES, PowerStatus.YES),
        "no": (PowerStatus.NO, PowerStatus.NO),
        "maybe": (PowerStatus.MAYBE, PowerStatus.MAYBE),
        "first": (PowerStatus.NO, PowerStatus.YES),
        "second": (PowerStatus.YES, PowerStatus.NO),
        "mfirst": (PowerStatus.MAYBE, PowerStatus.YES),
        "msecond": (PowerStatus.YES, PowerStatus.MAYBE),
    }

    def __init__(self, cache_manager: CacheManager) -> None:
        """
        Initializes the class.

        Args:
            cache_manager: An injected instance of the cache manager.
        """
        url: str = self.DTEK_URLS[settings.DTEK_REGION]
        # headers: dict[str, str] = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:120.0) Gecko/20100101 Firefox/120.0",
        #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        # }
        super().__init__(cache_manager, url)

        self.region: str = settings.DTEK_REGION
        self.city: str = settings.DTEK_CITY
        self.street: str = settings.DTEK_STREET
        self.house: str = settings.DTEK_HOUSE
        self.timezone: ZoneInfo = settings.TIMEZONE

        self._group_id: str | None = None
        self._lock: asyncio.Lock = asyncio.Lock()

    @staticmethod
    async def _block_static_resources(route: Route) -> None:
        """Playwright route interceptor to speed up page loading."""
        if route.request.resource_type in {"image", "stylesheet", "font", "media"}:
            await route.abort()
        else:
            await route.continue_()

    def _update_session_cookies(self, browser_cookies: list[Cookie]) -> None:
        """
        Syncs cookies from the headless browser to the HTTP session.

        Args:
            browser_cookies: A list of cookie dictionaries from browser.

        Raises:
            RuntimeError: If the internal HTTP session has not been initialized.
        """
        if not self.session:
            raise RuntimeError("HTTP session is not initialized.")

        cookies = {
            cookie["name"]: cookie["value"]  # pyright: ignore
            for cookie in browser_cookies
            if cookie["name"].lower() not in self.IGNORED_COOKIE_ATTRIBUTES  # pyright: ignore
        }

        self.session.cookie_jar.update_cookies(cookies)

    def _extract_regex(self, html: str, pattern: str) -> str | None:
        """
        Safely extracts the first capturing group of a regex pattern from an HTML string.

        Args:
            html: The raw HTML string to search through.
            pattern: The regular expression pattern containing at least one capture group.

        Returns:
            The matched string if found, otherwise `None`.
        """
        match = re.search(pattern, html, re.I | re.S)
        return match.group(1) if match else None

    async def _fetch_group_ajax(self, csrf_token: str) -> None:
        """
        Queries the DTEK AJAX endpoint to determine the group ID for the address.

        Args:
            csrf_token: The CSRF token.
        """
        logger.info("Retrieving group number for the address...")

        payload = {"method": "getHomeNum"}
        if self.region == "kem":
            payload.update({"data[0][name]": "street", "data[0][value]": self.street})
        else:
            payload.update(
                {
                    "data[0][name]": "city",
                    "data[0][value]": self.city,
                    "data[1][name]": "street",
                    "data[1][value]": self.street,
                }
            )

        ajax_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrf_token,
        }

        data = await self._request(
            HTTPMethod.POST, "/ua/ajax", data=payload, headers=ajax_headers
        )

        if not data or "result" not in data:
            logger.error("Failed to retrieve a group number for your address.")
            return

        self._group_id = data["data"][self.house]["sub_type_reason"][0]
        logger.info(f"Group number found: '{self._group_id}'.")

    async def _refresh_data(self) -> None:
        """Orchestrates the headless browser scraping flow."""
        logger.info("Scraping fresh data using Camoufox...")

        async with AsyncCamoufox(headless=True) as browser:
            page = await browser.new_page()
            url = f"{self.base_url}/ua/shutdowns"

            logger.info(f"Loading the page: '{url}'...")
            await page.route("**/*", self._block_static_resources)
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_selector("#discon_form", timeout=600)

            html = await page.content()

            # Retrieves outage schedules
            logger.info("Extracting raw schedules JSON...")
            schedules_json = self._extract_regex(
                html, r"DisconSchedule\.fact =\s*(\{.*?\})\s*(?=</script>)"
            )

            if not schedules_json:
                logger.error("Failed to retrieve outage schedules.")
                return

            self.cache.set("dtek_schedules_data", json.loads(schedules_json), ttl=900)

            # Retrieves and saves CSRF token
            if not self._group_id:
                logger.info("Retrieving a CSRF token for AJAX request...")
                csrf_token = self._extract_regex(
                    html, r'<meta\s+name="csrf-token"\s+content="([^"]+)"'
                )

                if not csrf_token:
                    logger.error("Failed to retrieve CSRF token.")
                    return

                self._update_session_cookies(await page.context.cookies())
                await self._fetch_group_ajax(csrf_token)

    def _parse_schedule(
        self, schedules_data: dict[str, Any], group_id: str
    ) -> OutageScheduleResponse:
        """
        Calculates upcoming power events by analyzing the raw schedule against the current time.

        Args:
            schedules_data: The deserialized JSON schedule object.
            group_id: The group ID.

        Returns:
            An `OutageScheduleResponse` object mapping the power states.
        """
        now = datetime.now(self.timezone)

        today_timestamp_key = next(
            (
                timestamp
                for timestamp in schedules_data.get("data", {})
                if datetime.fromtimestamp(int(timestamp), tz=self.timezone).date()
                == now.date()
            ),
            None,
        )

        if not today_timestamp_key:
            return OutageScheduleResponse()

        today_schedule = schedules_data["data"][today_timestamp_key].get(group_id, {})

        daily_slots = []
        for hour in range(1, 25):
            raw_status = today_schedule.get(str(hour), "yes")
            first_half_status, second_half_status = self.RAW_STATUS_MAPPING.get(
                raw_status, (PowerStatus.YES, PowerStatus.YES)
            )

            daily_slots.append(
                {"time": f"{hour - 1:02d}:00", "status": first_half_status}
            )
            daily_slots.append(
                {"time": f"{hour - 1:02d}:30", "status": second_half_status}
            )

        current_index = now.hour * 2 + (1 if now.minute >= 30 else 0)
        current_status = daily_slots[current_index]["status"]

        next_outage = None
        next_power_on = None

        for i in range(current_index + 1, len(daily_slots)):
            future_status = daily_slots[i]["status"]
            future_time = daily_slots[i]["time"]

            if current_status == PowerStatus.YES:
                if not next_outage and future_status in {
                    PowerStatus.NO,
                    PowerStatus.MAYBE,
                }:
                    next_outage = future_time
                elif (
                    next_outage
                    and not next_power_on
                    and future_status == PowerStatus.YES
                ):
                    next_power_on = future_time
                    break
            else:
                if future_status == PowerStatus.YES:
                    next_power_on = future_time
                    break

        return OutageScheduleResponse(
            current_status=current_status,
            next_outage_time=next_outage,
            next_power_on_time=next_power_on,
        )

    async def get_schedule(self) -> OutageScheduleResponse:
        """
        Fetches the current and upcoming power statuses.

        Returns:
            An `OutageScheduleResponse` object mapping the power states.
        """
        async with self._lock:
            schedules_data = self.cache.get("dtek_schedules_data")
            if not schedules_data:
                await self._refresh_data()
                schedules_data = self.cache.get("dtek_schedules_data")

        if not schedules_data or not self._group_id:
            return OutageScheduleResponse()

        return self._parse_schedule(schedules_data, self._group_id)
