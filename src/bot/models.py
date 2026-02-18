from pydantic import BaseModel


class RegionData(BaseModel):
    cpu: str
    name_ua: str
    schedule: dict[str, dict[str, dict[str, int]]] | None = None


class OutageResponse(BaseModel):
    date_today: str
    date_tomorrow: str
    regions: list[RegionData]
