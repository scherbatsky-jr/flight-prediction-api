# Flight Prediction API 

This project is accordance to Machine Learning Course for 2023 August Semester in Asian Institute of Tenchnology, Thailand. The contributors to this project are as follows (alphabetically):

- Biraj Koirala
- Jannutun Nayeem
- Jiewen Shen
- Stabya Acharya
- Sunil Prajapati


## Description

The project is targeted towards predicing the possible deplay for airlines. The api provides a REST endpoint to fetch the flight informations for a certain day and the corresponding delay for arrival.

The api is currently deployed with Heroku at: https://flight-prediction-api-e1805e5c4a40.herokuapp.com/

## Project Directory Structure:
<pre>
app
├── <a href="https://github.com/scherbatsky-jr/flight-prediction-api/tree/main/datasets">datasets</a>
├── <a href="https://github.com/scherbatsky-jr/flight-prediction-api/tree/main/models">models</a>
├── <a href="https://github.com/scherbatsky-jr/flight-prediction-api/tree/main/notebooks">notebooks</a>
├── <a href="https://github.com/scherbatsky-jr/flight-prediction-api/tree/main/services">services</a>
└── <a href="https://github.com/scherbatsky-jr/flight-prediction-api/blob/main/app.py">app.py</a>
</pre>


### To run the flask server

First install the required packages listed in the requirements.txt

Copy the .env.example to .env file for environment variables. Update these variables as necessary.

```
X_RAPIDAPI_KEY=
X_RAPIDAPI_HOST=flight-info-api.p.rapidapi.com
X_RAPIDAPI_URL=https://flight-info-api.p.rapidapi.com/schedules

APP_URL=http://localhost:5173
APP_PORT=5000
```

The server can be started with command:

`python3 app.py`

The server endpoint should be available for at http://localhost:5000


### Using the predictions endpoint:

The server will be provid a POST endpoint `/predictions` to recieve the request from the app. The example request body is shown below:
```
{
    "originCode": "BWI",
    "originID": 1
    "destinatioCode": "DFW",
    "destinationID": 2,
    "date": "2023-10-20",
    "lat": 2.7777,
    "long": -27777
}
```