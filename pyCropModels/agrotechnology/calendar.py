"""
Global crop calendar
"""
import datetime as dt
import xarray as xr
import math


class Agrotechnology:
    """
    TO-DO:
    1. Add: major agrotech info for DSSAT, MONICA and WOFOST
    2. AWS: add reading files from AWS S3 storage or from source Drive files (archive?)
    """

    def __init__(self) -> None:

        self.pathCalendar = "/home/mgasanov/agro/CropCalendar"
        self.dictCalendars = {
            "barley": "Barley.crop.calendar.fill.nc",
            "soybean": "Soybeans.crop.calendar.fill.nc",
            "sunflower": "Sunflower.crop.calendar.fill.nc",
            "maize": "Maize.crop.calendar.fill.nc",
            "wheat": "Wheat.crop.calendar.fill.nc",
        }

    def getCropCalendar(
        self, dataset: xr.Dataset, lon: float, lat: float, year: str = "2022"
    ) -> dict:

        harvest_flt = float(
            dataset.sel(latitude=lat, longitude=lon, method="nearest").harvest.values
        )
        plant_flt = float(
            dataset.sel(latitude=lat, longitude=lon, method="nearest").plant.values
        )
        if (math.isnan(harvest_flt)) or (math.isnan(plant_flt)):
            return {"plant_day": "NaN", "harvest_day": "NaN"}
        harvest_day = str(
            dt.datetime.strptime(f"{year} {int(harvest_flt)}", "%Y %j").date()
        )
        plant_day = str(
            dt.datetime.strptime(f"{year} {int(plant_flt)}", "%Y %j").date()
        )
        if harvest_day > f"{year}-09-30":
            harvest_day = f"{year}-09-29"
        if plant_day < f"{year}-04-22":
            plant_day = f"{year}-04-22"
        return {"plant_day": plant_day, "harvest_day": harvest_day}
