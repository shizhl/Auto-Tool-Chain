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
import math
import tiktoken
from model.instruction import *



encoder = tiktoken.encoding_for_model('gpt-3.5-turbo')

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


def simplify_spec(data):
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
            # if k == 'description':
            #     results[k] = normalize(simplify_spec(v))
            # else:
            results[k] = simplify_spec(v)
        return results
    elif isinstance(data, list):
        return [simplify_spec(item) for item in data]
    else:
        if type(data) == str:
            return normalize(data)
        return data


def normalize(sss):
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

    for i in range(10):
        sss = sss.replace(f'[{i}].', '')
        sss = sss.replace(f'[{i}]', '')
    return sss.strip()


class Base:

    def __init__(self, model_name='gpt-3.5-turbo'):
        self.model_name = model_name
        self.token = []

    def normalize(self, sss):
        return sss

    def generate(self, messages):
        res = get_from_openai(model_name=self.model_name, messages=messages, usage=True)
        self.token.append(res['usage'])
        return self.normalize(res['content']), res['usage']

    def get_token(self):
        tmp = []
        for line in self.token:
            tmp = [e1 + e2 for e1, e2 in zip(tmp, line)]
        return tmp


class Tool:

    def __init__(self, spec: dict = None):
        if spec is None:
            self.method, self.url, self.name = 'None', 'None', 'None'
            self.description = 'None'
            self.parameter = []
            self.responses = {}
            self.requestBody = 'None'
            return

        self.name = spec['name']
        self.method = spec['method']
        self.url = spec['url']
        self.description = spec['description']
        self.parameter = spec['parameters'] if 'parameters' in spec else []
        self.responses = {}

        if 'requestBody' in spec and spec['requestBody'] != None:
            self.requestBody = simplify_spec(spec['requestBody']['content']['application/json']["schema"]['properties'])
        else:
            self.requestBody = 'This API do not need the request body when calling.'

        if 'responses' in spec and spec['responses'] is not None and 'content' in spec['responses']:
            self.responses['responses'] = simplify_spec(spec['responses']['content']['application/json']["schema"]['properties'])
            self.responses['responses'] = json.dumps(self.responses['responses'], indent=4)
        else:
            self.responses['responses'] = 'This API has no return value.'

        if '_responses_json' in spec and spec['_responses_json'] is not None:
            self.responses['_responses_json'] = json.dumps(spec['_responses_json'], indent=4) if type(spec['_responses_json']) == dict else spec['_responses_json']
        else:
            self.responses['_responses_json'] = None

        if '_responses_yaml' in spec and spec['_responses_yaml'] is not None:
            self.responses['_responses_yaml'] = spec['_responses_yaml']
        else:
            self.responses['_response_yaml'] = None

    def update_response(self, response_format, response_example):
        if response_format == '_response_yaml':
            self.responses[response_format] = response_example
        else:
            self.responses[response_format] = response_example if type(response_example) == str else json.dumps(response_example, indent=4)

    def get_parameters(self) -> str:
        if len(self.parameter) == 0:
            parameter = 'No extra parameter, just replace the `{variable}` in the url path with actual value.'
        else:
            parameter = []
            for p in self.parameter:
                # if p['in'] != 'query':
                #     continue
                tmp = "- " + p['name'] + ": " + normalize(p['description'])
                if 'schema' in p and 'type' in p['schema']:
                    tmp += " (type: " + p['schema']['type'] + ")"
                parameter.append(tmp)
            parameter = '\n'.join(parameter)
            if '{' in self.url:
                parameter += '\nThe `{variable}` in the url path should also be replaced with actual value.'
        return parameter

    def formulate(self, is_description=True, is_parameters=True, is_request_type=True, is_url=True,
                  execution_results_type=None, is_request_body=True):
        text_doc = ["""API name: """ + self.name]
        if is_url:
            text_doc.append('### API url\n' + self.url)
        if is_request_type:
            method = """### Request type\n""" + self.method
            text_doc.append(method)
        if is_description:
            description = """### Description\n""" + normalize(self.description)
            text_doc.append(description)
        if is_parameters:
            parameters = '### Parameter\n' + self.get_parameters()
            text_doc.append(parameters)
        if execution_results_type is not None and execution_results_type in self.responses:
            response = '### Execution result specification\n' + str(self.responses[execution_results_type])
            text_doc.append(response)
        if is_request_body:
            requestBody = '### Request body\n' + json.dumps(self.requestBody, indent=4)
            text_doc.append(requestBody)
        text_doc = '\n'.join(text_doc)
        return text_doc


class Tools:

    def __init__(self, system, oas_spec):
        self.system = system
        api_spec = json.load(open(oas_spec))
        self.endpoint = {e['name']: Tool(e) for e in api_spec['endpoints']}
        self.host = api_spec['servers'][0]['url']

    def match(self, name):
        return name

    def get_tool_list(self):
        tmp = [k for k, v in self.endpoint.items()]
        return tmp

    def formulate(self, tool, is_description=True, is_parameters=True, is_request_type=True, is_url=True,
                  execution_results_type=None, is_request_body=True):
        # print(tool)
        tool = self.match(tool)
        doc = self.endpoint[tool].formulate(is_description=is_description,
                                            is_parameters=is_parameters, is_url=is_url,
                                            execution_results_type=execution_results_type,
                                            is_request_type=is_request_type, is_request_body=is_request_body)
        return doc


    def attribute(self,error):
        instruction = """"""

class TMDBTools(Tools):

    def __init__(self, system, oas_spec):
        super(TMDBTools, self).__init__(system=system, oas_spec=oas_spec)
        self.headers = {
            'Authorization': f'Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
        }

    def get_instruction(self, query, tools, LM_function=False,
                        is_description=True,
                        is_parameters=True,
                        is_request_type=True,
                        execution_results_type='responses',
                        is_request_body=True,
                        is_url=True):
        docs = [f'{i}. ' + self.formulate(tool, is_description=is_description,
                                          is_parameters=is_parameters,
                                          is_request_body=is_request_body, is_url=is_url,
                                          execution_results_type=execution_results_type,
                                          is_request_type=is_request_type)
                for i, tool in enumerate(tools, start=1)]
#         instruction = """Here are some APIs used to access the TMDB platform. You need to answer the question by writing python code to call appreciate APIs and `print` the final answer. The API can be accessed via HTTP request.
#
# Here are the OpenAPI Specification of given APIs, including their http url, description, arguments and execution results.
# {docs}
#
# You should use the following Http headers to call the API:
# ```python
# headers = {headers}
# ```
# Note: I will give you the `headers` used to request the http server. Do not make up one in your code. Here is an example to request the API:
# ```python
# import requests
# url = "<The API url selected from the above APIs>"
# params = "<The params dict>"
# response = requests.get(url, headers=headers, params=params) # The variable `headers` has been defined, please JUST USE it.
# ```
# If the API path contains "{{}}", it means that it is a variable and you should replace it with the appropriate value. For example, if the path is "/users/{{user_id}}/tweets", you should replace "{{user_id}}" with the user id. "{{" and "}}" cannot appear in the url.
#
# Based on provided APIs, please write python code to call API and solve it. Try to write correct Python Code and avoid grammar error, e.g. `variable is not defined`.  You need to provide Python code that can be executed directly; Please add the name of the used APIs in Python comments for the attributable consideration.
#
# **Note**: any information, e.g., person id or movie id, you need to obtain it by calling appropriate APIs. DO NOT make up value by yourself!
#
# Query: {query}
# Your output:
# ```python
# headers = {headers}
# Complete the python code...
# ```""".format(headers=json.dumps(self.headers, indent=4), query=query, docs='\n\n'.join(docs))
#         user_query = f"""# Your Output
# Starting below, you need to provide Python code that can be executed directly; any explanations should be marked as Python comments. Note: DO NOT make up value by yourself, please use the given APIs to acquire information (e.g., person ID or movie ID).
#
# Query: {query}
# Your output:
# ```python
# [Please write the code]
# ```"""
#
#         instruction = [instruction, user_query]
#         instruction = '\n'.join(instruction)


        instruction = GPT_TMDB_INSTRUCTION.format(system=self.system,headers=json.dumps(self.headers, indent=4), query=query, docs='\n\n'.join(docs))
        return instruction


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
        self.headers = {
            'Authorization': f'Bearer {access_token}'
        }
        # access_token = "BQDFeUrmM11KEebVbtIoHHCH4QIyI36UUSq67xkOI3ddGMAhK_0u7UZwNWfha1Evbb6hLYBx3ijPbfiyb46I8STJc2ctG5Wab45lPjCFJvMuMKaAuqAhuSDr8FqLDxYdQXI9GcKffAnp5_PPCMYSezTDWlFR8CKyeU0fbNS0c2G2Bd7bDkrnt5EphM6ZFXdHdae7VFe8_dPblBX6ZEJu5BkcooA6NJ2ppvLpqT4hkEeyWX5q1SCrJN_dhnZv3HXpJ6_JSYKA_XcRTPsDVAmPbcDaLfb0-Qgdn8CdA21Jobgkw6IWUwKPk-kIWzy0rKevKcIULpWKhNHNd0hvaHsn_mh9"
        # self.headers ={
        #         'Authorization': f'Bearer {access_token}'
        # }
    def get_instruction(self,  query, tools, LM_function=False,
                        is_description=True,
                        is_parameters=True,
                        is_request_type=True,
                        execution_results_type='responses',
                        is_request_body=True,
                        is_url=True):
        docs = [f'{i}. ' + self.formulate(tool, is_description=is_description,
                                          is_parameters=is_parameters,
                                          is_request_body=is_request_body, is_url=is_url,
                                          execution_results_type=execution_results_type,
                                          is_request_type=is_request_type)
                for i, tool in enumerate(tools, start=1)]

        instruction = GPT_SPOTIFY_INSTRUCTION.format(system=self.system, headers=json.dumps(self.headers, indent=4), query=query, docs='\n'.join(docs))

        return instruction



class WeatherTools(Tools):

    def __init__(self, system, oas_spec):
        super(WeatherTools, self).__init__(system=system, oas_spec=oas_spec)
        self.headers = {
            'X-RapidAPI-Key': '0ade7be5b2mshd53f97c3d81bcd4p1587abjsn25826e5f4a79',
            'X-RapidAPI-Host': 'ai-weather-by-meteosource.p.rapidapi.com'
        }
    def get_instruction(self, query, tools,
                        is_description=True,
                        is_parameters=True,
                        is_request_type=True,
                        execution_results_type='responses',
                        is_request_body=True,
                        is_url=True):
        docs = [f'{i}. ' + self.formulate(tool, is_description=is_description,
                                          is_parameters=is_parameters,
                                          is_request_body=is_request_body, is_url=is_url,
                                          execution_results_type=execution_results_type,
                                          is_request_type=is_request_type)
                for i, tool in enumerate(tools, start=1)]

        instruction = """Here are some APIs used to access the Open Weather platform. You need to answer the question by writing python code to call appreciate APIs and `print` the final answer. The API can be accessed via HTTP request. 

Here are the OpenAPI Specification of given APIs, including their http url, description, arguments and execution results.
{docs}

You should use the following Http headers to call the API:
```python
headers = {headers}
```
Note: I will give you the `headers` used to request the http server. Do not make up one in your code. Here is an example to request the API:
```python
import requests
url = "<The API url selected from the above APIs>"
params = "<The params dict>"
response = requests.get(url, headers=headers, params=params) # The variable `headers` has been defined, please JUST USE it.
```
If the API path contains "{{}}", it means that it is a variable and you should replace it with the appropriate value. For example, if the path is "/users/{{user_id}}/tweets", you should replace "{{user_id}}" with the user id. "{{" and "}}" cannot appear in the url.

Based on provided APIs, please write python code to call API and solve it. Try to write correct Python Code and avoid grammar error, e.g. `variable is not defined`.  You need to provide Python code that can be executed directly; Please add the name of the used APIs in Python comments for the attributable consideration. 

**Note**: any information, e.g., person id or movie id, you need to obtain it by calling appropriate APIs. DO NOT make up value by yourself!

Query: {query}
Your output:
```python
headers = {headers}
Complete the python code...
```""".format(headers=json.dumps(self.headers, indent=4), query=query, docs='\n\n'.join(docs))

        user_query = f"""# Your Output
Starting below, you need to provide Python code that can be executed directly; any explanations should be marked as Python comments. Note: DO NOT make up value by yourself, please use the given APIs to acquire information (e.g., person ID or movie ID). 

Query: {query}
Your output:
```python
[Please write the code]
```"""

        instruction = [instruction, user_query]
        instruction = '\n'.join(instruction)

        return instruction

class RapidTools(Tools):
    def __init__(self, system, oas_spec):
        super(RapidTools, self).__init__(system=system, oas_spec=oas_spec)
        self.headers = {
            'Authorization': f'Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
        }



# ====================== LLMs Tools ========================


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


# ====================== API manager ========================

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

def multi_process_func(ranks, func, data, model):
    pools = multiprocessing.Pool(processes=len(ranks))
    length = math.ceil(len(data) // len(ranks))
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
    results = []

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
        line['output'] = res
        line['match'] = len([e for e in line['solution'] if e.split(' ')[-1].strip() in res]), len(line['solution'])

        # print('-' * 50)
        # print(line['solution'])
        # print(res)

        results.append(line)

    return rank, results


if __name__ == '__main__':
    data = load_data('/Users/shizhl/Paper2024/ProTool/dataset/tmdb.json')
    results = func(0, data, 'gpt-3.5-turbo')
