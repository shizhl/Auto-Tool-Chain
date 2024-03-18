import requests
from utilize.apis import get_from_openai

access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
headers = {
    'Authorization': f'Bearer {access_token}'
}
# Define the API endpoint to get the TV show id for Breaking Bad
url_search_tv = "https://api.themoviedb.org/3/search/tv"
params_search_tv = {
    "query": "Breaking Bad"
}
response_search_tv = requests.get(url_search_tv, headers=headers, params=params_search_tv)
search_results = response_search_tv.json()

# Extract the TV show id for Breaking Bad
tv_id = search_results['results'][0]['id']

# Call the API to get reviews for Breaking Bad
url_reviews = f"https://api.themoviedb.org/3/tv/{tv_id}/reviews"
params_reviews = {
    "page": 1
}
response_reviews = requests.get(url_reviews, headers=headers, params=params_reviews)
reviews = response_reviews.json()

# Print the review for Breaking Bad
print("Review for Breaking Bad:")
print(reviews['results'][0]['content'])

# Summarize the review using a generic instruction
instruction = "Summarize the review for Breaking Bad"
print(reviews['results'][0]['content'])

print("\nSummary of the review:")

