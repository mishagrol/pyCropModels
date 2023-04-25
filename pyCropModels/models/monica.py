import json
import pandas as pd
import subprocess
import os
import datetime as dt
import xarray as xr
from ..agrotechnology.calendar import Agrotechnology

## Example -> Реализация запуска бинарника


import platform

OS = platform.system().lower()
# from DSSATTools import __file__ as DSSATModulePath

# Пример реализация запуска exe или бинарника для DSSAT, я так понимаю
# автор определяет тип OS и в зависимости уже идет запуск через subprocess exe или bin
# в setup.py правила распространения пакета
# Исходники: https://github.com/daquinterop/Py_DSSATTools


# class DSSAT:
#     """
#     Class that represents the simulation environment. When initializing and seting up the environment, a new folder is created (usually in the tmp folder), and all of the necesary files to run the model are copied into it.
#     """

#     def __init__(self):
#         BASE_PATH = os.path.dirname(DSSATModulePath)
#         self._STATIC_PATH = os.path.join(BASE_PATH, "static")
#         if "windows" in OS:
#             self._BIN_PATH = os.path.join(self._STATIC_PATH, "bin", "dscsm048.exe")
#             self._CONFILE = "DSSATPRO.V48"
#         else:
#             self._BIN_PATH = os.path.join(self._STATIC_PATH, "bin", "dscsm048")
#             self._CONFILE = "DSSATPRO.L48"


#
# excinfo = subprocess.run(exc_args,
#         cwd=self._RUN_PATH, capture_output=True, text=True
#     )


def csvdate_to_date(x, dateformat):
    """Converts string x to a datetime.date using given format.

    :param x: the string representing a date
    :param dateformat: a strptime() accepted date format
    :return: a date
    """
    dt_f = dt.datetime.strptime(str(x), dateformat)
    dt_p = dt.datetime.strftime(dt_f, "%d.%m.%Y")
    return dt_p


def weather_to_monica(weather: pd.DataFrame, dst: str):
    weather.loc[:, "de-date"] = pd.to_datetime(weather["de-date"], format="%d.%m.%Y")
    weather.round(2).to_csv(dst, sep=";", index=False)
    return weather


calendar = Agrotechnology()


class MONICA:
    def __init__(self) -> None:
        pass

    def compute(
        self,
        crop: str,
        crop_variety: str,
        lat: float,
        lon: float,
        harvest: dt.datetime,
        sowing: dt.datetime,
    ):
        calendar_dataset = xr.Dataset()
        cropCalendar = calendar.getCropCalendar(
            dataset=calendar_dataset, lon=lon, lat=lat, year=year
        )
        if (cropCalendar["plant_day"] == "NaN") or (
            cropCalendar["harvest_day"] == "NaN"
        ):
            return "NaN"
        path_monica = "../monica/monica_input/"
        dst = os.path.join(path_monica, "climate-monica.csv")
        crop_res = prepareCrop(
            path=path_monica,
            crop_name=crop,
            planting=cropCalendar["plant_day"],
            harvest=cropCalendar["harvest_day"],
        )

        site_res = prepareSite(path=path_monica, latitude=lat)
        # Run monica
        path_sim_file = "monica_run.sh"
        cmd_monica = "bash"

        cmd = "monica-run"
        res_monica_run = subprocess.run([cmd, path_sim_file], universal_newlines=True)
        print(res_monica_run)
        daily_monica = pd.read_csv(
            "./out.csv", skiprows=[0, 2], skipfooter=30, engine="python"
        )
        out_monica = pd.read_csv("./out.csv", skiprows=1, nrows=2)
        monica_yield = out_monica.loc[1, "Yield"]
        return monica_yield


def prepareCrop(path: str, crop_name: str, planting: str, harvest: str) -> dict:

    """
    Prepare crop dict for MONICA JSON file

    """

    crop_file = os.path.join(path, "crop.json")

    with open(crop_file, "r") as j:
        cropJson = json.loads(j.read())

    # planting date
    cropJson["cropRotation"][0]["worksteps"][0]["date"] = planting
    # harvest date
    cropJson["cropRotation"][0]["worksteps"][1]["date"] = harvest
    for target in ["species", "cultivar"]:
        cropJson["cropRotation"][0]["worksteps"][0]["crop"]["cropParams"][target][
            1
        ] = cropsDict[crop_name][target]
    cropJson["cropRotation"][0]["worksteps"][0]["crop"]["residueParams"][1] = cropsDict[
        crop_name
    ]["crop-residues"]

    cropfName = os.path.join(path, "crop-monica.json")
    with open(cropfName, "w") as file:
        json.dump(cropJson, file, ensure_ascii=False, indent=4)

    return cropJson


def prepareSite(path: str, latitude: float) -> dict:
    """
    Prepare site dict for MONICA JSON file

    TO-DO: add soil data from soilgrids

    """

    site_file = os.path.join(path, "site.json")

    with open(site_file, "r") as j:
        siteJson = json.loads(j.read())
    siteJson["SiteParameters"]["Latitude"] = latitude
    sitefName = os.path.join(path, "site-monica.json")
    with open(sitefName, "w") as file:
        json.dump(siteJson, file, ensure_ascii=False, indent=4)

    return siteJson
