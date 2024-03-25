from langchain.agents import Tool
from langchain_experimental.utilities import PythonREPL

code = """

def get_movie_keywords():
    import requests
    headers = {
        'Authorization': f'Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
    }
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/keywords"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        keywords = response.json()
        return keywords
    else:
        return None
movie_id = 550  # Fight Club movie ID
keywords = get_movie_keywords()
if keywords:
    print("Keywords for Fight Club:")
    for keyword in keywords['keywords']:
        print(keyword['name'])
else:
    print("Failed to retrieve keywords.")
"""
python_repl = PythonREPL()

res=  python_repl.run(code)
print(res)