import copy
import json
from utilize.apis import get_from_openai
import spotipy
import yaml
import os
from typing import Union
from tqdm import tqdm
from utilize.utilze import load_data
import random
import multiprocessing

import tiktoken
encoder = tiktoken.encoding_for_model('gpt-3.5-turbo')


class Base:

    def __init__(self, model_name='gpt-3.5-turbo'):
        self.model_name = model_name
        self.token = []

    def normalize(self, sss):
        return sss

    def generate(self, messages):
        res = get_from_openai(model_name=self.model_name, messages=messages,usage=True)
        self.token.append(res['usage'])
        return self.normalize(res['content']),res['usage']

    def get_token(self):
        tmp = []
        for line in self.token:
            tmp = [e1 + e2 for e1, e2 in zip(tmp, line)]
        return tmp


class Tools:

    def __init__(self, system, oas_spec):
        self.system = system
        self.api_spec = json.load(open(oas_spec))
        self.endpoint = {}
        self.host = self.api_spec['servers'][0]['url']
        for line in self.api_spec['endpoints']:
            # print(line)
            tmp = {
                "name": line[0] if self.host in line[0] else line[0].split(' ')[0] + ' ' + self.host + line[0].split(' ')[-1] ,  # unique id for each api
                "url": self.host + line[0].split(' ')[-1],
                "method": line[0].split(' ')[0],
                "description": self.normalize(line[1]),
                "parameter": line[-1]['parameters'] if 'parameters' in line[-1] else [],
                "usage": None,
            }
            if 'responses' in line[-1] and 'content' in line[-1]['responses']:
                tmp['responses'] = line[-1]['responses']['content']['application/json']["schema"]['properties']
                # tmp['responses']=self.simplify_dict({"type":"",'properties':tmp['responses']})['properties']
                tmp['responses'] = self.simplify_dict(tmp['responses'])
            else:
                tmp['responses'] = 'This API has no return value.'
            if '_responses_json' in line[-1]:
                tmp['_responses_json'] = line[-1]['_responses_json']
            if '_responses_yaml' in line[-1]:
                tmp['_responses_yaml'] = line[-1]['_responses_yaml']
            if 'requestBody' in line[-1]:
                tmp['requestBody'] = line[-1]['requestBody']['content']['application/json']["schema"]['properties']
                # tmp['requestBody'] = self.simplify_dict({"type":"",'properties':tmp['requestBody']})['properties']
                tmp['requestBody'] = self.simplify_dict(tmp['requestBody'])
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
        for s in ['<br />', '<br/>', '_**NOTE**:']:
            sss = sss.replace(s, '\n')
        sss = sss.split('\n')[0]
        tmp = [
            '(/documentation/web-api/#spotify-uris-and-ids)',
            '(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)',
            '(https://www.spotify.com/se/account/overview/)',
            '(http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)',
            '<br/>',
            '<br>',
            '<br />',
            '\n',
            '/documentation/general/guides/track-relinking-guide/',
            '(http://en.wikipedia.org/wiki/Universal_Product_Code)',
            '(http://en.wikipedia.org/wiki/International_Standard_Recording_Code)',
            '/documentation/web-api/#spotify-uris-and-ids'
        ]
        for s in tmp:
            sss = sss.replace(s, '')
        return sss

    def simplify_dict(self, data):
        """
        Recursively simplify the dictionary by removing specific keys.

        :param data: The input dictionary to be simplified.
        :return: A simplified dictionary with specified keys removed.
        """
        keys_to_remove = ['example', 'nullable', 'x-spotify-docs-type', 'required', 'default', 'minimum', 'maximum', 'examples']

        if isinstance(data, dict):
            results = {}
            for k, v in data.items():
                if k in keys_to_remove:
                    continue
                if k == 'description':
                    results[k] = normalize(self.simplify_dict(v))
                else:
                    results[k] = self.simplify_dict(v)
            return results
        elif isinstance(data, list):
            return [self.simplify_dict(item) for item in data]
        else:
            return data

    def get_parameters(self, doc) -> str:
        if len(doc['parameter']) == 0:
            parameter = 'No extra parameter, just replace the `{variable}` in the url path with actual value.'
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
        return parameter

    def formulate(self, tool, is_description=True, is_parameters=True, is_request_type=True,
                  execution_results_type='responses', is_request_body=True):
        # print(tool)
        doc = self.get_doc_by_name(tool)
        text_doc = ["""API url: """+doc['url']]
        if is_request_type and 'method' in doc:
            method = """### Request type\n""" + doc['method']
            text_doc.append(method)
        if is_description and 'description' in doc:
            description = """### Description\n""" + self.normalize(doc['description'])
            text_doc.append(description)
        if is_parameters:
            parameters = '### Parameter\n' + self.get_parameters(doc)
            text_doc.append(parameters)
        if execution_results_type is not None and execution_results_type in doc:
            if 'yaml' in execution_results_type:
                response = '### Execution result specification\n' + str(doc[execution_results_type])
            else:
                response = '### Execution result specification\n' + json.dumps(doc[execution_results_type], indent=4)
            text_doc.append(response)
        if is_request_body and 'requestBody' in doc:
            requestBody = '### Request body\n' + json.dumps(doc['requestBody'], indent=4)
            text_doc.append(requestBody)
        text_doc = '\n'.join(text_doc)
        return text_doc

    # def simplify_response_template(self,data):
    #     results = {}
    #     if 'required' in data and 'properties' in data:
    #         results['properties'] = {}
    #         for k, v in data['properties'].items():
    #             if k in data['required']:
    #                 results['properties'][k]=v
    #
    #     for k, v in data.items():
    #         if k == 'properties':
    #             if 'properties' not in results:
    #                 results['properties'] = {}
    #             for t1, t2 in v.items():
    #                 results['properties'][t1] = self.simplify_response_template(copy.deepcopy(t2))
    #         elif k in ['example', 'nullable', 'x-spotify-docs-type', 'required']:
    #             continue
    #         elif k == 'description':
    #             results[k] = self.normalize(v)
    #         else:
    #             results[k] = v
    #     return results
    #
    # def simplify_response_template1(self, data):
    #     results = {}
    #     if 'required' in data and 'properties' in data:
    #         results['properties'] = {}
    #         # 仅处理'required'列表中的属性
    #         for k in data['required']:
    #             if k in data['properties']:
    #                 results['properties'][k] = data['properties'][k]
    #
    #     # 遍历并处理其他键值对
    #     for k, v in data.items():
    #         if k == 'properties':
    #             # 仅当'required'不存在或属性在'required'中时，递归处理
    #             if 'required' not in data:
    #                 required_properties = v.keys()
    #             else:
    #                 required_properties = data['required']
    #
    #             for t1, t2 in v.items():
    #                 if t1 in required_properties:
    #                     if 'properties' not in results:
    #                         results['properties'] = {}
    #                     results['properties'][t1] = self.simplify_response_template1(t2)
    #         elif k in ['example', 'nullable', 'x-spotify-docs-type', 'required']:
    #             continue
    #         elif k == 'description':
    #             results[k] = self.normalize(v)  # 假设normalize方法已定义
    #         else:
    #             results[k] = v
    #
    #     return results


class TMDBTools(Tools):

    def __init__(self, system, oas_spec):
        super(TMDBTools, self).__init__(system=system, oas_spec=oas_spec)
        access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
        self.header = {
            'Authorization': f'Bearer {access_token}'
        }

    def get_instruction(self, query, tools, LM_function=False,
                        is_description=True,
                        is_parameters=True,
                        is_request_type=True,
                        execution_results_type='responses',
                        is_request_body=True
                        ):
        docs = [f'{i}. ' + self.formulate(tool,is_description=is_description,
                                          is_parameters=is_parameters,
                                          is_request_body=is_request_body,
                                          execution_results_type=execution_results_type,
                                          is_request_type=is_request_type)
                for i, tool in enumerate(tools, start=1)]
        if LM_function == False:
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
response = requests.get(url, headers=headers, params=params) # The variable `headers` has been defined, please JUST USE it.
```
If the API path contains "{{}}", it means that it is a variable and you should replace it with the appropriate value. For example, if the path is "/users/{{user_id}}/tweets", you should replace "{{user_id}}" with the user id. "{{" and "}}" cannot appear in the url.

Based on provided APIs, please write python code to call API and solve it. Try to write correct Python Code and avoid grammar error, e.g. `variable is not defined`. 
You need to provide Python code that can be executed directly; any explanations should be marked as Python comments. Note: DO NOT make up value by yourself, please use the given APIs to acquire information (e.g., person id or movie id). 

Query: {query}
Your output:
```python
[Please write the code]
```""".format(system=self.system, header=json.dumps(self.header, indent=4), query=query, docs='\n\n'.join(docs))
        else:
            system_instruction = """In this task, you should answer the user's query by using the provided OpenAPI API.
Specifically, you should write Python code to call the appreciate APIs to obtain the required information. Then, you are provided large language models (LLMs) to help you process the text data, e.g., text summarization and sentiment analysis. You can customize the LLMs' function using specific instructions."""

            openapi = """# OpenAPIs List
Here are the OpenAPI specifications of given APIs, including their HTTP URL, description, arguments, and execution results.
{docs}

You should use the following HTTP header to call the API:
```python
headers = {header}
```
Note: I will give you 'headers', do not make one, just reference it in your code. Here is an example to request the API:
```python
import requests
url = "<The API url selected from the above APIs>"
params = "<The params dict>"
response = requests.get(URL, headers=headers, params=params) # The variable `headers` has been defined, please JUST USE it.
```
If the API path contains "{{}}", it means that it is a variable and you should replace it with the appropriate value. For example, if the path is "/users/{{user_id}}/tweets", you should replace "{{user_id}}" with the user id. "{{" and "}}" cannot appear in the URL.

Based on the provided APIs, please write Python code to call the API and solve it. Try to write correct Python Code and avoid grammar errors, e.g. `variable is not defined`.
""".format(header=json.dumps(self.header, indent=4), docs='\n\n'.join(docs))

            LLM_api = """# Customize Your Own Function using `LLMs`
To process the text information, you can instruct the large language models (LLMs) by writing specific instructions. Specifically, you should instruct the large language models (LLMs) by writing specific instructions. You can directly access the LLMs via a built-in function named `LLMs`. It is a black-box function I have pre-defined in the Python library. Please directly use this function in your code 
The details of the function `LLMs` are as follows.

## Signature
def LLMs(instruction: str, input_data: str) -> str

## Parameters
- **instruction** (`str`): An instruction to the language model specifying how to process the input text. This should be a clear command and must specify the format of the output for subsequent string parsing. Here are some examples: 
    (1) Summarize the following text and just output the string type
    (2) Analysis of the sentiment (positive or negative) of this review. Only output `1` if positive, otherwise `0` for negative.
    (3) read the input text and extract the main protagonist. Give only the names of people, separated by commas
- **input_data** (`str`): The text to be processed. This can be any string where language processing is applicable, including documents, articles, or sentences. 

## Return: 
- the return type of this function is `str`. The return value can be further transformed into bool, int or split into a list according to the customized instruction.

## Usages:
- Example 1: Customize the document summarization function to compress a long article less than 100 words.
```python
def summarize_by_LLMs(article: str)-> str:
    \"\"\"
    Summarize the input text.
    
    :param input_text: Text to be summarized.
    :return: A summary of the input text.
    \"\"\"
    
    # First: design the `instruction` to enable the LLMs to summarize your article
    instruction = 'Please summarize the following text with less than 100 words.'
    summary = LLMs(instruction = instruction, input_text = article)
    
    # Second: truncate it into 100 words.
    summary = summary.split(' ')[:100]
    summary = ' '.join(summary)
    
    return summary
```
In this example, the processed text would contain a concise summary highlighting the key points of the research findings and their implications.

- Example 2: Customize a function that can analyze any given movie overview and count the number of main protagonists.
```python
def count_protagonist(movies_overview: str) -> int:
    \"\"\"
    count the number of the main protagonist
    
    :param input_text: Text involving many protagonist
    :return: A number of involved protagonist
    \"\"\"
    
    # First: design the `instruction` to enable the LLMs to extract the names of the protagonist
    instruction = "Please extract the main protagonist. Give only the names of people, separated by commas"
    names_string_sequence = LLMs(instruction = instruction, input_text = movies_overview)
    
    # Second: split the extract sequence of names and count the number
    number = len(names_string_sequence.split(","))
    
    return number
```
In this example, the built-in operation `LLMs` extracts the names of the main protagonist in the input text with each name separated by commas.

**Note that**: Your designed instruction must specify the clear output format to control the generated content of LLMs. The clearer your instructions are, the more formatted the content generated by the language model will be, which will make it easier to parse later.
"""

            user_query= f"""# Your Output
Starting below, you need to provide Python code that can be executed directly; any explanations should be marked as Python comments. Note: DO NOT make up value by yourself, please use the given APIs to acquire information (e.g., person ID or movie ID). 

Query: {query}
Your output:
```python
[Please write the code]
```"""

            instruction = [system_instruction, openapi, LLM_api, user_query]
            instruction = '\n'.join(instruction)

        return instruction

    def get_tools_instruction(self,tools):
        docs = [self.formulate(tool) for i, tool in enumerate(tools, start=1)]
        return docs

class SpotifyTools(Tools):

    def __init__(self, system, oas_spec):
        super(SpotifyTools, self).__init__(system=system, oas_spec=oas_spec)
        config = yaml.load(open('/Users/shizhl/Paper2024/ProTool/dataset/spotify_config.yaml', 'r'), Loader=yaml.FullLoader)
        os.environ['SPOTIPY_CLIENT_ID'] = config['spotipy_client_id']
        os.environ['SPOTIPY_CLIENT_SECRET'] = config['spotipy_client_secret']
        os.environ['SPOTIPY_REDIRECT_URI'] = config['spotipy_redirect_uri']

        with open("/Users/shizhl/Paper2024/ProTool/specs/spotify_oas.json") as f:
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
    if type(sss) != str:
        return sss
    tmp = [
        '(/documentation/web-api/#spotify-uris-and-ids)',
        '(https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)',
        '(http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)',
        '(https://www.spotify.com/se/account/overview/)',
        '<br/>',
        '<br>',
        '\n',
        '/documentation/general/guides/track-relinking-guide/',
        '(http://en.wikipedia.org/wiki/Universal_Product_Code)',
        '(http://en.wikipedia.org/wiki/International_Standard_Recording_Code)',
        '/documentation/web-api/#spotify-uris-and-ids'
    ]
    for s in tmp:
        sss = sss.replace(s, '')
    return sss


def simplify_response_template(data):
    if 'required' in data and 'properties' in data:
        for k, v in data['properties'].items():
            if k not in data['required']:
                data.pop(k)
    if 'type' in data and data['type'] == 'object' and 'properties' in data:
        for k, v in data['properties'].items():
            data['properties'][k] = simplify_response_template(v)
    else:
        for k, v in data.items():
            if k in ['example', 'nullable', 'x-spotify-docs-type']:
                data.pop(k)
            if k == 'description':
                data[k] = normalize(v)
    return data

# def simplify_response_template1(data):
#     results={}
#     if 'required' in data and 'properties' in data:
#         results['properties']={}
#         for k, v in data['properties'].items():
#             if k in data['required']:
#                 results['properties'][k]=v
#
#     for k,v in data.items():
#         if k=='external_urls':
#             print('')
#         if k=='properties':
#             if 'properties' not in results:
#                 results['properties'] = {}
#             for t1,t2 in v.items():
#                 results['properties'][t1]=simplify_response_template1(copy.deepcopy(t2))
#         elif k in ['example', 'nullable', 'x-spotify-docs-type','required']:
#             continue
#         elif k == 'description':
#             results[k] = normalize(v)
#         else:
#             results[k]=v
#     return results
#
#
# # a={}
# # a['type']='object'
# # a['properties']={'href': {'description': 'A link to the Web API endpoint returning the full result of the request\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=0&limit=20\n', 'type': 'string'}, 'limit': {'description': 'The maximum number of items in the response (as set in the query or by default).\n', 'example': '20', 'type': 'integer'}, 'next': {'description': 'URL to the next page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'offset': {'description': 'The offset of the items returned (as set in the query or by default)\n', 'example': '0', 'type': 'integer'}, 'previous': {'description': 'URL to the previous page of items. ( `null` if none)\n', 'example': 'https://api.spotify.com/v1/me/shows?offset=1&limit=1', 'nullable': 'true', 'type': 'string'}, 'total': {'description': 'The total number of items available to return.\n', 'example': '4', 'type': 'integer'}, 'items': {'items': {'properties': {'artists': {'description': 'The artists who performed the track. Each artist object includes a link in `href` to more detailed information about the artist.', 'items': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the artist.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}, 'name': {'description': 'The name of the artist.\n', 'type': 'string'}, 'type': {'description': 'The object type.\n', 'enum': ['artist'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedArtistObject'}, 'type': 'array'}, 'available_markets': {'description': 'A list of the countries in which the track can be played, identified by their [ISO 3166-1 alpha-2](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code.\n', 'items': {'type': 'string'}, 'type': 'array'}, 'disc_number': {'description': 'The disc number (usually `1` unless the album consists of more than one disc).', 'type': 'integer'}, 'duration_ms': {'description': 'The track length in milliseconds.', 'type': 'integer'}, 'explicit': {'description': 'Whether or not the track has explicit lyrics ( `true` = yes it does; `false` = no it does not OR unknown).', 'type': 'boolean'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the track.', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}, 'is_local': {'description': 'Whether or not the track is from a local file.\n', 'type': 'boolean'}, 'is_playable': {'description': 'Part of the response when [Track Relinking](/documentation/general/guides/track-relinking-guide/) is applied. If `true`, the track is playable in the given market. Otherwise `false`.\n', 'type': 'boolean'}, 'linked_from': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the track.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}, 'type': {'description': 'The object type: "track".\n', 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'name': {'description': 'The name of the track.', 'type': 'string'}, 'preview_url': {'description': 'A URL to a 30 second preview (MP3 format) of the track.\n', 'type': 'string', 'x-spotify-policy-list': [{}]}, 'restrictions': {'properties': {'reason': {'description': "The reason for the restriction. Supported values:\n- `market` - The content item is not available in the given market.\n- `product` - The content item is not available for the user's subscription type.\n- `explicit` - The content item is explicit and the user's account is set to not play explicit content.\n\nAdditional reasons may be added in the future.\n**Note**: If you use this field, make sure that your application safely handles unknown values.\n", 'type': 'string'}}, 'required': [], 'type': 'object'}, 'track_number': {'description': 'The number of the track. If an album has several discs, the track number is the number on the specified disc.\n', 'type': 'integer'}, 'type': {'description': 'The object type: "track".\n', 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedTrackObject'}, 'type': 'array'}}
# a={'type': 'object', 'properties': {'items': {'properties': {'artists': {'description': 'The artists who performed the track. Each artist object includes a link in `href` to more detailed information about the artist.', 'items': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the artist.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}, 'name': {'description': 'The name of the artist.\n', 'type': 'string'}, 'type': {'description': 'The object type.\n', 'enum': ['artist'], 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the artist.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedArtistObject'}, 'type': 'array'}, 'available_markets': {'description': 'A list of the countries in which the track can be played, identified by their [ISO 3166-1 alpha-2](http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) code.\n', 'items': {'type': 'string'}, 'type': 'array'}, 'disc_number': {'description': 'The disc number (usually `1` unless the album consists of more than one disc).', 'type': 'integer'}, 'duration_ms': {'description': 'The track length in milliseconds.', 'type': 'integer'}, 'explicit': {'description': 'Whether or not the track has explicit lyrics ( `true` = yes it does; `false` = no it does not OR unknown).', 'type': 'boolean'}, 'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the track.', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}, 'is_local': {'description': 'Whether or not the track is from a local file.\n', 'type': 'boolean'}, 'is_playable': {'description': 'Part of the response when [Track Relinking](/documentation/general/guides/track-relinking-guide/) is applied. If `true`, the track is playable in the given market. Otherwise `false`.\n', 'type': 'boolean'}, 'linked_from': {'properties': {'external_urls': {'properties': {'spotify': {'description': 'The [Spotify URL](/documentation/web-api/#spotify-uris-and-ids) for the object.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'href': {'description': 'A link to the Web API endpoint providing full details of the track.\n', 'type': 'string'}, 'id': {'description': 'The [Spotify ID](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}, 'type': {'description': 'The object type: "track".\n', 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}}, 'required': [], 'type': 'object'}, 'name': {'description': 'The name of the track.', 'type': 'string'}, 'preview_url': {'description': 'A URL to a 30 second preview (MP3 format) of the track.\n', 'type': 'string', 'x-spotify-policy-list': [{}]}, 'restrictions': {'properties': {'reason': {'description': "The reason for the restriction. Supported values:\n- `market` - The content item is not available in the given market.\n- `product` - The content item is not available for the user's subscription type.\n- `explicit` - The content item is explicit and the user's account is set to not play explicit content.\n\nAdditional reasons may be added in the future.\n**Note**: If you use this field, make sure that your application safely handles unknown values.\n", 'type': 'string'}}, 'required': [], 'type': 'object'}, 'track_number': {'description': 'The number of the track. If an album has several discs, the track number is the number on the specified disc.\n', 'type': 'integer'}, 'type': {'description': 'The object type: "track".\n', 'type': 'string'}, 'uri': {'description': 'The [Spotify URI](/documentation/web-api/#spotify-uris-and-ids) for the track.\n', 'type': 'string'}}, 'type': 'object', 'x-spotify-docs-type': 'SimplifiedTrackObject'}, 'type': 'array'}}
# print(json.dumps(a))
# b=simplify_response_template1(a)['properties']
# print(json.dumps(b))


class LLMTools:
    document = {
        "vague_match_function": """def vague_match_function(source: str, target: str) -> bool

### Description
This function determines whether two input strings, 'source' and 'target', share the same semantic meaning. It analyzes the underlying context or concept conveyed by each string and returns `True` if they are semantically similar or related in meaning, and `False` otherwise.

### Parameters
- source (str): The first string for comparison.
- target (str): The second string for comparison.

### Returns
- bool: Returns `True` if the 'source' and 'target' share similar semantic meanings. Returns `False` otherwise.

### Usage
**Example 1: Understanding semantically similar terms.**
```python
results=vague_match_tools('Director', 'Directing') # True
```
In this example, 'Director' and 'Directing' are considered semantically similar because they pertain to the same underlying concept or role.

**Example 2: Differentiating semantically distinct terms.**
```python
result = vague_match_tools('Actor', 'Director') # False
```
In this example, 'Actor' and 'Director' are considered semantically different as they refer to distinct roles within the context of film or theater.
""",

        'text_process_tool': """def text_process_tool(instruction, input_text) -> string
## Description
This function is a black-box function which is used to calling a large language model to process the text data.  You can customize the input 'instruction' to control the language model to process the input `text`, e.g., 'Please summarize the long movie review' or 'polish the input article'.
## Parameters:
- instruction: the input instruction used to customize the function of the langauge model (type: string)
- input_text: the input text need to be processed. (type: string)
# Usage
Example 1: The 'Director' and 'Directing' share the same meaning, the variable `x` is True.
Input: ```python
input_text="In a landmark achievement, an international coalition of scientists unveiled a revolutionary space engine that drastically reduces travel time to Mars. Utilizing quantum entanglement principles, this innovation promises to transform interplanetary travel, fostering unprecedented opportunities for colonization and deep space exploration. The collaborative effort symbolizes a new era for humanity."
instruction='Please summarize the following document'
text_process_tool(instruction input_text) 
```
Output:
```
"Revolutionary space engine, quantum principles, Mars, collaboration, new exploration era."
```""",

        "generic_instructional_function": """def generic_instructional_function(instruction: str, input_text: str) -> str:

### Description
This function is a utility designed to leverage a language model for processing and transforming text data based on customized instructions. This function abstracts the complexities of the language model interaction, allowing users to apply a variety of text manipulations or analyses effortlessly. It returns the processed text.

### Parameters
- **instruction** (`str`): An instruction to the language model specifying how to process the input text. This should be a clear, concise command, such as 'Summarize the following text' or 'Improve the readability of this article'.
- **input_text** (`str`): The text to be processed. This can be any string where language processing is applicable, including documents, articles, or sentences.

### Returns
- **processed_text** (`str`): The processed text (`str`) according to the given instruction.

### Usage Examples
**Example 1: Document Summarization**
```python
instruction = 'Please summarize the following text.'
input_text = "An international team of researchers has developed a groundbreaking method for water desalination, potentially solving global water scarcity issues. Their innovative approach, which utilizes solar energy efficiently, offers a sustainable and cost-effective solution to accessing clean water in arid regions."
output_text = generic_instructional_function(instruction, input_text)
```
In this example, the processed text would contain a concise summary highlighting the key points of the research findings and their implications.

**Example 2: Date Comparison**
```python
instruction = 'Determine which of these two dates is earlier and return "0" for the first date being earlier or "1" for the second.'
input_text = "July 20, 1969 and April 12, 1961"
output_text = generic_instructional_function(instruction, input_text)
```
In this example, the processed text would be "1", indicating the second date is earlier.
""",

        "personalized_selection_from_list": """def personalized_selection_from_list(instruction: str, input_list: list[str]) -> int:
        
### Description
The `personalized_selection_from_list` function analyzes an input list of strings and returns the index of the single best-matching element based on a specific instruction. This function facilitates a targeted selection process, identifying one element from the list that best aligns with the given criteria or preferences articulated in the instruction.

### Parameters
- **instruction** (`str`): A directive that specifies the criteria or logic for identifying the best-matching string from the input list. This instruction should clearly articulate the conditions or attributes that define the optimal selection.
- **input_list** (`list[str]`): The list of string elements to be evaluated. The function assesses each element against the criteria outlined in the instruction to determine the most suitable match.

### Returns
- **index** (`int`): The index of the best-matching element within the input list. This index corresponds to the position of the element that most closely fulfills the criteria specified in the instruction.

### Usage Example
**Example 1: Movie Genre Selection**
Assume you have a list of movie titles and you want to find the index of the title that best matches a specific genre:

```python
instruction = 'Find the index of the title most closely associated with the sci-fi genre.'
input_list = ['The Shawshank Redemption', 'Blade Runner', 'The Godfather', 'Inception']
selected_item_index = personalized_selection_from_list(instruction = instruction, input_list = input_list) # 1
```
This example assumes that the logic implemented by personalized_selection_from_list determines 'Blade Runner' to be the most relevant title to the 'sci-fi' genre based on the instruction. Consequently, the function returns 1, which is the index of 'Blade Runner' in the input_list.
"""

    }

    # Output: ```
    # "Revolutionary space engine, quantum principles, Mars, collaboration, new exploration era."
    # ```
    #  This function is a black-box function which is used to calling a language model to process the input text data.  You can customize the input 'instruction' to control the language model to process the input `text`, e.g., 'Please summarize the long movie review' or 'polish the input article'.
    # """### Usage
    # - Example 1: The customize the summarization instruction to instruct the language model.
    # ```python
    # instruction='Please summarize the following document.'
    # input_text="In a landmark achievement, an international coalition of scientists unveiled a revolutionary space engine that drastically reduces travel time to Mars. Utilizing quantum entanglement principles, this innovation promises to transform interplanetary travel, fostering unprecedented opportunities for colonization and deep space exploration. The collaborative effort symbolizes a new era for humanity."
    # generic_instructional_function(instruction input_text)
    # ```
    # - Example 2: compare which date is earlier, the first or the second.
    # Input: ```python
    # instruction = 'compare the two dates and only output "0" if the first is earlier, otherwise output "1".'
    # input_text="March 11, 2024 and January 8, 2025"
    # generic_instructional_function(instruction input_text)
    # ```
    # Output: ```
    # "0"
    # ```"""

    def __init__(self, model_name='gpt-3.5-turbo'):
        self.model_name = model_name
        self.token = []

    @staticmethod
    def vague_match_function(source, target):
        instruction = f"""Here are two snippets. If the two snippets share the same meaning, just output 'TRUE', otherwise output 'FALSE'. 
Here are some examples:
Director, Directing -> TRUE
Director, Actor -> FALSE
{source}, {target} -> """

        res = get_from_openai(model_name='gpt-3.5-turbo-instruct', prompt=instruction, temp=0)['content']
        if res.lower() == 'true':
            return True
        else:
            return False

    @staticmethod
    def generic_instructional_function(instruction, input_data):
        prompt = instruction + '\n' + input_data
        res = get_from_openai(model_name='gpt-3.5-turbo-instruct', prompt=prompt, temp=0)['content']
        return res

    @staticmethod
    def text_process_tool(instruction, input_data):
        prompt = instruction + '\n' + input_data
        res = get_from_openai(model_name='gpt-3.5-turbo-instruct', prompt=prompt, temp=0)['content']
        return res

    @staticmethod
    def personalized_selection_from_list(instruction, input_list):
        """
        根据输入对instruction 进行个性化对筛选，从列表中筛选出一个最合适的
        """
        prompt = """{instruction}
        
Now please choice an element from the following list, and only output the correspond numeric index identifier, e.g., 1, 2 or 3.

{candidate}

Your output: """.format(instruction=instruction, candidate='\n'.join([f'{i}. {e}' for i, e in enumerate(input_list)]))

        res = get_from_openai(model_name='gpt-3.5-turbo-instruct', prompt=prompt, temp=0)['content']
        return res

    # reasoning capability is out of the code
    # semantic capability is out of the code
    # answer gathering
    #


class APIManager:

    def __init__(self, model_name='gpt-3.5-turbo', toolset: Union[Tools, TMDBTools, SpotifyTools] = None):
        self.model_name = model_name
        self.token = []
        self.toolset = toolset

    def generate(self, query, tool_list):
        tool_doc = []
        for tool in tool_list:
            doc = self.toolset.formulate(tool, execution_results_type=False,
                                         is_request_body=False, is_request_type=True)
            tool_doc.append(doc)

        tool_doc = '\n\n'.join([f'{i}. {e}' for i, e in enumerate(tool_doc, 1)])

        system = """In this task, you are a software engineer and you are provided a list of external APIs. You need to develop a class named `Solution` that contains several static functions. These static functions serve as encapsulations for the selected APIs.

More specifically, you need to:

1. Select the appropriate APIs from the list to address the user's question. For each selected API, please create a static method in the Solution class, including the signature and implement details.
2. You should select all APIs that may be involved since in the subsequent stage we can only use your currently selected APIs to solve the question.
3. Add comments above each function to describe its purpose, inputs, and outputs. You should also add the url of the used APIs for each function.

Here is a template of the generated programming framework:
```python
class Solution:

    @staticmethod
    def func1(param1: [type of param1], param2: [type of param2]) -> [type of output]:
        \"\"\"
        Purpose:
        [The description of this function]
        
        Inputs:
        - param1: [the description of param1]
        - param2: [the description of param2]

        Outputs:
        [The description of the return value]
        
        Which API to use:
        [only give the url of the selected API]
        \"\"\"
        # [implement the function]
```
"""

        user_instruction = f"""Here is the user query: {query}. 

Please first select appropriate APIs from the following APIs list. Then, write a Python class named `Solution` to guide another model which APIs to use and how these APIs to use for solving the query.  
{tool_doc}

Note: you should only give the Python code (enclosed with ```python [Your code]```. 

Your output:
```python
class Solution:
    ...
```"""
        res = get_from_openai(model_name=self.model_name,
                              messages=[{'role': 'user', 'content': system},
                                        {'role': 'user', 'content': user_instruction}],
                              usage=True)
        # print(user_instruction)
        # print(res['usage'])
        return res['content']

import math

def multi_process_func(ranks, func, data, model):
    pools = multiprocessing.Pool(processes=len(ranks))
    length = math.ceil(len(data) // len(ranks) )
    collects = []
    for ids, rank in enumerate(ranks):
        collect = data[ids * length:(ids + 1) * length]
        collects.append(pools.apply_async(func, (rank, collect, model)))
    pools.close()
    pools.join()
    results = []
    for rank, result in zip(ranks, collects):
        r, res = result.get()
        assert r == rank
        results.extend(res)
    return results

def func(rank, data, model_name):
    toolsets = TMDBTools(
        system='Here are some APIs used to access the TMDB platform. You need to answer the question by writing python code to call appreciate APIs and `print` the final answer. The API can be accessed via HTTP request. ',
        oas_spec='../dataset/tmdb_api_spec.json',
    )
    model = APIManager(model_name='gpt-3.5-turbo', toolset=toolsets)
    negative = toolsets.get_tool_list()
    results=[]

    for line in tqdm(data):
        # print(line)
        tools = copy.deepcopy(line['solution'])
        while len(tools) < 30:
            tool = negative[random.randint(0, 10000) % len(negative)]
            if tool not in tools:
                tools.append(tool)
        line['api_list'] = tools

        # try:
        res = model.generate(query=line['query'], tool_list=tools)
        # encoded_docs = encoder.encode(instruction)
        # print(len(encoded_docs))
        line['output']=res
        line['match']=len([e for e in line['solution'] if e.split(' ')[-1].strip() in res]),len(line['solution'])

        # print('-' * 50)
        # print(line['solution'])
        # print(res)

        results.append(line)

    return rank, results


if __name__ == '__main__':
    data = load_data('/Users/shizhl/Paper2024/ProTool/dataset/tmdb.json')
    results = func(0,data,'gpt-3.5-turbo')
    # results = multi_process_func(ranks=list(range(10)), func=func, data=data, model='gpt-3.5-turbo')
    # for line in results:
    #     print(line['match'])
