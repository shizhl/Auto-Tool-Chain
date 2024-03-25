import random
from collections import defaultdict
from model.base import Tools, TMDBTools
from model.base import Base
from utilize.apis import get_from_openai
from utilize.utilze import load_data, write_file
from tqdm import tqdm
from model.engine import *
import ast
import yaml

model_name = 'gpt-3.5-turbo'
dataset = 'spotify'  # spotify
if dataset == 'tmdb':
    headers = {
        'Authorization': f'Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
    }
else:
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
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

env = PythonExecNet(dataset=dataset)

system_single = f"""In this task, you are a programming engineer. Your task is to test the provided APIs, which are provided by the OpenAPI platform to access the web information, e.g., movie and music.
Specifically, you need to write Python code to pass the required arguments to call the APIs, getting the execution results of the APIs.

You should use the following HTTP header to call the API:
```python
{headers}
```
Note: I will give you 'headers', do not makeup one, just reference it in your code!!!

Here is an example to request the API:
```python
import requests
url = "<The API url selected from the above APIs>"
params = "<The params dict>"
response = requests.get(url, headers=headers, params=params) # The variable `headers` has been defined, please JUST USE it in your code!
```"""

user_single = """Here are the OpenAPI Specification of given APIs, including their HTTP URL, functional description, and argument details.

{docs}

To test the APIs, please first propose a clear and detailed query to specify the purpose of your test code, e.g., 'find a movies named The Matrix' or 'get some keywords of the TV series named Friends'. Then provide Python code that can be executed directly to finish your query and get the execution results.
Note that: please always transform the raw execution results into `str` (e.g., json.dumps(response.json(),indent=0)) and print them in your code via `print()`. Not not print any extra.

Starting below, your should follow this format:
Query: "propose your query"
Test code: ```python
import json
def test_code(param...):
    ...implement details
    
# call your `test_code` function
...
# transform the raw execution results into `str` print the execution results
print(json.dumps(response.json(),indent=0))
```"""

system_multi = f"""In this task, you are a programming engineer. Your task is to help me test one black-box API, which lacks detailed OpenAPI specification documentation. 
Specifically, I only know the description, parameter and request url of this black-box API. However, I want to analyze its execution results. So, you need to write Python code to pass the required arguments to call the APIs, getting the execution results of the APIs.

Since you may need the parameter to call the black-box API, I also provide your some known APIs with clear documentation, including the functional description, parameters, request type (HTTP GET or POST) and execution result example. You can use these APIs to first get required information( e.g., id), and then call the black-box API.
 
All the APIs are called via HTTP request. And you should use the following HTTP header to call the API:
```python
{headers}
```
Note: I will give you 'headers', do not makeup one, just reference it in your code!!!

Here is an example to request the API:
```python
import requests
url = "<The API url selected from the above APIs>"
params = "<The params dict>"
response = requests.get(url, headers=headers, params=params) # The variable `headers` has been defined, please JUST USE it in your code!
```"""

user_multi = """Here is the black-box API you should test. We only know is description, parameter, and request URL. 

{t_doc}

Since you may need specific parameters, e.g., id, to call this black-box API, I also provide you with some known APIs to get the required value you need. These APIs have detailed OpenAPI Specification.

{docs}

To test the block-box API, please first propose a clear and detailed query to specify the purpose of your test code, e.g., 'find movies named The Matrix' or 'get some keywords of the TV series named Friends'. Then provide Python code that can be executed directly to finish your query and get the execution results.
Note that: please always transform the raw execution results of the block-box API into `str` (e.g., json.dumps(response.json(),indent=0)) and print them in your code via `print()`. Don't print any extra.

Starting below, you should follow this format:
Query: "Propose your query"
Test code: ```python
import json

def test_code(param...):
    ...implement details

# call your `test_code` function
...

# transform the raw execution results into `str` and print the execution results
if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
    print(json.dumps(response.json(),indent=0))
else:
    print(response.text)
```"""

tool_rank = """In this task, you are a programming engineer. Your task is to help me test one black-box API, which lacks detailed OpenAPI specification documentation. 
Specifically, I only know the description, parameter and request url of this black-box API. However, I want to analyze its execution results. So, you need to write Python code to pass the required arguments to call the APIs, getting the execution results of the APIs.
Here is the details of the black-box API:

{doc}

Since you may need the parameter to call the black-box API, I also provide your some known APIs. You should select the APIs you need to get the required parameter (e.g., id) used call the black-box API. Here are some candidate APIs you can select:

{api_list}

Starting below, you should select the APIs by giving their name and write each API in a new line. And you are encouraged to select more APIs you might use.
Your selection:
```output:
[1] first API name...
[2] ...
...
```"""

query_generation = """In this task, you are a creative software engineer and you are provide an API. Your task is to propose a specific question which can be answer by calling this API. You question will be taken as the usage and added in the API documentation.
Here is the OpenAPI specification of the API.

{doc}

Please propose one question which can be solved by calling this API:
Question: """



def run_single_probing():
    toolsets = TMDBTools(
        system='Here are some APIs used to access the TMDB platform. You need to answer the question by writing python code to call appreciate APIs and `print` the final answer. The API can be accessed via HTTP request. ',
        oas_spec='../dataset/tmdb_api_spec.json',
    )
    # spec = load_data('../dataset/tmdb_api_spec.json')
    cnt = 0
    spec = load_data('../dataset/tmdb.pseudo_spec.json')

    for line in tqdm(spec['endpoints']):
        print('*' * 50)
        tool = line[0]
        docs = [toolsets.formulate(tool, is_description=True, is_parameters=True, is_request_type=True, execution_results_type=None)]
        message = [
            {"role": "system", 'content': system_single},
            {"role": "user", 'content': user_single.format(docs='\n'.join([f'{i}. {e}' for i, e in enumerate(docs, 1)]))}
        ]
        # code = get_from_openai(model_name=model_name,messages=message)['content']
        # line[2]['code'] = code
        code = line[2]['code']
        pattern = r"```python(.*?)```"
        print(code.split('\n')[0])
        matches = re.findall(pattern, code, re.DOTALL)
        example, state = env.run(matches[0])
        try:
            example = json.loads(example)
            # example = ast.literal_eval(example)
            if state == False:
                print(tool)
                print(example)
                cnt += 0
                line[2]['example'] = None
                line[2]['_responses_json'] = None
                line[2]['_responses_yaml'] = None
            else:
                cnt += 1
                line[2]['example'] = example
                line[2]['_responses_json'] = simplify_json(example)
                line[2]['_responses_yaml'] = '\n'.join(get_yaml(example, 'execution result'))
        except:
            cnt += 0
            line[2]['example'] = None
            line[2]['_responses_json'] = None
            line[2]['_responses_yaml'] = None
            print(tool)
            print(example)

    print(cnt)
    write_file(spec, '../dataset/tmdb.pseudo_spec.json')


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

        if '_response_json' in spec and spec['_response_json'] is not None:
            self.responses['_response_json'] = json.dumps(spec['_response_json'], indent=4) if type(spec['_response_json']) == dict else spec['_response_json']
        else:
            self.responses['_response_json'] = None

        if '_response_yaml' in spec and spec['_response_yaml'] is not None:
            self.responses['_response_yaml'] = spec['_response_yaml']
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
                if p['in'] != 'query':
                    continue
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
            response = '### Execution result specification\n' + self.responses[execution_results_type]
            text_doc.append(response)
        if is_request_body:
            requestBody = '### Request body\n' + json.dumps(self.requestBody, indent=4)
            text_doc.append(requestBody)
        text_doc = '\n'.join(text_doc)
        return text_doc

def is_json(json_str):
    try:
        tmp = json.loads(json_str)
        return True
    except:
        return False


def _probing(t, tools):

    docs = [tool.formulate(is_description=True, is_parameters=True, is_request_type=True, execution_results_type='_responses_json')
            for tool in [t] + tools]
    # random.shuffle(docs)

    if tools == []:
        message = [
            {"role": "system", 'content': system_single},
            {"role": "user", 'content': user_single.format(docs='\n'.join([f'{i}. {e}' for i, e in enumerate(docs, 1)]))}
        ]
    else:
        message = [
            {"role": "system", 'content': system_multi},
            {"role": "user", 'content': user_multi.format(t_doc=docs[0], docs='\n'.join([f'{i}. {e}' for i, e in enumerate(docs[1:], 1)]))},
        ]


    try:
        for i in range(3):
            code = get_from_openai(model_name=model_name, messages=message)['content']
            pattern = r"```python(.*?)```"
            matches = re.findall(pattern, code, re.DOTALL)

            execute_code = code.split('\n')[0].replace('```python', '').replace('```', '') if len(matches) == 0 else matches[0]
            example, state = env.run(execute_code)
            if state == True:
                if is_json(example):
                    example = json.loads(example)
                    result = {}
                    result['example'] = example
                    result['_responses_json'] = simplify_json(example)
                    result['_responses_yaml'] = '\n'.join(get_yaml(example, 'execution result'))
                    return result
                else:
                    message.append({"role":"assistant",'content': code})

                    feedback = """Please print the raw execution results of the API in the json format as follows.
```python
if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
    print(json.dumps(response.json(),indent=0))
else:
    print(response.text)
```"""
                    message.append({"role":"user",'content': feedback})
        # example = ast.literal_eval(example)
    except:
        return None

    return None


def topology_probing(filename='../dataset/tmdb_api_spec_v1.json', k=3):
    def random_sample(l, n):
        examples = []
        while len(examples) < n:
            a = random.randint(0, 1000000) % len(l)
            if a not in examples:
                examples.append(a)
        examples = [l[i] for i in examples]
        return examples

    def LLM_sample(target, candidates):
        doc = api_spec[target].formulate(is_description=True, is_parameters=True, is_request_type=True, execution_results_type='_responses_json')
        candidates = [
            api_spec[e].formulate(is_description=True, is_parameters=False, is_url=False, is_request_type=False, is_request_body=False, execution_results_type=None)
            for e in candidates
        ]
        candidates = '\n\n'.join([f'[{i}]. {e}' for i, e in enumerate(candidates, 1)])
        tools = get_from_openai(model_name=model_name,
                                messages=[{"role": "user", "content": tool_rank.format(doc=doc, api_list=candidates)}])['content']
        tools = tools.replace('```output', '').replace('```', '')
        tools = [normalize(e) for e in tools.split('\n') if e != '']
        return tools

    cnt = 0
    raw_spec = load_data(filename)
    cache_api = []  # 已经探索过的api
    cache_traj = []  # 探索的trajectory

    api_spec, api_list = defaultdict(Tool), []
    for e in raw_spec['endpoints']:
        api_list.append(e['name'])
        api_spec[e['name']] = Tool(e)
        if '_responses_json' in e:
            cache_api.append(e['name'])

    api_list = [e for e in api_list if e not in cache_api]

    # 初始
    for api in tqdm(api_list):
    # for api in tqdm(['GET_search']):
        result = _probing(api_spec[api], [])
        if result is not None:
            print(api)
            api_spec[api].update_response('_responses_json', result['_responses_json'])
            api_spec[api].update_response('_responses_yaml', result['_responses_yaml'])
            cache_api.append(api)

    api_list = [e for e in api_list if e not in cache_api]
    print(len(api_list))
    while len(api_list) > 0 and cnt < 5:
        cnt += 1
        print(f'==========={cnt}==========')
        for api in tqdm(api_list):
            # apis = random_sample(cache_api, k)
            apis = LLM_sample(api, cache_api)
            apis = [e for e in apis if e in api_spec]
            result = _probing(api_spec[api], [api_spec[e] for e in apis])
            if result is not None:
                print(api)
                api_spec[api].update_response('_responses_json', result['_responses_json'])
                api_spec[api].update_response('_responses_yaml', result['_responses_yaml'])
                cache_api.append(api)
        api_list = [e for e in api_list if e not in cache_api]

    for i, endpoint in enumerate(raw_spec['endpoints']):
        if endpoint['name'] in cache_api:
            raw_spec['endpoints'][i]['_responses_json'] = api_spec[endpoint['name']].responses['_responses_json']
            raw_spec['endpoints'][i]['_responses_yaml'] = api_spec[endpoint['name']].responses['_responses_yaml']

    return raw_spec


# filename='../dataset/tmdb_api_spec_v1.json'
filename = '../dataset/spotify.topo.v0.api_spec.json'
res = topology_probing(filename)
write_file(res, '../dataset/spotify.topo.v1.api_spec.json')
