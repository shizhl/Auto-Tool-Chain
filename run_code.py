# import requests
# import json
#
# headers = {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'}
#
code = """import requests
import json

url = "https://api.themoviedb.org/3/movie/550/keywords"
params = {}
response = requests.get(url, headers=headers, params=params)
print(json.dumps(response.json()))
"""
#
# code = '\n'.join(['\t'+e.strip() for e in code.split('\n')])
#
# exec_code = """import sys
# from io import StringIO
# import requests
#
# # 重定向 stdout
# old_stdout = sys.stdout
# redirected_output = StringIO()
# sys.stdout = redirected_output
#
# headers = {{
#     'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
# }}
#
# try:
# {code}
# except Exception as e:
#     # 捕获异常信息
#     channel.send((str(e), False))
# else:
#     # 如果没有异常发生，恢复原始 stdout，并获取重定向输出的内容
#     sys.stdout = old_stdout
#     output = redirected_output.getvalue()
#     # 发送标准输出内容和任何异常信息
#     channel.send((output, True))
# """.format(code=code)
#
# print(exec_code)

import requests
import json

headers = {'Authorization': 'Bearer BQAVqRTh8fS55tDB9xseAHRmSw-kJ3odKn0KIC6H1jT5zFrhb4LVEpQ7CjhDj8n9bGBz57VQGbNE-wuAzE7C1X7Bj9erZ0CWcF5HzG3e7Y2fIUkQaZSmr0XxgwGZLXR8v576WSFJ2BwW-FYOLuJohqVuiHSjyu81WZ0PhyET8xhVyGTVvOBYAOC0ZDM1KAyXHusAKCeuGQGW4XDYjSz2FPA68tL_8JjCwM3sa-LNbyMImxe9b9YExGXSPXzaWrmxbDSGimBgN0u08Y-qze1rtOzAjF2l5aGWTmBB1XLm1VURj-H9aCejl8Ygh6gruC4UslL8dEGc0KlGBHljOsBCqnJz'}

url = "https://api.spotify.com/v1/me/albums"
params = {"ids": "4iV5W9uYEdYUVa79Axb7Rh,1301WleyT98MSxVHPZCA6M"} # Example Spotify IDs

response = requests.delete(url, headers=headers, params=params)

print(json.dumps(response.json(), indent=0))