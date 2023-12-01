from flask import Flask, request
from flask_cors import CORS
import requests
import requests_cache
import openmeteo_requests
from retry_requests import retry
from datetime import date, timedelta, datetime
import pickle
from dotenv import load_dotenv
import os
import numpy as np
import xgboost as xgb
import json

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
    data = schedules['data']

    if (len(data) <= 0):
        return []
    
    if (len(data) > 10):
        data = data[:10]

    formattedFlights = []

    for flight in data:
        formattedFlight = {}
        formattedFlight['flight_number'] = flight['flightNumber']
        formattedFlight['originCode'] = flight['arrival']['airport']['iata']
        formattedFlight['destinationCode'] = flight['departure']['airport']['iata']
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
        "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "rain", "snowfall", "weather_code", "surface_pressure", "cloud_cover", "wind_speed_10m", "wind_direction_100m"]
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
    hourly_wind_direction_100m = hourly.Variables(10).ValuesAsNumpy()

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
    flight['wind_direction_100m'] = float(hourly_wind_direction_100m[index])

    return flight

def convert_to_json_serializable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.float32):
        return float(obj)
    else:
        return obj

def getDelayPredictions(flights):
    filename = './models/classification-logistic-c-imbalance.pkl'
    model = pickle.load(open(filename,'rb'))

    flights_data = []

    for flight in flights:
        flight_data = [
            flight["Origin"],
            flight["Dest"],
            flight["CRSDepTime"],
            flight["DepDel15"],
            flight['temperature_2m'],
            flight['dew_point_2m'],
            flight['precipitation'],
            flight['cloud_cover'],
            flight['wind_direction_100m']
        ]
        
        flights_data.append(flight_data)

    # Convert the list of lists to a NumPy array
    flights_array = np.array(flights_data)

    predictions = model.predict(flights_array)
    probability_scores = model.predict_proba(flights_array)

    confidence_scores = np.max(probability_scores, axis=1)

    regression_model = pickle.load(open('./models/regression-xg-boost-2.pkl','rb'))

    delay_predictions = regression_model.predict(flights_array)

    for index, flight in enumerate(flights):
        flight['delay_prediction'] = predictions[index]
        flight['probability'] = confidence_scores[index]
        flight['delay_minutes'] = delay_predictions[index]


@app.route('/predictions', methods=['POST'])
def getPredictions():
    data = request.get_json()

    flights = getFlightSchedules(
        data.get('originCode'),
        data.get('destinationCode'),
        data.get('date')
    )

    if (len(flights) <=0):
        return flights

    for flight in flights:
        flight['Origin'] = data.get('originID')
        flight['Dest'] = data.get('destinationID')
        flight['lat'] = data.get('lat')
        flight['long'] = data.get('long')
        flight['DepDel15'] = 1

        dt_object = datetime.strptime(flight['departure_time'], "%Y-%m-%dT%H:%M")
        flight['CRSDepTime'] = dt_object.hour * 100 + dt_object.minute
        fillWeatherInfoForFlight(flight)

    getDelayPredictions(flights=flights)

    return flights


@app.route('/')
def hello():
    return 'Flight Predictions API v1.0'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

