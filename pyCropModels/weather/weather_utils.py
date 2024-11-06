import os
from pcse.db import NASAPowerWeatherDataProvider
import pandas as pd
from scipy import spatial
import time
import traceback
import pcse

def weather_loader(path_CSV_dir:str, 
                   latitude:float, 
                   longitude: float,
                   path_to_pattern: str = './weather/pattern.csv'):
        """
        Main fun to load weather 
        If we have CSV file - load CSV,         
        else: Load from NASA
        """
        path_to_CSV_database = path_CSV_dir
        # Path to csv file with weather history
        path_weather_file = os.path.join(path_to_CSV_database ,f'NASA_weather_latitude_{latitude}_longitude_{longitude}.csv')
        # Check path
        if os.path.exists(path_weather_file):
            # print('LOAD FROM LOCAL CSV WEATHER DATABASE')
            # Load weather from CSV file
            weather = pcse.fileinput.CSVWeatherDataProvider(path_weather_file)
            return weather, 'Use weather from DataBase'
    
        else:
            print('No such directory or CSV file')
            # Test load from NASA POWER and save as csv and after load to crop model
            path = path_to_CSV_database
            try: 
                start_time = time.time()
                #API request to NASA database
                weather = NASAPowerWeatherDataProvider(latitude, longitude, force_update=True)

                # Print done if downloaded
                print(f'Downloaded weather from NASA POWER system, latitude: {latitude}, longitude: {longitude}')

                # export pcse.weather format to pandas df
                df_weather = pd.DataFrame(weather.export())

                #create full range of dates
                r = pd.date_range(start=df_weather.DAY.min(), end=df_weather.DAY.max())

                #extend range of dates
                full_range_weather = df_weather.set_index('DAY').reindex(r).rename_axis('DAY').reset_index()
                missing_days = (full_range_weather.isna()).sum().sum()
                filled_weather = full_range_weather.fillna(method='ffill', axis=0)
            

                filled_weather=filled_weather[['DAY', 'IRRAD', 'TMIN', 'TMAX', 'VAP', 'WIND', 'RAIN']]
                filled_weather['SNOWDEPTH'] = 'NaN'
                filled_weather[['IRRAD']] = filled_weather[['IRRAD']]/1000.
                filled_weather[['VAP']] = filled_weather[['VAP']]/10.
                filled_weather.DAY=filled_weather.DAY.dt.strftime('%Y%m%d')


                text = open(path_to_pattern, "r")
                text = ''.join([i for i in text]).replace("1111", str(weather.longitude))
                text = ''.join([i for i in text]).replace("2222", str(weather.latitude))
                text = ''.join([i for i in text]).replace("3333", str(weather.elevation))
                text = ''.join([i for i in text]).replace("4444", str(weather.angstA))
                text = ''.join([i for i in text]).replace("5555", str(weather.angstB))
                x = open(os.path.join(path,f'NASA_weather_latitude_{latitude}_longitude_{longitude}.csv'),"w")
                x.writelines(text)
                x.close()

                path_to_save_csv_file = os.path.join(path,f'NASA_weather_latitude_{latitude}_longitude_{longitude}.csv')
                filled_weather.to_csv(path_to_save_csv_file, mode='a', header=False, index=False)

                #add info to weather database and save it to csv
                print('path_to_save_csv_file', path_to_save_csv_file)
                print('time in sec', time.time() - start_time)

                #LOAD WEATHER as csv file
                weather = pcse.fileinput.CSVWeatherDataProvider(path_to_save_csv_file)
                return weather, 'Downloaded weather from NASA system'
            except Exception:
                info = traceback.format_exc()
                all_weather = [file for file in os.listdir(path_to_CSV_database) if 'latitude' in file]
                user_coords = [(longitude, latitude)]
                coords = []
                for weather in all_weather:
                    latitude = weather.split('_')[3]
                    longitude = os.path.splitext(weather.split('_')[5])[0]
                    coords.append((float(latitude), float(longitude)))

                tree = spatial.KDTree(coords)
                dist, position = tree.query(user_coords)
                closest_weather_coords = coords[position[0]]
                weather_file = all_weather[position[0]]
                closest_weather = os.path.join(path_to_CSV_database,weather_file)
                weather = pcse.fileinput.CSVWeatherDataProvider(closest_weather)
                

                return weather, 'Use closest weather data'

