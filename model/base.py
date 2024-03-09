import copy
import json
from utilize.apis import get_from_openai
import spotipy
import yaml
import os


class Base:

    def __init__(self, model_name='gpt-3.5-turbo'):
        self.model_name = model_name
        self.token = []

    def normalize(self, sss):
        return sss

    def generate(self, messages):
        res = get_from_openai(model_name=self.model_name, messages=messages)
        self.token.append([res['usage'].completion_tokens, res['usage'].prompt_tokens, res['usage'].total_tokens])
        return self.normalize(res['content'])

    def get_token(self):
        tmp = []
        for line in self.token:
            tmp = [e1 + e2 for e1, e2 in zip(tmp, line)]
        return tmp




class Tools:

    def __init__(self, system, oas_spec):
        self.system = system
        self.api_spec = json.load(open(oas_spec))
        self.api_spec = json.load(open(oas_spec))
        self.endpoint = {}
        self.host = self.api_spec['servers'][0]['url']
        for line in self.api_spec['endpoints']:
            # print(line)
            tmp = {
                "name": line[0].split(' ')[0] + ' ' + self.host + line[0].split(' ')[-1],  # unique id for each api
                "url": self.host + line[0].split(' ')[-1],
                "method": line[0].split(' ')[0],
                "description": line[1],
                "parameter": line[-1]['parameters'] if 'parameters' in line[-1] else [],
                "usage": None,
            }
            if 'responses' in line[-1] and 'content' in line[-1]['responses']:
                tmp['responses'] = line[-1]['responses']['content']['application/json']["schema"]['properties']
                tmp['responses']=self.simplify_response_template({"type":"",'properties':tmp['responses']})['properties']
            else:
                tmp['responses'] = 'This API has no return value.'
            if 'requestBody' in line[-1]:
                tmp['requestBody'] = line[-1]['requestBody']['content']['application/json']["schema"]['properties']
            else:
                tmp['requestBody'] = 'This API do not need the request body when calling.'
            self.endpoint[tmp['name']] = tmp

    def match(self, name):

        return name

    def get_tool_list(self, ):

        tmp = [k for k, v in self.endpoint.items()]
        return tmp

    def get_doc_by_name(self, name):
        tool = self.match(name.strip())
        return self.endpoint[tool]

    def normalize(self, sss):
        tmp = [
            '(/documentation/web-api/#spotify-uris-and-ids)',
            '(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)',
            '(https://www.spotify.com/se/account/overview/)',
            '<br/>',
            '<br>',
            '\n',
            '/documentation/general/guides/track-relinking-guide/',
            '(http://en.wikipedia.org/wiki/Universal_Product_Code)',
            '(http://en.wikipedia.org/wiki/International_Standard_Recording_Code)',
            '/documentation/web-api/#spotify-uris-and-ids'
            ''
        ]
        for s in tmp:
            sss = sss.replace(s, '')
        return sss

    def formulate(self, tool):
        print(tool)
        doc = self.get_doc_by_name(tool)
        if len(doc['parameter']) == 0:
            parameter = '## Parameter:\nNo extra parameter, just replace the `{variable}` in the url path with actual value.'
        else:
            parameter = []
            for p in doc['parameter']:
                if p['in'] != 'query':
                    continue
                tmp = "- " + p['name'] + ": " + self.normalize(p['description'])
                if 'schema' in p and 'type' in p['schema']:
                    tmp += " (type: " + p['schema']['type'] + ")"
                parameter.append(tmp)
            parameter = '\n'.join(parameter)
        # print(tool)
        response = json.dumps(doc['responses'], indent=4)
        requestBody = json.dumps(doc['requestBody'], indent=4)
        text_doc = """API url: {url}
## Request type:
{method}
## Description
{description}
## Parameter
{parameter}
## Execution result
{responses}
## Request body
{requestBody}
""".format(url=doc['url'],
           description=doc['description'].replace('\n', ' '),
           parameter=parameter,
           responses=response,
           requestBody=requestBody,
           method=doc['method'])
        return text_doc

    def simplify_response_template(self,data):
        if 'required' in data and 'properties' in data:
            for k, v in data['properties'].items():
                if k not in data['required']:
                    data.pop(k)

        results = {}
        for k, v in data.items():
            if k == 'properties':
                if 'properties' not in results:
                    results['properties'] = {}
                for t1, t2 in v.items():
                    results['properties'][t1] = simplify_response_template1(copy.deepcopy(t2))
            elif k in ['example', 'nullable', 'x-spotify-docs-type', 'required']:
                continue
            elif k == 'description':
                results[k] = self.normalize(v)
            else:
                results[k] = v
        return results

class TMDBTools(Tools):

    def __init__(self, system, oas_spec):
        super(TMDBTools, self).__init__(system=system, oas_spec=oas_spec)
        access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
        self.header = {
            'Authorization': f'Bearer {access_token}'
        }

    def get_instruction(self, query, tools):
        docs = [f'{i}. ' + self.formulate(tool) for i, tool in enumerate(tools, start=1)]

        instruction = """{system}

Here are the OpenAPI Specification of given APIs, including their http url, description, arguments and execution results.
{docs}

You should use the following Http header to call the API:
```python
headers = {header}
```
Note: I will give you 'headers', do not make up one, just reference it in your code. Here is an example to request the API:
```python
import requests
url = "<The API url selected from the above APIs>"
params = "<The params dict>"
response = requests.get(url, headers=headers, params=params)
```
If the API path contains "{{}}", it means that it is a variable and you should replace it with the appropriate value. For example, if the path is "/users/{{user_id}}/tweets", you should replace "{{user_id}}" with the user id. "{{" and "}}" cannot appear in the url.

Based on provided APIs, please write python code to call API and solve it. You need to provide Python code that can be executed directly; any explanations should be marked as Python comments.

Query: {query}
Your output:
```python
[Please write the code]
```""".format(system=self.system, header=json.dumps(self.header, indent=4), query=query, docs='\n'.join(docs))
        return instruction


class SpotifyTools(Tools):

    def __init__(self, system, oas_spec):
        super(SpotifyTools, self).__init__(system=system, oas_spec=oas_spec)
        config = yaml.load(open('D:/Paper2024/CodeTool/dataset/spotify_config.yaml', 'r'), Loader=yaml.FullLoader)
        os.environ['SPOTIPY_CLIENT_ID'] = config['spotipy_client_id']
        os.environ['SPOTIPY_CLIENT_SECRET'] = config['spotipy_client_secret']
        os.environ['SPOTIPY_REDIRECT_URI'] = config['spotipy_redirect_uri']

        with open("D:/Paper2024/CodeTool/specs/spotify_oas.json") as f:
            raw_api_spec = json.load(f)
        scopes = list(
            raw_api_spec['components']['securitySchemes']['oauth_2_0']['flows']['authorizationCode'][
                'scopes'].keys())
        access_token = spotipy.util.prompt_for_user_token(scope=','.join(scopes))
        self.header = {
            'Authorization': f'Bearer {access_token}'
        }

    def get_instruction(self, query, tools):
        docs = [f'{i}. ' + self.formulate(tool) for i, tool in enumerate(tools, start=1)]

        instruction = """{system}

Here are the OpenAPI Specification of given APIs, including their http url, description, arguments and execution results.
{docs}

You should use the following Http header to call the API:
```python
headers = {header}
```
Note: I will give you 'headers', do not make up one, just reference it in your code. Here is an example to request the API:
```python
import requests
url = "<The API url selected from the above APIs>"
params = "<The params dict>"
method = "<The Http request type, e.g., POST, GET, PUT and DELETE>"
if method == "GET":
    response = requests.get(url, headers=headers, params=params)
elif method == "POST":
    request_body = "<The request body>"
    response = requests.post(url, headers=headers, params=params, data=request_body)
elif method == "PUT":
    request_body = "<The request body>"
    response = requests.put(url, headers=headers, params=params, data=request_body)
elif method == "DELETE":
    request_body = "<The request body>"
    response = requests.delete(url, headers=headers, params=params, json=request_body)
```
If the API path contains "{{}}", it means that it is a variable and you should replace it with the appropriate value. For example, if the path is "/users/{{user_id}}/tweets", you should replace "{{user_id}}" with the user id. "{{" and "}}" cannot appear in the url.

Based on provided APIs, please write python code to call API and solve it. You need to provide Python code that can be executed directly; any explanations should be marked as Python comments.

Query: {query}
Your output:
```python
[Please write the code]
```""".format(system=self.system, header=json.dumps(self.header, indent=4), query=query, docs='\n'.join(docs))

        return instruction


def normalize(sss):
    tmp = [
        '(/documentation/web-api/#spotify-uris-and-ids)',
        '(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)',
        '(https://www.spotify.com/se/account/overview/)',
        '<br/>',
        '<br>',
        '\n',
        '/documentation/general/guides/track-relinking-guide/',
        '(http://en.wikipedia.org/wiki/Universal_Product_Code)',
        '(http://en.wikipedia.org/wiki/International_Standard_Recording_Code)',
        '/documentation/web-api/#spotify-uris-and-ids'
        ''
    ]
    for s in tmp:
        sss = sss.replace(s, '')
    return sss

def simplify_response_template(data):
    if 'required' in data and 'properties' in data:
        for k, v in data['properties'].items():
            if k not in data['required']:
                data.pop(k)
    if 'type' in data and data['type']=='object' and 'properties' in data:
        for k, v in data['properties'].items():
            data['properties'][k] = simplify_response_template(v)
    else:
        for k, v in data.items():
            if k in ['example', 'nullable', 'x-spotify-docs-type']:
                data.pop(k)
            if k == 'description':
                data[k] = normalize(v)
    return data

def simplify_response_template1(data):
    if 'required' in data and 'properties' in data:
        for k, v in data['properties'].items():
            if k not in data['required']:
                data.pop(k)

    results={}
    for k,v in data.items():
        if k=='properties':
            if 'properties' not in results:
                results['properties'] = {}
            for t1,t2 in v.items():
                results['properties'][t1]=simplify_response_template1(copy.deepcopy(t2))
        elif k in ['example', 'nullable', 'x-spotify-docs-type','required']:
            continue
        elif k == 'description':
            results[k] = normalize(v)
        else:
            results[k]=v
    return results


a={}
a['type']='object'
a['properties']={'albums': {'properties': {'href': {'description': 'A link to the Web API endpoint returning the full result of the request\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=0&limit=20\n', 'type': 'string'}, 'limit': {'description': 'The maximum number of items in the response (as set in the query or by default).\n', 'example': '20', 'type': 'integer'}, 'next': {'description': 'URL to the next page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'offset': {'description': 'The offset of the items returned (as set in the query or by default)\n', 'example': '0', 'type': 'integer'}, 'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of items available to return.\n', 'example': '4',
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       'type': 'integer'},
                              'items': {'items': {'properties': {'album_type': {'description': 'The type of the album.\n', 'enum': ['album', 'single', 'compilation'], 'example': 'compilation', 'type': 'string'}, 'available_markets': {'description': 'The markets in which the album is available: [ISO 3166-1 alpha-2 country codes](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2). _**NOTE**: an album is considered available in a market when at least 1 of its tracks is available in that market._\n', 'example': ['CA', 'BR', 'IT'], 'items': {'type': 'string'}, 'type': 'array'}, 'copyrights': {'description': 'The copyright statements of the album.\n', 'items': {'properties': {'text': {'description': 'The copyright text for this content.\n', 'type': 'string'}, 'type': {'description': 'The type of copyright: `C` = the copyright, `P` = the sound recording (performance) copyright.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'CopyrightObject'}, 'type': 'array'}, 'external_ids': {'properties': {'ean': {'description': '[International Article Number](http://en.wikipedia.org/wiki/International_Article_Number_%28EAN%29)\n', 'type': 'string'}, 'isrc': {'description': '[International Standard Recording Code](http://en.wikipedia.org/wiki/International_Standard_Recording_Code)\n', 'type': 'string'}, 'upc': {'description': '[Universal Product Code](http://en.wikipedia.org/wiki/Universal_Product_Code)\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'genres': {'description': 'A list of the genres the album is associated with. If not yet classified, the array is empty.\n', 'example': ['Egg punk', 'Noise rock'], 'items': {'type': 'string'}, 'type': 'array'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the album.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the album.\n', 'example': '2up3OPMp9Tb4dAKM2erWXQ', 'type': 'string'}, 'images': {'description': 'The cover art for the album in various sizes, widest first.\n', 'items': {'properties': {'height': {'description': 'The image height in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}, 'url': {'description': 'The source URL of the image.\n', 'example': 'https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228\n', 'type': 'string'}, 'width': {'description': 'The image width in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}}, 'required': ['url', 'height', 'width'], 'type': 'object', 'x-spotify-docs-type': 'ImageObject'}, 'type': 'array'}, 'label': {'description': 'The label associated with the album.\n', 'type': 'string'}, 'name': {'description': 'The name of the album. In case of an album takedown, the value may be an empty string.\n', 'type': 'string'}, 'popularity': {'description': 'The popularity of the album. The value will be between 0 and 100, with 100 being the most popular.\n', 'type': 'integer'}, 'release_date': {'description': 'The date the album was first released.\n', 'example': '1981-12', 'type': 'string'}, 'release_date_precision': {'description': 'The precision with which `release_date` value is known.\n', 'enum': ['year', 'month', 'day'], 'example': 'year', 'type': 'string'}, 'restrictions': {'properties': {'reason': {'description': "The reason for the restriction. Albums may be restricted if the content is not available in a given market, to the user's subscription type, or when the user's account is set to not play explicit content.\nAdditional reasons may be added in the future.\n", 'enum': ['market', 'product', 'explicit'], 'type': 'string'}}, 'required': [], 'type': 'object'}, 'total_tracks': {'description': 'The number of tracks in the album.', 'example': '9', 'type': 'integer'}, 'type': {'description': 'The object type.\n', 'enum': ['album'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the album.\n', 'example': 'spotify:album:2up3OPMp9Tb4dAKM2erWXQ', 'type': 'string'}, 'album_group': {'description': "The field is present when getting an artist's albums. Compare to album_type this field represents relationship between the artist and the album.\n", 'enum': ['album', 'single', 'compilation', 'appears_on'], 'example': 'compilation', 'type': 'string'}, 'artists': {'description': 'The artists of the album. Each artist object includes a link in `href` to more detailed information about the artist.\n', 'items': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the artist.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}, 'name': {'description': 'The name of the artist.\n', 'type': 'string'}, 'type': {'description': 'The object type.\n', 'enum': ['artist'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedArtistObject'}, 'type': 'array'}}, 'required': ['album_type', 'total_tracks', 'available_markets', 'external_urls', 'href', 'id', 'images', 'name', 'release_date', 'release_date_precision', 'type', 'uri', 'artists'], 'type': 'object'}, 'type': 'array'}}, 'required': ['href', 'items', 'limit', 'next', 'offset', 'previous', 'total'], 'type': 'object'}, 'artists': {'properties': {'href': {'description': 'A link to the Web API endpoint returning the full result of the request\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=0&limit=20\n', 'type': 'string'}, 'limit': {'description': 'The maximum number of items in the response (as set in the query or by default).\n', 'example': '20', 'type': 'integer'}, 'next': {'description': 'URL to the next page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'offset': {'description': 'The offset of the items returned (as set in the query or by default)\n', 'example': '0', 'type': 'integer'}, 'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of items available to return.\n', 'example': '4', 'type': 'integer'}, 'items': {'items': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'followers': {'properties': {'href': {'description': 'This will always be set to null, as the Web API does not support it at the moment.\n', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of followers.\n', 'type': 'integer'}}, 'required': [], 'type': 'object'}, 'genres': {'description': 'A list of the genres the artist is associated with. If not yet classified, the array is empty.\n', 'example': ['Prog rock', 'Grunge'], 'items': {'type': 'string'}, 'type': 'array'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the artist.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}, 'images': {'description': 'Images of the artist in various sizes, widest first.\n', 'items': {'properties': {'height': {'description': 'The image height in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}, 'url': {'description': 'The source URL of the image.\n', 'example': 'https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228\n', 'type': 'string'}, 'width': {'description': 'The image width in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}}, 'required': ['url', 'height', 'width'], 'type': 'object', 'x-spotify-docs-type': 'ImageObject'}, 'type': 'array'}, 'name': {'description': 'The name of the artist.\n', 'type': 'string'}, 'popularity': {'description': "The popularity of the artist. The value will be between 0 and 100, with 100 being the most popular. The artist's popularity is calculated from the popularity of all the artist's tracks.\n", 'type': 'integer'}, 'type': {'description': 'The object type.\n', 'enum': ['artist'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'ArtistObject'}, 'type': 'array'}}, 'required': ['href', 'items', 'limit', 'next', 'offset', 'previous', 'total'], 'type': 'object'}, 'audiobooks': {'properties': {'href': {'description': 'A link to the Web API endpoint returning the full result of the request\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=0&limit=20\n', 'type': 'string'}, 'limit': {'description': 'The maximum number of items in the response (as set in the query or by default).\n', 'example': '20', 'type': 'integer'}, 'next': {'description': 'URL to the next page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'offset': {'description': 'The offset of the items returned (as set in the query or by default)\n', 'example': '0', 'type': 'integer'}, 'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of items available to return.\n', 'example': '4', 'type': 'integer'}, 'items': {'items': {'properties': {'authors': {'description': 'The author(s) for the audiobook.\n', 'items': {'properties': {'name': {'description': 'The name of the author.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'AuthorObject'}, 'type': 'array'}, 'available_markets': {'description': 'A list of the countries in which the audiobook can be played, identified by their [ISO 3166-1 alpha-2](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code.\n', 'items': {'type': 'string'}, 'type': 'array'}, 'copyrights': {'description': 'The copyright statements of the audiobook.\n', 'items': {'properties': {'text': {'description': 'The copyright text for this content.\n', 'type': 'string'}, 'type': {'description': 'The type of copyright: `C` = the copyright, `P` = the sound recording (performance) copyright.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'CopyrightObject'}, 'type': 'array'}, 'description': {'description': 'A description of the audiobook. HTML tags are stripped away from this field, use `html_description` field in case HTML tags are needed.\n', 'type': 'string'}, 'edition': {'description': 'The edition of the audiobook.\n', 'example': 'Unabridged', 'type': 'string'}, 'explicit': {'description': 'Whether or not the audiobook has explicit content (true = yes it does; false = no it does not OR unknown).\n', 'type': 'boolean'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the audiobook.\n', 'type': 'string'}, 'html_description': {'description': 'A description of the audiobook. This field may contain HTML tags.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the audiobook.\n', 'type': 'string'}, 'images': {'description': 'The cover art for the audiobook in various sizes, widest first.\n', 'items': {'properties': {'height': {'description': 'The image height in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}, 'url': {'description': 'The source URL of the image.\n', 'example': 'https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228\n', 'type': 'string'}, 'width': {'description': 'The image width in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}}, 'required': ['url', 'height', 'width'], 'type': 'object', 'x-spotify-docs-type': 'ImageObject'}, 'type': 'array'}, 'languages': {'description': 'A list of the languages used in the audiobook, identified by their [ISO 639](https://en.wikipedia.org/wiki/ISO_639) code.\n', 'items': {'type': 'string'}, 'type': 'array'}, 'media_type': {'description': 'The media type of the audiobook.\n', 'type': 'string'}, 'name': {'description': 'The name of the audiobook.\n', 'type': 'string'}, 'narrators': {'description': 'The narrator(s) for the audiobook.\n', 'items': {'properties': {'name': {'description': 'The name of the Narrator.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'NarratorObject'}, 'type': 'array'}, 'publisher': {'description': 'The publisher of the audiobook.\n', 'type': 'string'}, 'total_chapters': {'description': 'The number of chapters in this audiobook.\n', 'type': 'integer'}, 'type': {'description': 'The object type.\n', 'enum': ['audiobook'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the audiobook.\n', 'type': 'string'}}, 'required': ['authors', 'available_markets', 'copyrights', 'description', 'explicit', 'external_urls', 'href', 'html_description', 'id', 'images', 'languages', 'media_type', 'name', 'narrators', 'publisher', 'total_chapters', 'type', 'uri'], 'type': 'object'}, 'type': 'array'}}, 'required': ['href', 'items', 'limit', 'next', 'offset', 'previous', 'total'], 'type': 'object'}, 'episodes': {'properties': {'href': {'description': 'A link to the Web API endpoint returning the full result of the request\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=0&limit=20\n', 'type': 'string'}, 'limit': {'description': 'The maximum number of items in the response (as set in the query or by default).\n', 'example': '20', 'type': 'integer'}, 'next': {'description': 'URL to the next page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'offset': {'description': 'The offset of the items returned (as set in the query or by default)\n', 'example': '0', 'type': 'integer'}, 'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of items available to return.\n', 'example': '4', 'type': 'integer'}, 'items': {'items': {'properties': {'audio_preview_url': {'description': 'A URL to a 30 second preview (MP3 format) of the episode. `null` if not available.\n', 'example': 'https://p.scdn.co/mp3-preview/2f37da1d4221f40b9d1a98cd191f4d6f1646ad17', 'type': 'string', 'x-spotify-policy-list': [{}]}, 'description': {'description': 'A description of the episode. HTML tags are stripped away from this field, use `html_description` field in case HTML tags are needed.\n', 'example': 'A Spotify podcast sharing fresh insights on important topics of the moment—in a way only Spotify can. You’ll hear from experts in the music, podcast and tech industries as we discover and uncover stories about our work and the world around us.\n', 'type': 'string'}, 'duration_ms': {'description': 'The episode length in milliseconds.\n', 'example': '1686230', 'type': 'integer'}, 'explicit': {'description': 'Whether or not the episode has explicit content (true = yes it does; false = no it does not OR unknown).\n', 'type': 'boolean'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the episode.\n', 'example': 'https://api.spotify.com/v1/episodes/5Xt5DXGzch68nYYamXrNxZ', 'type': 'string'}, 'html_description': {'description': 'A description of the episode. This field may contain HTML tags.\n', 'example': '<p>A Spotify podcast sharing fresh insights on important topics of the moment—in a way only Spotify can. You’ll hear from experts in the music, podcast and tech industries as we discover and uncover stories about our work and the world around us.</p>\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the episode.\n', 'example': '5Xt5DXGzch68nYYamXrNxZ', 'type': 'string'}, 'images': {'description': 'The cover art for the episode in various sizes, widest first.\n', 'items': {'properties': {'height': {'description': 'The image height in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}, 'url': {'description': 'The source URL of the image.\n', 'example': 'https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228\n', 'type': 'string'}, 'width': {'description': 'The image width in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}}, 'required': ['url', 'height', 'width'], 'type': 'object', 'x-spotify-docs-type': 'ImageObject'}, 'type': 'array'}, 'is_externally_hosted': {'description': "True if the episode is hosted outside of Spotify's CDN.\n", 'type': 'boolean'}, 'is_playable': {'description': 'True if the episode is playable in the given market. Otherwise false.\n', 'type': 'boolean'}, 'language': {'deprecated': 'true', 'description': 'The language used in the episode, identified by a [ISO 639](https://en.wikipedia.org/wiki/ISO_639) code. This field is deprecated and might be removed in the future. Please use the `languages` field instead.\n', 'example': 'en', 'type': 'string'}, 'languages': {'description': 'A list of the languages used in the episode, identified by their [ISO 639-1](https://en.wikipedia.org/wiki/ISO_639) code.\n', 'example': ['fr', 'en'], 'items': {'type': 'string'}, 'type': 'array'}, 'name': {'description': 'The name of the episode.\n', 'example': 'Starting Your Own Podcast: Tips, Tricks, and Advice From Anchor Creators\n', 'type': 'string'}, 'release_date': {'description': 'The date the episode was first released, for example `"1981-12-15"`. Depending on the precision, it might be shown as `"1981"` or `"1981-12"`.\n', 'example': '1981-12-15', 'type': 'string'}, 'release_date_precision': {'description': 'The precision with which `release_date` value is known.\n', 'enum': ['year', 'month', 'day'], 'example': 'day', 'type': 'string'}, 'restrictions': {'properties': {'reason': {'description': "The reason for the restriction. Supported values:\n- `market` - The content item is not available in the given market.\n- `product` - The content item is not available for the user's subscription type.\n- `explicit` - The content item is explicit and the user's account is set to not play explicit content.\n\nAdditional reasons may be added in the future.\n**Note**: If you use this field, make sure that your application safely handles unknown values.\n", 'type': 'string'}}, 'required': [], 'type': 'object'}, 'resume_point': {'properties': {'fully_played': {'description': 'Whether or not the episode has been fully played by the user.\n', 'type': 'boolean'}, 'resume_position_ms': {'description': "The user's most recent position in the episode in milliseconds.\n", 'type': 'integer'}}, 'required': [], 'type': 'object'}, 'type': {'description': 'The object type.\n', 'enum': ['episode'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the episode.\n', 'example': 'spotify:episode:0zLhl3WsOCQHbe1BPTiHgr', 'type': 'string'}}, 'required': ['audio_preview_url', 'description', 'html_description', 'duration_ms', 'explicit', 'external_urls', 'href', 'id', 'images', 'is_externally_hosted', 'is_playable', 'languages', 'name', 'release_date', 'release_date_precision', 'resume_point', 'type', 'uri'], 'type': 'object'}, 'type': 'array'}}, 'required': ['href', 'items', 'limit', 'next', 'offset', 'previous', 'total'], 'type': 'object'}, 'playlists': {'properties': {'href': {'description': 'A link to the Web API endpoint returning the full result of the request\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=0&limit=20\n', 'type': 'string'}, 'limit': {'description': 'The maximum number of items in the response (as set in the query or by default).\n', 'example': '20', 'type': 'integer'}, 'next': {'description': 'URL to the next page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'offset': {'description': 'The offset of the items returned (as set in the query or by default)\n', 'example': '0', 'type': 'integer'}, 'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of items available to return.\n', 'example': '4', 'type': 'integer'}, 'items': {'items': {'properties': {'collaborative': {'description': '`true` if the owner allows other users to modify the playlist.\n', 'type': 'boolean'}, 'description': {'description': 'The playlist description. _Only returned for modified, verified playlists, otherwise_ `null`.\n', 'type': 'string'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the playlist.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the playlist.\n', 'type': 'string'}, 'images': {'description': 'Images for the playlist. The array may be empty or contain up to three images. The images are returned by size in descending order. See [Working with Playlists](/documentation/general/guides/working-with-playlists/). _**Note**: If returned, the source URL for the image (`url`) is temporary and will expire in less than a day._\n', 'items': {'properties': {'height': {'description': 'The image height in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}, 'url': {'description': 'The source URL of the image.\n', 'example': 'https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228\n', 'type': 'string'}, 'width': {'description': 'The image width in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}}, 'required': ['url', 'height', 'width'], 'type': 'object', 'x-spotify-docs-type': 'ImageObject'}, 'type': 'array'}, 'name': {'description': 'The name of the playlist.\n', 'type': 'string'}, 'owner': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'followers': {'properties': {'href': {'description': 'This will always be set to null, as the Web API does not support it at the moment.\n', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of followers.\n', 'type': 'integer'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint for this user.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify user ID](/documentation/web-api/#spotify-uris-and-ids) for this user.\n', 'type': 'string'}, 'type': {'description': 'The object type.\n', 'enum': ['user'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for this user.\n', 'type': 'string'}, 'display_name': {'description': "The name displayed on the user's profile. `null` if not available.\n", 'nullable': 'true', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'public': {'description': "The playlist's public/private status: `true` the playlist is public, `false` the playlist is private, `null` the playlist status is not relevant. For more about public/private status, see [Working with Playlists](/documentation/general/guides/working-with-playlists/)\n", 'type': 'boolean'}, 'snapshot_id': {'description': 'The version identifier for the current playlist. Can be supplied in other requests to target a specific playlist version\n', 'type': 'string'}, 'tracks': {'properties': {'href': {'description': "A link to the Web API endpoint where full details of the playlist's tracks can be retrieved.\n", 'type': 'string'}, 'total': {'description': 'Number of tracks in the playlist.\n', 'type': 'integer'}}, 'required': [], 'type': 'object'}, 'type': {'description': 'The object type: "playlist"\n', 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the playlist.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedPlaylistObject'}, 'type': 'array'}}, 'required': ['href', 'items', 'limit', 'next', 'offset', 'previous', 'total'], 'type': 'object'}, 'shows': {'properties': {'href': {'description': 'A link to the Web API endpoint returning the full result of the request\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=0&limit=20\n', 'type': 'string'}, 'limit': {'description': 'The maximum number of items in the response (as set in the query or by default).\n', 'example': '20', 'type': 'integer'}, 'next': {'description': 'URL to the next page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'offset': {'description': 'The offset of the items returned (as set in the query or by default)\n', 'example': '0', 'type': 'integer'}, 'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of items available to return.\n', 'example': '4', 'type': 'integer'}, 'items': {'items': {'properties': {'available_markets': {'description': 'A list of the countries in which the show can be played, identified by their [ISO 3166-1 alpha-2](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code.\n', 'items': {'type': 'string'}, 'type': 'array'}, 'copyrights': {'description': 'The copyright statements of the show.\n', 'items': {'properties': {'text': {'description': 'The copyright text for this content.\n', 'type': 'string'}, 'type': {'description': 'The type of copyright: `C` = the copyright, `P` = the sound recording (performance) copyright.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'CopyrightObject'}, 'type': 'array'}, 'description': {'description': 'A description of the show. HTML tags are stripped away from this field, use `html_description` field in case HTML tags are needed.\n', 'type': 'string'}, 'explicit': {'description': 'Whether or not the show has explicit content (true = yes it does; false = no it does not OR unknown).\n', 'type': 'boolean'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the show.\n', 'type': 'string'}, 'html_description': {'description': 'A description of the show. This field may contain HTML tags.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the show.\n', 'type': 'string'}, 'images': {'description': 'The cover art for the show in various sizes, widest first.\n', 'items': {'properties': {'height': {'description': 'The image height in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}, 'url': {'description': 'The source URL of the image.\n', 'example': 'https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228\n', 'type': 'string'}, 'width': {'description': 'The image width in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}}, 'required': ['url', 'height', 'width'], 'type': 'object', 'x-spotify-docs-type': 'ImageObject'}, 'type': 'array'}, 'is_externally_hosted': {'description': "True if all of the shows episodes are hosted outside of Spotify's CDN. This field might be `null` in some cases.\n", 'type': 'boolean'}, 'languages': {'description': 'A list of the languages used in the show, identified by their [ISO 639](https://en.wikipedia.org/wiki/ISO_639) code.\n', 'items': {'type': 'string'}, 'type': 'array'}, 'media_type': {'description': 'The media type of the show.\n', 'type': 'string'}, 'name': {'description': 'The name of the episode.\n', 'type': 'string'}, 'publisher': {'description': 'The publisher of the show.\n', 'type': 'string'}, 'total_episodes': {'description': 'The total number of episodes in the show.\n', 'type': 'integer'}, 'type': {'description': 'The object type.\n', 'enum': ['show'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the show.\n', 'type': 'string'}}, 'required': ['available_markets', 'copyrights', 'description', 'explicit', 'external_urls', 'href', 'html_description', 'id', 'images', 'is_externally_hosted', 'languages', 'media_type', 'name', 'publisher', 'total_episodes', 'type', 'uri'], 'type': 'object'}, 'type': 'array'}}, 'required': ['href', 'items', 'limit', 'next', 'offset', 'previous', 'total'], 'type': 'object'}, 'tracks': {'properties': {'href': {'description': 'A link to the Web API endpoint returning the full result of the request\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=0&limit=20\n', 'type': 'string'}, 'limit': {'description': 'The maximum number of items in the response (as set in the query or by default).\n', 'example': '20', 'type': 'integer'}, 'next': {'description': 'URL to the next page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'offset': {'description': 'The offset of the items returned (as set in the query or by default)\n', 'example': '0', 'type': 'integer'}, 'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of items available to return.\n', 'example': '4', 'type': 'integer'}, 'items': {'items': {'properties': {'album': {'properties': {'album_type': {'description': 'The type of the album.\n', 'enum': ['album', 'single', 'compilation'], 'example': 'compilation', 'type': 'string'}, 'available_markets': {'description': 'The markets in which the album is available: [ISO 3166-1 alpha-2 country codes](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2). _**NOTE**: an album is considered available in a market when at least 1 of its tracks is available in that market._\n', 'example': ['CA', 'BR', 'IT'], 'items': {'type': 'string'}, 'type': 'array'}, 'copyrights': {'description': 'The copyright statements of the album.\n', 'items': {'properties': {'text': {'description': 'The copyright text for this content.\n', 'type': 'string'}, 'type': {'description': 'The type of copyright: `C` = the copyright, `P` = the sound recording (performance) copyright.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'CopyrightObject'}, 'type': 'array'}, 'external_ids': {'properties': {'ean': {'description': '[International Article Number](http://en.wikipedia.org/wiki/International_Article_Number_%28EAN%29)\n', 'type': 'string'}, 'isrc': {'description': '[International Standard Recording Code](http://en.wikipedia.org/wiki/International_Standard_Recording_Code)\n', 'type': 'string'}, 'upc': {'description': '[Universal Product Code](http://en.wikipedia.org/wiki/Universal_Product_Code)\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'genres': {'description': 'A list of the genres the album is associated with. If not yet classified, the array is empty.\n', 'example': ['Egg punk', 'Noise rock'], 'items': {'type': 'string'}, 'type': 'array'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the album.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the album.\n', 'example': '2up3OPMp9Tb4dAKM2erWXQ', 'type': 'string'}, 'images': {'description': 'The cover art for the album in various sizes, widest first.\n', 'items': {'properties': {'height': {'description': 'The image height in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}, 'url': {'description': 'The source URL of the image.\n', 'example': 'https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228\n', 'type': 'string'}, 'width': {'description': 'The image width in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}}, 'required': ['url', 'height', 'width'], 'type': 'object', 'x-spotify-docs-type': 'ImageObject'}, 'type': 'array'}, 'label': {'description': 'The label associated with the album.\n', 'type': 'string'}, 'name': {'description': 'The name of the album. In case of an album takedown, the value may be an empty string.\n', 'type': 'string'}, 'popularity': {'description': 'The popularity of the album. The value will be between 0 and 100, with 100 being the most popular.\n', 'type': 'integer'}, 'release_date': {'description': 'The date the album was first released.\n', 'example': '1981-12', 'type': 'string'}, 'release_date_precision': {'description': 'The precision with which `release_date` value is known.\n', 'enum': ['year', 'month', 'day'], 'example': 'year', 'type': 'string'}, 'restrictions': {'properties': {'reason': {'description': "The reason for the restriction. Albums may be restricted if the content is not available in a given market, to the user's subscription type, or when the user's account is set to not play explicit content.\nAdditional reasons may be added in the future.\n", 'enum': ['market', 'product', 'explicit'], 'type': 'string'}}, 'required': [], 'type': 'object'}, 'total_tracks': {'description': 'The number of tracks in the album.', 'example': '9', 'type': 'integer'}, 'type': {'description': 'The object type.\n', 'enum': ['album'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the album.\n', 'example': 'spotify:album:2up3OPMp9Tb4dAKM2erWXQ', 'type': 'string'}, 'album_group': {'description': "The field is present when getting an artist's albums. Compare to album_type this field represents relationship between the artist and the album.\n", 'enum': ['album', 'single', 'compilation', 'appears_on'], 'example': 'compilation', 'type': 'string'}, 'artists': {'description': 'The artists of the album. Each artist object includes a link in `href` to more detailed information about the artist.\n', 'items': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the artist.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}, 'name': {'description': 'The name of the artist.\n', 'type': 'string'}, 'type': {'description': 'The object type.\n', 'enum': ['artist'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedArtistObject'}, 'type': 'array'}}, 'required': ['album_type', 'total_tracks', 'available_markets', 'external_urls', 'href', 'id', 'images', 'name', 'release_date', 'release_date_precision', 'type', 'uri', 'artists'], 'type': 'object'}, 'artists': {'description': 'The artists who performed the track. Each artist object includes a link in `href` to more detailed information about the artist.\n', 'items': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'followers': {'properties': {'href': {'description': 'This will always be set to null, as the Web API does not support it at the moment.\n', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of followers.\n', 'type': 'integer'}}, 'required': [], 'type': 'object'}, 'genres': {'description': 'A list of the genres the artist is associated with. If not yet classified, the array is empty.\n', 'example': ['Prog rock', 'Grunge'], 'items': {'type': 'string'}, 'type': 'array'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the artist.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}, 'images': {'description': 'Images of the artist in various sizes, widest first.\n', 'items': {'properties': {'height': {'description': 'The image height in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}, 'url': {'description': 'The source URL of the image.\n', 'example': 'https://i.scdn.co/image/ab67616d00001e02ff9ca10b55ce82ae553c8228\n', 'type': 'string'}, 'width': {'description': 'The image width in pixels.\n', 'example': '300', 'nullable': 'true', 'type': 'integer'}}, 'required': ['url', 'height', 'width'], 'type': 'object', 'x-spotify-docs-type': 'ImageObject'}, 'type': 'array'}, 'name': {'description': 'The name of the artist.\n', 'type': 'string'}, 'popularity': {'description': "The popularity of the artist. The value will be between 0 and 100, with 100 being the most popular. The artist's popularity is calculated from the popularity of all the artist's tracks.\n", 'type': 'integer'}, 'type': {'description': 'The object type.\n', 'enum': ['artist'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'ArtistObject'}, 'type': 'array'}, 'available_markets': {'description': 'A list of the countries in which the track can be played, identified by their [ISO 3166-1 alpha-2](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code.\n', 'items': {'type': 'string'}, 'type': 'array'}, 'disc_number': {'description': 'The disc number (usually `1` unless the album consists of more than one disc).\n', 'type': 'integer'}, 'duration_ms': {'description': 'The track length in milliseconds.\n', 'type': 'integer'}, 'explicit': {'description': 'Whether or not the track has explicit lyrics ( `true` = yes it does; `false` = no it does not OR unknown).\n', 'type': 'boolean'}, 'external_ids': {'properties': {'ean': {'description': '[International Article Number](http://en.wikipedia.org/wiki/International_Article_Number_%28EAN%29)\n', 'type': 'string'}, 'isrc': {'description': '[International Standard Recording Code](http://en.wikipedia.org/wiki/International_Standard_Recording_Code)\n', 'type': 'string'}, 'upc': {'description': '[Universal Product Code](http://en.wikipedia.org/wiki/Universal_Product_Code)\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the track.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}, 'is_local': {'description': 'Whether or not the track is from a local file.\n', 'type': 'boolean'}, 'is_playable': {'description': 'Part of the response when [Track Relinking](/documentation/general/guides/track-relinking-guide/) is applied. If `true`, the track is playable in the given market. Otherwise `false`.\n', 'type': 'boolean'}, 'linked_from': {'description': 'Part of the response when [Track Relinking](/documentation/general/guides/track-relinking-guide/) is applied, and the requested track has been replaced with different track. The track in the `linked_from` object contains information about the originally requested track.\n', 'type': 'object'}, 'name': {'description': 'The name of the track.\n', 'type': 'string'}, 'popularity': {'description': 'The popularity of the track. The value will be between 0 and 100, with 100 being the most popular.<br/>The popularity of a track is a value between 0 and 100, with 100 being the most popular. The popularity is calculated by algorithm and is based, in the most part, on the total number of plays the track has had and how recent those plays are.<br/>Generally speaking, songs that are being played a lot now will have a higher popularity than songs that were played a lot in the past. Duplicate tracks (e.g. the same track from a single and an album) are rated independently. Artist and album popularity is derived mathematically from track popularity. _**Note**: the popularity value may lag actual popularity by a few days: the value is not updated in real time._\n', 'type': 'integer'}, 'preview_url': {'description': 'A link to a 30 second preview (MP3 format) of the track. Can be `null`\n', 'type': 'string', 'x-spotify-policy-list': [{}]}, 'restrictions': {'properties': {'reason': {'description': "The reason for the restriction. Supported values:\n- `market` - The content item is not available in the given market.\n- `product` - The content item is not available for the user's subscription type.\n- `explicit` - The content item is explicit and the user's account is set to not play explicit content.\n\nAdditional reasons may be added in the future.\n**Note**: If you use this field, make sure that your application safely handles unknown values.\n", 'type': 'string'}}, 'required': [], 'type': 'object'}, 'track_number': {'description': 'The number of the track. If an album has several discs, the track number is the number on the specified disc.\n', 'type': 'integer'}, 'type': {'description': 'The object type: "track".\n', 'enum': ['track'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'TrackObject'}, 'type': 'array'}}, 'required': ['href', 'items', 'limit', 'next', 'offset', 'previous', 'total'], 'type': 'object'}}
b=simplify_response_template1(a)
print(json.dumps(b))