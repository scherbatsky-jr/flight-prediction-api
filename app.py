from flask import Flask, request
from flask_cors import CORS
import requests
import requests_cache
import openmeteo_requests
from openmeteo_requests import retry
from datetime import date, timedelta, datetime
import pickle
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.environ.get('APP_URL')}})

def getFlightSchedules(origin, destination, departure_date):
    url = os.environ.get('X_RAPIDAPI_URL', '')

    querystring = {
        "CodeType":"IATA",
        "ArrivalAirport": origin,
        "DepartureAirport": destination,
        "DepartureDateTime": f"{departure_date}T00:00"
        ,"version":"v2"
    }

    headers = {
        "X-RapidAPI-Key": os.environ.get('X_RAPIDAPI_KEY', ''),
        "X-RapidAPI-Host": os.environ.get('X_RAPIDAPI_HOST', '')
    }

    response = requests.get(url, headers=headers, params=querystring)

    return parseFlightResponse(response.json())

def parseFlightResponse(schedules):
    print(schedules)
    data = schedules['data']

    if (len(data) > 10):
        data = data[:10]

    formattedFlights = []

    for flight in data:
        formattedFlight = {}
        formattedFlight['flight_number'] = flight['flightNumber']
        formattedFlight['originCode'] = flight['departure']['airport']['iata']
        formattedFlight['destinationCode'] = flight['arrival']['airport']['iata']
        formattedFlight['departure_time'] = f"{flight['departure']['date']['utc']}T{flight['departure']['time']['utc']}"
        formattedFlight['arrival_time'] = f"{flight['arrival']['date']['utc']}T{flight['arrival']['time']['utc']}"
        formattedFlight['carrier'] = flight['carrier']

        formattedFlights.append(formattedFlight)

    return formattedFlights

def fillWeatherInfoForFlight(flight):
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    url = "https://api.open-meteo.com/v1/forecast"

    datetime_obj = datetime.strptime(flight['departure_time'], "%Y-%m-%dT%H:%M")
    formatted_date = datetime_obj.strftime("%Y-%m-%d")

    hour = datetime_obj.hour
    minute = datetime_obj.minute

    index = hour

    params = {
        "latitude": flight['lat'],
        "longitude": flight['long'],
        "start_date": formatted_date,
        "end_date": formatted_date,
        "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "rain", "snowfall", "weather_code", "surface_pressure", "cloud_cover", "wind_speed_10m", "wind_direction_10m"]
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

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

    flight['temperature_2m'] = float(hourly_temperature_2m[index])
    flight['relative_humidity_2m'] = float(hourly_relative_humidity_2m[index])
    flight['dew_point_2m'] = float(hourly_dew_point_2m[index])
    flight['precipitation'] = float(hourly_precipitation[index])
    flight['rain'] = float(hourly_rain[index])
    flight['snowfall'] = float(hourly_snowfall[index])
    flight['weather_code'] = float(hourly_weather_code[index])
    flight['surface_pressure'] = float(hourly_surface_pressure[index])
    flight['cloud_cover'] = float(hourly_cloud_cover[index])
    flight['wind_speed_10m'] = float(hourly_wind_speed_10m[index])
    flight['wind_direction_10m'] = float(hourly_wind_direction_10m[index])


    return flight


@app.route('/predictions', methods=['POST'])
def getPredictions():
    data = request.get_json()

    flights = getFlightSchedules(
        data.get('originCode'),
        data.get('destinationCode'),
        data.get('date')
    )

    for flight in flights:
        flight['lat'] = data.get('lat')
        flight['long'] = data.get('long')
        fillWeatherInfoForFlight(flight)

    return flights


@app.route('/')
def hello():
    return 'Flight Predictions API v1.0'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

