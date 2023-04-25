"""
DSSAT model
"""
from DSSATTools import Crop, SoilProfile, WeatherData, WeatherStation, Management

from DSSATTools import DSSAT as pyDSSAT
import pandas as pd
from datetime import datetime
import numpy as np
import datetime as dt
import requests


class DSSAT:
    def __init__(self) -> None:
        pass

    def get_weather(self, lon, lat) -> pd.DataFrame:
        # TO-DO Добавить загрузчик погоды из AWS
        df_weather["DATE"] = pd.to_datetime(df_weather["DATE"])
        weather_cols = ["DATE", "TMIN", "TMAX", "RAD", "RAIN", "RHUM"]
        WTH_DATA = WeatherData(
            df_weather[weather_cols].copy(),
            variables={
                "TMIN": "TMIN",
                "TMAX": "TMAX",
                "RAIN": "RAIN",
                "RAD": "SRAD",
                "RHUM": "RHUM",
            },
        )
        # TO-DO : add elevation from aws weather module
        wth = WeatherStation(
            WTH_DATA, {"ELEV": 400, "LAT": lat, "LON": lon, "INSI": "NeverLand"}
        )
        return wth

    def compute(
        self,
        crop: str,
        crop_variety: str,
        lat: float,
        lon: float,
        harvest: datetime,
        sowing: datetime,
    ):
        # lon, lat = round_geoposition(r['lon']), round_geoposition(r['lat'])
        # df_weather = weather_loader(path=weather_folder, longitude=lon, latitude=lat)

        wth = self.get_weather(lon=lon, lat=lat)
        soil = SoilProfile(default_class="SCL")

        crop = Crop(crop_name=crop)
        man = Management(cultivar=crop_variety, planting_date=sowing, irrigation="A")
        # Modify harvest to Automatic
        man.harvest_details["table"].loc[0, ["HDATE", "HPC"]] = [
            harvest.strftime("%y%j"),
            100,
        ]
        # man.simulation_controls['HARVS'] = 'A'
        dssat = pyDSSAT()
        dssat.setup()
        dssat.run(
            soil=soil,
            weather=wth,
            crop=crop,
            management=man,
        )
        output_1 = dssat.output["PlantGro"]
        dssat.close()
        return float(
            output_1["CWAD"].max()
        )  # TO-DO проверить что .max() это хорошая идея


class NASA_DSSAT:
    """
    Utils to download weather from NASA POWER and convert to DSSAT units
    """

    ranges = {
        "LAT": (-90.0, 90.0),
        "LON": (-180.0, 180.0),
        "ELEV": (-300, 6000),
        "IRRAD": (0.0, 40e6),
        "TMIN": (-50.0, 60.0),
        "TMAX": (-50.0, 60.0),
        "VAP": (
            0.06,
            199.3,
        ),  # hPa, computed as sat. vapour pressure at -50, 60 Celsius
        "RAIN": (0, 25),
        "E0": (0.0, 2.5),
        "ES0": (0.0, 2.5),
        "ET0": (0.0, 2.5),
        "WIND": (0.0, 100.0),
        "SNOWDEPTH": (0.0, 250.0),
        "TEMP": (-50.0, 60.0),
        "TMINRA": (-50.0, 60.0),
    }

    def __init__(self, latitude, longitude):
        if latitude < -90 or latitude > 90:
            msg = "Latitude should be between -90 and 90 degrees."
            raise ValueError(msg)
        if longitude < -180 or longitude > 180:
            msg = "Longitude should be between -180 and 180 degrees."
            raise ValueError(msg)

        self.MJ_to_J = lambda x: x * 1e6
        self.mm_to_cm = lambda x: x / 10.0
        self.tdew_to_hpa = lambda x: ea_from_tdew(x) * 10.0
        self.to_date = lambda d: d.date()
        self.HTTP_OK = 200
        self.angstA = 0.29
        self.angstB = 0.49

        self.latitude = latitude
        self.longitude = longitude
        # To-do: add ALLSKY_SFC_PAR_TOT to weather
        self.power_variables = [
            "TOA_SW_DWN",
            "ALLSKY_SFC_SW_DWN",
            "T2M",
            "T2M_MIN",
            "T2M_MAX",
            "T2MDEW",
            "WS2M",
            "PRECTOTCORR",
            "RH2M",
        ]
        self.df_weather = self._get_and_process_NASAPower(latitude, longitude)

    def csvdate_to_date(self, x, dateformat):
        """Converts string x to a datetime.date using given format.

        :param x: the string representing a date
        :param dateformat: a strptime() accepted date format
        :return: a date
        """
        dt_f = dt.datetime.strptime(str(x), dateformat)
        #         dt_p = dt.datetime.strftime(dt_f, '%Y-%m-%d')
        return dt_f

    def _get_and_process_NASAPower(self, latitude, longitude):
        """Handles the retrieval and processing of the NASA Power data"""
        powerdata = self._query_NASAPower_server(latitude, longitude)
        if not powerdata:
            msg = (
                "Failure retrieving POWER data from server. This can be a connection problem with "
                "the NASA POWER server, retry again later."
            )
            raise RuntimeError(msg)

        self.description = [powerdata["header"]["title"]]
        self.elevation = float(powerdata["geometry"]["coordinates"][2])

        df_power = self._process_POWER_records(powerdata)
        df_weather = self._POWER_to_DSSAT(df_power)
        return df_weather

    def _query_NASAPower_server(self, latitude, longitude):
        start_date = dt.date(2010, 1, 1)
        end_date = dt.date.today()
        # build URL for retrieving data, using new NASA POWER api
        server = "https://power.larc.nasa.gov/api/temporal/daily/point"
        payload = {
            "request": "execute",
            "parameters": ",".join(self.power_variables),
            "latitude": latitude,
            "longitude": longitude,
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "community": "AG",
            "format": "JSON",
            "user": "anonymous",
        }
        req = requests.get(server, params=payload)

        if req.status_code != self.HTTP_OK:
            msg = (
                "Failed retrieving POWER data, server returned HTTP "
                + "code: %i on following URL %s"
            ) % (req.status_code, req.url)
            raise ValueError(msg)

        return req.json()

    def _process_POWER_records(self, powerdata):
        """Process the meteorological records returned by NASA POWER"""

        fill_value = float(powerdata["header"]["fill_value"])

        df_power = {}
        for varname in self.power_variables:
            s = pd.Series(powerdata["properties"]["parameter"][varname])
            s[s == fill_value] = np.NaN
            df_power[varname] = s
        df_power = pd.DataFrame(df_power)
        df_power["DAY"] = pd.to_datetime(df_power.index, format="%Y%m%d")

        # find all rows with one or more missing values (NaN)
        ix = df_power.isnull().any(axis=1)
        # Get all rows without missing values
        df_power = df_power[~ix]

        return df_power

    def _POWER_to_DSSAT(self, df_power):

        # Convert POWER data to a dataframe with PCSE compatible inputs
        df_pcse = pd.DataFrame(
            {
                "DATE": df_power.DAY.apply(self.to_date),
                "TMEAN": df_power.T2M,
                "TMIN": df_power.T2M_MIN,
                "TMAX": df_power.T2M_MAX,
                "WIND": df_power.WS2M,
                "RAD": df_power.ALLSKY_SFC_SW_DWN,
                "RAIN": df_power.PRECTOTCORR,
                "DEWP": df_power.T2MDEW,
                "RHUM": df_power.RH2M,
            }
        )
        df_pcse.loc[:, "DATE"] = df_pcse.loc[:, "DATE"].apply(
            lambda x: self.csvdate_to_date(x, "%Y-%m-%d")
        )
        self.df_pcse = df_pcse.reset_index(drop=True)
        return df_pcse
