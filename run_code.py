import requests

# Set the API url to search for person
url_search_person = "https://api.themoviedb.org/3/search/person"
# Set the API url to get the movie credits for a person
url_person_movie_credits = "https://api.themoviedb.org/3/person/{person_id}/movie_credits"
# Set the headers for authorization
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s"
}


# Define a function to get the person ID by searching for specific name
def get_person_id(name):
    # Prepare the parameters for searching the person
    params_search_person = {
        "query": name,
        "page": 1,
        "include_adult": False
    }
    # Send a GET request to search for the person
    response_search_person = requests.get(url_search_person, headers=headers, params=params_search_person)

    # Check if the response is successful
    if response_search_person.status_code == 200:
        # Extract the person ID from the response
        person_id = response_search_person.json()["results"][0]["id"]
        return person_id
    else:
        return None


# Define a function to get the movie credits of a person
def get_movie_credits(person_id):
    # Replace the variable in the URL with the actual person ID
    url = url_person_movie_credits.format(person_id=person_id)
    # Send a GET request to get the movie credits
    response = requests.get(url, headers=headers)

    # Check if the response is successful
    if response.status_code == 200:
        # Extract the cast information from the response
        cast = response.json()["cast"]
        return cast
    else:
        return None


# Search for Sofia Coppola's person ID
sofia_coppola_id = get_person_id("Sofia Coppola")

# Get the movie credits for Sofia Coppola
movies_directed_by_sofia = []
if sofia_coppola_id:
    cast_list = get_movie_credits(sofia_coppola_id)
    # Check if the cast list is not empty
    if cast_list:
        # Iterate through the cast list to find movies directed by Sofia Coppola
        for movie in cast_list:
            if 'Director' in movie["job"]:
                movies_directed_by_sofia.append(movie["title"])

# Print the number of movies directed by Sofia Coppola
print(len(movies_directed_by_sofia))