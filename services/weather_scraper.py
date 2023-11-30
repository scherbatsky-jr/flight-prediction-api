import openmeteo_requests

import requests_cache
import pandas as pd
from retry_requests import retry
from datetime import date, timedelta

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

airports = [
    {"code": "DFW", "lat": 32.8972331, "long": -97.0376947},
    {"code": "CLT", "lat": 35.21375, "long": -80.9490556},
    {"code": "ORD", "lat": 41.9769403, "long": -87.9081497},
    {"code": "DEN", "lat": 39.8616667, "long": -104.6731667},
    {"code": "ATL", "lat": 33.6366996, "long": -84.427864},
    {"code": "SEA", "lat": 47.4498889, "long": -122.3117778},
    {"code": "PHX", "lat": 33.4342778, "long": -112.0115833},
    {"code": "LAX", "lat": 33.9424964, "long": -118.4080486},
    {"code": "DTW", "lat": 42.2124311, "long": -83.3533933},
    {"code": "IAH", "lat": 29.9844353, "long": -95.3414425},
    {"code": "SLC", "lat": 40.7883933, "long": -111.9777733},
    {"code": "PHL", "lat": 39.8720839, "long": -75.2406631},
    {"code": "MDW", "lat": 41.7859722, "long": -87.7524167},
    {"code": "SFO", "lat": 37.6188056, "long": -122.3754167},
    {"code": "BWI", "lat": 39.1757283, "long": -76.6689911}
]

url = "https://archive-api.open-meteo.com/v1/archive"

# Function to fetch hourly temperature data for an airport
def fetch_hourly_temperature(api, airport, start_date, end_date):
    params = {
        "latitude": airport['lat'],
        "longitude": airport['long'],
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "rain", "snowfall", "weather_code", "surface_pressure", "cloud_cover", "wind_speed_10m", "wind_direction_10m", "wind_direction_100m","weather_code"]
    }
    responses = api.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
    hourly_dew_point_2m = hourly.Variables(2).ValuesAsNumpy()
    hourly_precipitation = hourly.Variables(3).ValuesAsNumpy()
    hourly_rain = hourly.Variables(4).ValuesAsNumpy()
    hourly_snowfall = hourly.Variables(5).ValuesAsNumpy()
    hourly_weather_code = hourly.Variables(6).ValuesAsNumpy()
    hourly_surface_pressure = hourly.Variables(7).ValuesAsNumpy()
    hourly_cloud_cover = hourly.Variables(8).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(9).ValuesAsNumpy()
    hourly_wind_direction_10m = hourly.Variables(10).ValuesAsNumpy()
    hourly_wind_direction_100m = hourly.Variables(11).ValuesAsNumpy()
    hourly_weather_code = hourly.Variables(12).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s"),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s"),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )}
    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
    hourly_data["dew_point_2m"] = hourly_dew_point_2m
    hourly_data["precipitation"] = hourly_precipitation
    hourly_data["rain"] = hourly_rain
    hourly_data["snowfall"] = hourly_snowfall
    hourly_data["weather_code"] = hourly_weather_code
    hourly_data["surface_pressure"] = hourly_surface_pressure
    hourly_data["cloud_cover"] = hourly_cloud_cover
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
    hourly_data["wind_direction_10m"] = hourly_wind_direction_10m
    hourly_data["wind_direction_100m"] = hourly_wind_direction_100m
    hourly_data["weather_code"] = hourly_weather_code
    hourly_dataframe = pd.DataFrame(data=hourly_data)
    return hourly_dataframe


csv_filename = 'weather_data.csv'

# Fetch and export data for each airport for the year 2021
start_date = date(2021, 1, 1)
end_date = date(2021, 12, 31)

for airport in airports:
    current_date = start_date
    airport_data = pd.DataFrame()

    daily_data = fetch_hourly_temperature(openmeteo, airport, start_date, end_date)

    daily_data.to_csv(f"../datasets/weather_data/{airport['code']}_2021.csv", index=False)

print(f"Weather data for the year 2021 exported to CSV files.")