Here are some APIs used to access the weather inquiry system. You need to answer the question by writing python code to call appreciate APIs. The API can be accessed via HTTP request. 

The HTTP header is:

```python
headers = {
	"X-RapidAPI-Key": "0ade7be5b2mshd53f97c3d81bcd4p1587abjsn25826e5f4a79",
	"X-RapidAPI-Host": "weatherapi-com.p.rapidapi.com"
}
```

Here are the details of given APIs, including their http url, API desciption, API parameters, usage and execution results. Only key execution results are remained due to the limted space.

[1] https://weatherapi-com.p.rapidapi.com/current.json
## Description: 
get the real-time weather information for specific area, which includes wind degree, wind mp, humidity, gust mph and visibility in mile.
## Parameters:
q: the name of a city, such Beijing, London and New York.
## Usage:
```python
url = "https://weatherapi-com.p.rapidapi.com/current.json"
querystring = {"q":" New York"}
response = requests.get(url, headers=headers, params=querystring)
```
## Execution result:
```python
{
  "current": {
    "wind_mph": 2.2,
    "wind_kph": 3.6,
    "wind_degree": 10,
    "pressure_mb": 1030,
    "pressure_in": 30.42,
    "precip_mm": 0.04,
    "precip_in": 0,
    "humidity": 86,
    "cloud": 100,
    "vis_miles": 4,
    "gust_mph": 5.4,
    "gust_kph": 8.7
  }
}
```

[2] https://weatherapi-com.p.rapidapi.com/forecast.json
## Description: 
This api returns upto next 14 day weather forecast and weather alert as json. It contains astronomy data, day weather forecast and hourly interval weather information for a given city.
## Parameters:
- q: the name of a specific city
- days: number of days of forecast required. (e.g., 3 means the weather after 3 days.)
## Usage:
```python
url = "https://weatherapi-com.p.rapidapi.com/forecast.json"
querystring = {"q":"London","days":"3"}
response = requests.get(url, headers=headers, params=querystring)
```
## Execution result:
```json
{
  "location": {
    "name": "London",
    "region": "City of London, Greater London",
    "country": "United Kingdom",
    "lat": 51.52,
    "lon": -0.11,
    "tz_id": "Europe/London",
    "localtime_epoch": 1703416667,
    "localtime": "2023-12-24 11:17"
  }
}
```

[3] https://weatherapi-com.p.rapidapi.com/timezone.json
## Description: 
get the date time zone and local time information in json
## Parameters:
- q: the city name.
## Usage:
```python
url = "https://weatherapi-com.p.rapidapi.com/timezone.json"
querystring = {"q":"London"}
response = requests.get(url, headers=headers, params=querystring)
```
## Execution result:
```json
{
  "location": {
    "name": "London",
    "region": "City of London, Greater London",
    "country": "United Kingdom",
    "lat": 51.52,
    "lon": -0.11,
    "tz_id": "Europe/London",
    "localtime_epoch": 1703417066,
    "localtime": "2023-12-24 11:24"
  }
}
```

[4] https://weatherapi-com.p.rapidapi.com/astronomy.json
## Description:
this API allows a user to get up to date information for sunrise, sunset, moonrise, moonset, moon phase and illumination in json.
## Parameters:
- q: a specific name of city, like London.
## Usage:
```python
url = "https://weatherapi-com.p.rapidapi.com/astronomy.json"
querystring = {"q":"London"}
response = requests.get(url, headers=headers, params=querystring)
```
## Execution result:
```json
{
  "astronomy": {
    "astro": {
      "sunrise": "08:05 AM",
      "sunset": "03:55 PM",
      "moonrise": "01:35 PM",
      "moonset": "05:39 AM",
      "moon_phase": "Waxing Gibbous",
      "moon_illumination": 90,
      "is_moon_up": 1,
      "is_sun_up": 0
    }
  }
}
```

[5] https://weatherapi-com.p.rapidapi.com/history.json
## Description: 
This API returns historical weather for a date on or after 1st Jan, 2010 (depending upon subscription level) as json.
## Parameters:
- q: the city name.
- dt: a specific date with yyyy-MM-dd format, e.g., 2023-12-20.
## Usage:
```python
url = "https://weatherapi-com.p.rapidapi.com/history.json"
querystring = {"q":"London","dt":"2023-12-20","lang":"en"}
response = requests.get(url, headers=headers, params=querystring)
```
## Execution result:
```json
{
  "forecast": {
    "forecastday": [
      {
        "day": {
          "maxtemp_c": 13.2,
          "mintemp_c": 10.1,
          "avgtemp_c": 12.2,
          "maxwind_kph": 29.9,
          "totalprecip_mm": 0.28,
          "totalprecip_in": 0.01,
          "totalsnow_cm": 0,
          "avgvis_miles": 6,
          "avghumidity": 86,
          "daily_chance_of_rain": 100
        },
        "astro": {
          "sunrise": "08:05 AM",
          "sunset": "03:55 PM",
          "moonrise": "01:35 PM",
          "moonset": "05:39 AM"
        }
      }
    ]
  }
}
```

[6] https://weatherapi-com.p.rapidapi.com/sports.json
## Description:
Sports API method allows a user to get listing of all upcoming sports events for football, cricket and golf in json.
## Parameters:
- q: the city name
## Usage:
```python
url = "https://weatherapi-com.p.rapidapi.com/sports.json"
querystring = {"q":"London"}
response = requests.get(url, headers=headers, params=querystring)
```
## Execution result:
```json
{
  "football": [
    {
      "stadium": "Arsenal",
      "country": "United Kingdom",
      "region": "",
      "tournament": "Premier League",
      "start": "2023-12-28 20:15",
      "match": "Arsenal vs West Ham United"
    },
    {
      "stadium": "Brentford Fc",
      "country": "United Kingdom",
      "region": "",
      "tournament": "Premier League",
      "start": "2023-12-27 19:30",
      "match": "Brentford vs Wolverhampton Wanderers"
    }
  ],
  "cricket": [],
  "golf": []
}
```

[7] https://weatherapi-com.p.rapidapi.com/ip.json
## Description: it allows a user to get up to date information for an IP address in json.
## Parameters:
- q: a specific IP for a city, like "100.0.0.1" for Boston 
## Usage:
```python
url = "https://weatherapi-com.p.rapidapi.com/ip.json"
querystring = {"q":"100.0.0.1"}
response = requests.get(url, headers=headers, params=querystring)
```
## Execution result:
```json
{
	"continent_code": "NA",
  "continent_name": "North America",
  "country_code": "US",
  "country_name": "United States",
  "geoname_id": 4930956,
  "city": "Boston",
  "region": "Massachusetts",
  "lat": 42.3601,
  "lon": -71.0589,
  "tz_id": "America/New_York",
}
```

[8] https://weatherapi-com.p.rapidapi.com/search.json
## Description: 
Search or Autocomplete API returns matching cities and towns.
## Parameters:
- q: the city name.
## Usage:
```python
url = "https://weatherapi-com.p.rapidapi.com/search.json"
querystring = {"q":"london"}
response = requests.get(url, headers=headers, params=querystring)
```
## Execution result:
```json
{
  "ip": "100.0.0.1",
  "type": "ipv4",
  "continent_code": "NA",
  "continent_name": "North America",
  "country_code": "US",
  "country_name": "United States",
  "is_eu": "false",
  "geoname_id": 4930956,
  "city": "Boston",
  "region": "Massachusetts",
  "lat": 42.3601,
  "lon": -71.0589,
  "tz_id": "America/New_York",
}
```

[9] https://localhost/calculation.json
## Description: 
compute the given expression and return the value.
## Parameters:
- e: the experssion need to computing, e.g., "2+4-1", '2*6/8'
## Usage:
```python
url = "https://localhost/calculation.json"
querystring = {"e":"2+4-1"}
response = requests.get(url, params=querystring)
```
## Execution result:
```json
{
  "result": 5
}
```

Based on provided APIs, please write python code to call API and solve it. You need to provide Python code that can be executed directly; any explanations should be marked as Python comments.

Question: What is the average temperature in Shanghai for the coming week?