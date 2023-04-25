from datetime import datetime
from pydantic import BaseModel


class MinimalAgroTech(BaseModel):
    crop: str
    crop_variety: str
    lon: float
    lat: float
    sowing: datetime
    harvest: datetime
