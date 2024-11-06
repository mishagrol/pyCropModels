from DSSATTools import Crop, SoilProfile, Weather, Management, DSSAT, available_cultivars
import DSSATTools
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

from tqdm import notebook

import datetime as dt
import numpy as np 
import os

import os, sys
import json
import pandas as pd
import datetime as dt
import subprocess
import csv
import math
import shutil

import sys

# sys.path.append("../src/")
import gc

import subprocess
from itertools import chain, product
import time


import numpy as np
import pandas as pd
from functools import lru_cache


import datetime as dt 
import os
import requests

from math import log10, cos, sin, asin, sqrt, exp, pi, radians


pd.options.mode.chained_assignment = None  # default='warn'



import time


import requests


from math import log10, cos, sin, asin, sqrt, exp, pi, radians

power_variables = ["TOA_SW_DWN", "ALLSKY_SFC_SW_DWN", "T2M", "T2M_MIN",
                            "T2M_MAX", "T2MDEW", "WS2M", "PRECTOTCORR", 'RH2M']




def csvdate_to_date(x, dateformat):
    """Converts string x to a datetime.date using given format.

    :param x: the string representing a date
    :param dateformat: a strptime() accepted date format
    :return: a date
    """
    dt_f = dt.datetime.strptime(str(x), dateformat)
    dt_p = dt.datetime.strftime(dt_f, '%d.%m.%Y')
    return dt_p


# Conversion functions
def NoConversion(x, d):
    return float(x)


def kJ_to_MJ(x, d):
    return float(x)/1000.


def mm_to_cm(x, d):
    return float(x)/10.


def kPa_to_hPa(x, d):
    return float(x)*10.




@lru_cache(maxsize=128)
def query_NASAPower_server(latitude, longitude):
    start_date = dt.date(2019,1,1)
    end_date = dt.date(2021,1,1)

    server = "https://power.larc.nasa.gov/api/temporal/daily/point"
    payload = {"request": "execute",
                "parameters": ",".join(power_variables),
                "latitude": latitude,
                "longitude": longitude,
                "start": start_date.strftime("%Y%m%d"),
                "end": end_date.strftime("%Y%m%d"),
                "community": "AG",
                "format": "JSON",
                "user": "anonymous"
                }
    req = requests.get(server, params=payload)

    if req.status_code != 200:
        msg = ("Failed retrieving POWER data, server returned HTTP " +
                "code: %i on following URL %s") % (req.status_code, req.url)
        raise ValueError(msg)

    return req.json()



class NASA_MONICA:
    ranges = {"LAT": (-90., 90.),
          "LON": (-180., 180.),
          "ELEV": (-300, 6000),
          "IRRAD": (0., 40e6),
          "TMIN": (-50., 60.),
          "TMAX": (-50., 60.),
          "VAP": (0.06, 199.3),  # hPa, computed as sat. vapour pressure at -50, 60 Celsius
          "RAIN": (0, 25),
          "E0": (0., 2.5),
          "ES0": (0., 2.5),
          "ET0": (0., 2.5),
          "WIND": (0., 100.),
          "SNOWDEPTH": (0., 250.),
          "TEMP": (-50., 60.),
          "TMINRA": (-50., 60.)}

    def __init__(self, latitude, longitude):
        if latitude < -90 or latitude > 90:
            msg = "Latitude should be between -90 and 90 degrees."
            raise ValueError(msg)
        if longitude < -180 or longitude > 180:
            msg = "Longitude should be between -180 and 180 degrees."
            raise ValueError(msg)

        self.MJ_to_J = lambda x: x * 1e6
        self.mm_to_cm = lambda x: x / 10.
        self.tdew_to_hpa = lambda x: ea_from_tdew(x) * 10.
        self.to_date = lambda d: d.date()
        self.HTTP_OK = 200
        self.angstA = 0.29
        self.angstB = 0.49

        self.latitude = latitude
        self.longitude = longitude

        self.power_variables = ["TOA_SW_DWN", "ALLSKY_SFC_SW_DWN", "T2M", "T2M_MIN",
                            "T2M_MAX", "T2MDEW", "WS2M", "PRECTOTCORR", 'RH2M']
        self._get_and_process_NASAPower(latitude, longitude)

    def _get_and_process_NASAPower(self, latitude, longitude):
            """Handles the retrieval and processing of the NASA Power data
            """
            powerdata = query_NASAPower_server(latitude, longitude)
            if not powerdata:
                msg = "Failure retrieving POWER data from server. This can be a connection problem with " \
                    "the NASA POWER server, retry again later."
                raise RuntimeError(msg)

            # Store the informational header then parse variables
            self.description = [powerdata["header"]["title"]]
            self.elevation = float(powerdata["geometry"]["coordinates"][2])
            
            
            df_power = self._process_POWER_records(powerdata)
#             self.angstA, self.angstB = self._estimate_AngstAB(df_power)
            df_monica = self._POWER_to_PCSE(df_power)
            self.df_monica = df_monica
            return df_monica
        
    @lru_cache(maxsize=128)
    def _query_NASAPower_server(self, latitude, longitude):
        start_date = dt.date(2019,1,1)
        end_date = dt.date(2021,1,1)
        # build URL for retrieving data, using new NASA POWER api
        server = "https://power.larc.nasa.gov/api/temporal/daily/point"
        payload = {"request": "execute",
                    "parameters": ",".join(self.power_variables),
                    "latitude": latitude,
                    "longitude": longitude,
                    "start": start_date.strftime("%Y%m%d"),
                    "end": end_date.strftime("%Y%m%d"),
                    "community": "AG",
                    "format": "JSON",
                    "user": "anonymous"
                    }
        req = requests.get(server, params=payload)

        if req.status_code != self.HTTP_OK:
            msg = ("Failed retrieving POWER data, server returned HTTP " +
                    "code: %i on following URL %s") % (req.status_code, req.url)
            raise ValueError(msg)

        return req.json()

    def _process_POWER_records(self, powerdata):
        """Process the meteorological records returned by NASA POWER
        """


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
    
    def _POWER_to_PCSE(self, df_power):

            # Convert POWER data to a dataframe with PCSE compatible inputs
            df_pcse = pd.DataFrame({"de-date": df_power.DAY.apply(self.to_date),
                                    "tavg": df_power.T2M,
                                    "tmin": df_power.T2M_MIN,
                                    "tmax": df_power.T2M_MAX,
                                    "wind": df_power.WS2M,
                                    "globrad": df_power.ALLSKY_SFC_SW_DWN,
                                    "precip": df_power.PRECTOTCORR,
                                    "relhumid": df_power.RH2M})
            df_pcse.loc[:, 'de-date'] = df_pcse.loc[:, 'de-date'].apply(lambda x: csvdate_to_date(x, '%Y-%m-%d'))
            self.df_pcse = df_pcse.reset_index(drop=True)
            return df_pcse
        

class NASA_DSSAT(NASA_MONICA):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.MJ_to_J = lambda x: x * 1e6
        self.mm_to_cm = lambda x: x / 10.0
        self.K_to_C = lambda x: x - 273.15
        self.tdew_to_hpa = lambda x: ea_from_tdew(x) * 10.0
        self.to_date = lambda d: d.date()
        self.HTTP_OK = 200
        self.kg_m2_to_mm = lambda x: x * 86400
        self.ms_to_kmd = lambda x: x*86.4
        self.watt_to_joules = lambda x: x * 86400
    
    def csvdate_to_date(self, x, dateformat):
        """Converts string x to a datetime.date using given format.

        :param x: the string representing a date
        :param dateformat: a strptime() accepted date format
        :return: a date
        """
        dt_f = dt.datetime.strptime(str(x), dateformat)
        return dt_f
    
    def get_dssat_weather(self, longitude:float, latitude:float):
        
        powerdata = query_NASAPower_server(latitude, longitude)
        if not powerdata:
            msg = "Failure retrieving POWER data from server. This can be a connection problem with " \
                "the NASA POWER server, retry again later."
            raise RuntimeError(msg)

        # Store the informational header then parse variables
        self.description = [powerdata["header"]["title"]]
        self.elevation = float(powerdata["geometry"]["coordinates"][2])


        df_power = self._process_POWER_records(powerdata)

        df_dssat = pd.DataFrame(
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
        df_dssat.loc[:, "DATE"] = df_dssat.loc[:, "DATE"].apply(
            lambda x: self.csvdate_to_date(x, "%Y-%m-%d")
        )
        self.df_dssat = df_dssat.reset_index(drop=True)
        return df_dssat

    
    
def get_real_soil():
    soil_layer_a1 = {'Thickness': [0.37, 'm'],
      'SoilOrganicCarbon': [5.1, '%'],
      'KA5TextureClass': 'Lu',
      'Sand': [0.037, 'kg kg-1 (%[0-1])'],
      'Clay': [0.09, 'kg kg-1 (%[0-1])'],
      'Skeleton': [0.02, '%[0-1]'],
      'PoreVolume': [0.566, 'm3 m-3'],
      'FieldCapacity': [0.3, 'm3 m-3'],
      'PermanentWiltingPoint': [0.15, 'm3 m-3'],
      'pH': [6.213],
      'CN': [12.481],
      'SoilBulkDensity': [1126.625, 'kg m-3']}
    
    
    soil_layer_b1 =  {'Thickness': [0.23, 'm'],
      'SoilOrganicCarbon': [2.38, '%'],
      'KA5TextureClass': 'Lu',
      'Sand': [0.066, 'kg kg-1 (%[0-1])'],
      'Clay': [0.13, 'kg kg-1 (%[0-1])'],
      'Skeleton': [0.02, '%[0-1]'],
      'PoreVolume': [0.401, 'm3 m-3'],
      'FieldCapacity': [0.3, 'm3 m-3'],
      'PermanentWiltingPoint': [0.15, 'm3 m-3'],
      'pH': [6.787],
      'CN': [10.139],
      'SoilBulkDensity': [1544.678, 'kg m-3']}
    
    
    soil_layer_b2 = {'Thickness': [1.30, 'm'],
      'SoilOrganicCarbon': [0.6, '%'],
      'KA5TextureClass': 'Lu',
      'Sand': [0.069, 'kg kg-1 (%[0-1])'],
      'Clay': [0.136, 'kg kg-1 (%[0-1])'],
      'Skeleton': [0.02, '%[0-1]'],
      'PoreVolume': [0.37, 'm3 m-3'],
      'FieldCapacity': [0.3, 'm3 m-3'],
      'PermanentWiltingPoint': [0.15, 'm3 m-3'],
      'pH': [8.013],
      'CN': [7.705],
      'SoilBulkDensity': [1599.873, 'kg m-3']}

    return [soil_layer_a1, soil_layer_b1, soil_layer_b2]
