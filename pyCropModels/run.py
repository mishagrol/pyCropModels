from models.dssat import DSSAT


polygon = (1000, 1000)

# 100 на 100


weather = get_weather(region="EU")  # type weather: xarry

soil = get_soil(region="EU")  # type soil: xarry

for lon, lat in weather["lon", "lat"]:
    point_weather = get_weather(lon, lat)
    point_soil = get_soil_point()

    agro[lon, lat] = point_soil
    # DSSAT.compute(lon, lat, weather = weather)
    # WOFOST.compute(lon, lat, weather = weather)
agro.apply(DSSAT.compute())
