import datetime as dt
import yaml
from ..weather.aws_weather import Aws_Wofost

import pcse
from pcse.models import Wofost71_WLP_FD, Wofost71_PP
from pcse.fileinput import CABOFileReader, YAMLCropDataProvider
from pcse.db import NASAPowerWeatherDataProvider
from pcse.util import WOFOST71SiteDataProvider, DummySoilDataProvider
from pcse.base import ParameterProvider
from pcse.engine import Engine
from pcse.fileinput import csvweatherdataprovider


class WOFOST:
    def __init__(self, dataset) -> None:
        self.dataset = dataset  # aws weather dataset
        self._cropd = YAMLCropDataProvider()
        self._sited = WOFOST71SiteDataProvider(WAV=50)
        self.cultivars = {"soybean": "Soybean_904", "maize": "Grain_maize_201"}

        self._soild = DummySoilDataProvider()

    def get_wdp(self, lon: float, lat: float, dataset: dict):
        wdp = Aws_Wofost(
            longitude=lon,
            latitude=lat,
            ds_solar=dataset["solar"],  # ???
            ds_weather=dataset["meteo"],
        )  # ???)
        return wdp

    def get_soil(self, lon: float, lat: float):
        pass

    def compute(
        self,
        crop: str,
        crop_variety: str,
        lat: float,
        lon: float,
        harvest: str,
        sowing: str,
    ):
        wdp = self.get_wdp(lon=lon, lat=lat, dataset=self.dataset)
        sowing_dt = dt.datetime.strptime(sowing, "%Y-%m-%d")
        campaign_start_date = dt.datetime.strftime(
            sowing_dt - dt.timedelta(20), "%Y-%m-%d"
        )
        emergence_date = sowing
        harvest_date = harvest
        max_duration = 300
        soilgrids = self.get_soil(lat=lat, lon=lon)
        soild = self._soild
        #     soild['SMW'] = df.iloc[i, :]['Wilting point']
        #     soild['SMFCF'] = df.iloc[i, :]['Field Capacity']
        #     soild['K0'] = df.iloc[i, :]['Ks (cm/h)']
        # Here we define the agromanagement for crop
        agro_yaml = f"""
        - {campaign_start_date}:
            CropCalendar:
                crop_name: {crop}
                variety_name: {crop_variety}
                crop_start_date: {sowing}
                crop_start_type: emergence
                crop_end_date: {harvest}
                crop_end_type: harvest
                max_duration: {max_duration}
            TimedEvents: null
            StateEvents: null
        """
        agro = yaml.safe_load(agro_yaml)

        firstkey = list(agro[0])[0]
        cropcalendar = agro[0][firstkey]["CropCalendar"]
        cropd = self._cropd
        sited = self._sited
        cropd.set_active_crop(cropcalendar["crop_name"], cropcalendar["variety_name"])
        params = ParameterProvider(cropdata=cropd, sitedata=sited, soildata=soild)

        wofost = Wofost71_WLP_FD(params, wdp, agro)
        wofost.run_till_terminate()
        r = wofost.get_summary_output()
        fld_yield = r[-1]["TWSO"]
        return fld_yield
