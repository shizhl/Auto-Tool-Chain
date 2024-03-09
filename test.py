import requests

access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
headers = {
    'Authorization': f'Bearer {access_token}'
}
import requests

# List of recommended movies for Titanic
def get_recommendations(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations"
    params = {
        "page": 1,
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    return data

# Get movie_id for Titanic
def search_movie(query):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "query": query,
        "page": 1,
        "include_adult": False
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if data["total_results"] > 0:
        # Assuming the first result is the correct movie
        movie_id = data["results"][0]["id"]
        return movie_id
    else:
        return None

# Search for Titanic
query = "Titanic"
titanic_id = search_movie(query)

if titanic_id:
    recommendations_data = get_recommendations(titanic_id)
    if recommendations_data["total_results"] > 0:
        recommended_movies = recommendations_data["results"]
        for movie in recommended_movies:
            print(movie["title"])
    else:
        print("No recommendations found")
else:
    print("Movie not found")

