"""
DSSAT model
"""
from DSSATTools import (
    Crop,
    SoilProfile,
    Weather,
    Management,
    available_cultivars,
)

from DSSATTools import DSSAT
import pandas as pd
from datetime import datetime
import numpy as np
import datetime as dt
import requests

import xarray as xr


class DSSATModel:
    def __init__(self, ds_weather: xr.Dataset, ds_solar: xr.Dataset) -> None:
        self.ds_weather = ds_weather
        self.ds_solar = ds_solar

        self.MJ_to_J = lambda x: x * 1e6
        self.mm_to_cm = lambda x: x / 10.0
        self.K_to_C = lambda x: x - 273.15
        # self.tdew_to_hpa = lambda x: ea_from_tdew(x) * 10.0
        self.to_date = lambda d: d.date()
        self.HTTP_OK = 200
        self.kg_m2_to_mm = lambda x: x * 86400
        self.ms_to_kmd = lambda x: x * 86.4
        self.watt_to_joules = lambda x: x * 86400
        # To-do: add ALLSKY_SFC_PAR_TOT to weather

    def _csvdate_to_date(self, x, dateformat):
        """Converts string x to a datetime.date using given format.

        :param x: the string representing a date
        :param dateformat: a strptime() accepted date format
        :return: a date
        """
        dt_f = dt.datetime.strptime(str(x), dateformat)
        return dt_f

    def get_elevation(self, longitude: float, latitude: float) -> float:
        """_get_elevation
        Get elevation from OpenTopoData API by lon and lat

        Args:
            longitude (float): longitude in WGS84
            latitude (float): latitude in WGS84

        Returns:
            float: elevation (m)
        """
        url = (
            f"https://api.opentopodata.org/v1/aster30m?locations={latitude},{longitude}"
        )
        resp = requests.get(url=url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            elevation = data["results"][0]["elevation"]
        else:
            elevation = 200
        return elevation

    def select_from_xarray(self, longitude: float, latitude: float) -> pd.DataFrame:
        """Select weather from Xarray dataset

        Args:
            longitude (float): point longitude
            latitude (float): point latitude

        Returns:
            pd.DataFrame: weather dataframe
        """
        point_weather = self.ds_weather.sel(
            lon=longitude, lat=latitude, method="nearest"
        )
        point_solar = self.ds_solar.sel(lon=longitude, lat=latitude, method="nearest")
        df_power = self.xr_dataset_to_pandas(ds=point_weather)

        df_solar = self.xr_dataset_to_pandas(ds=point_solar)

        df_power["DAY"] = pd.to_datetime(point_weather.time.values, format="%Y%m%d")

        df_solar = (
            df_solar.apply(self.watt_to_joules) / 1e6
        )  # Convert to MJ for A,B computing

        df_power = pd.concat([df_power, df_solar], axis=1)
        return df_power

    def xr_dataset_to_pandas(self, ds: xr.Dataset) -> pd.DataFrame:
        """Convert xarray point to pandas -> faster than implimented"""
        dict_to_pandas = {}
        for key in list(ds.keys()):
            dict_to_pandas[key] = ds[key].values
        return pd.DataFrame(dict_to_pandas)

    def get_dssat_weather(self, longitude: float, latitude: float):

        df_power = self.select_from_xarray(longitude=longitude, latitude=latitude)

        # Convert POWER data to a dataframe with PCSE compatible inputs
        df_dssat = pd.DataFrame(
            {
                "DATE": df_power.DAY.apply(self.to_date),
                "TMEAN": df_power.T2M.apply(self.K_to_C),
                "TMIN": df_power.T2M_MIN.apply(self.K_to_C),
                "TMAX": df_power.T2M_MAX.apply(self.K_to_C),
                "WIND": df_power.WS2M.apply(self.ms_to_kmd),
                "RAD": df_power.ALLSKY_SFC_SW_DWN,
                "RAIN": df_power.PRECTOTCORR.apply(self.kg_m2_to_mm),
                "DEWP": df_power.T2MDEW.apply(self.K_to_C),
                "RHUM": df_power.RH2M,
            }
        )
        df_dssat.loc[:, "DATE"] = df_dssat.loc[:, "DATE"].apply(
            lambda x: self._csvdate_to_date(x, "%Y-%m-%d")
        )
        self.df_dssat = df_dssat.reset_index(drop=True)
        return df_dssat

    def compute(
        self,
        crop_name: str,
        cultivar: str,
        lat: float,
        lon: float,
        harvest: datetime,
        sowing: datetime,
    ):

        df_weather = self.get_dssat_weather(latitude=lat, longitude=lon)
        df_weather["DATE"] = pd.to_datetime(df_weather["DATE"])
        weather_cols = ["DATE", "TMIN", "TMAX", "RAD", "RAIN", "RHUM"]
        wth = Weather(
            df_weather[weather_cols].copy(),
            pars={
                "DATE": "DATE",
                "TMIN": "TMIN",
                "TMAX": "TMAX",
                "RAIN": "RAIN",
                "RAD": "SRAD",
                "RHUM": "RHUM",
            },
            lat=lat,
            lon=lon,
            elev=self.get_elevation(latitude=lat, longitude=lon),
        )
        soil = SoilProfile(default_class="SCL")

        crop = Crop(crop_name, cultivar)
        man = Management(planting_date=sowing, irrigation="A")

        man.harvest_details["HDATE"] = harvest.strftime("%y%j")
        man.harvest_details["HPC"] = 100

        #
        dssat = DSSAT()
        dssat.setup()

        dssat.run(
            soil=soil,
            weather=wth,
            crop=crop,
            management=man,
        )
        if dssat.output["PlantGro"]:  # type: ignore
            output_1 = dssat.output["PlantGro"]  # type: ignore
            dssat.close()
            return float(output_1["CWAD"].max())
        else:
            raise ValueError("DSSAT no output")
