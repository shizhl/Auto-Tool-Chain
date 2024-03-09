import json
from utilize.apis import get_from_openai


class Base:

    def __init__(self, model_name='gpt-3.5-turbo'):
        self.model_name = model_name
        self.token = []

    def normalize(self, sss):
        return sss

    def generate(self, messages):
        res = get_from_openai(model_name=self.model_name, messages=messages)
        self.token.append([res['usage'].completion_tokens,res['usage'].prompt_tokens,res['usage'].total_tokens])
        return self.normalize(res['content'])

    def get_token(self):
        tmp=[]
        for line in self.token:
            tmp=[e1+e2 for e1,e2 in zip(tmp,line)]
        return tmp
#
# class Tools:
#
#     def __init__(self,):

class TMDBTools:

    def __init__(self, system, oas_spec):
        self.system = system
        access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
        self.header = {
            'Authorization': f'Bearer {access_token}'
        }
        self.api_spec = json.load(open(oas_spec))
        self.endpoint = {}
        self.host = self.api_spec['servers'][0]['url']
        for line in self.api_spec['endpoints']:
            tmp = {
                "name": line[0].split(' ')[0] + ' ' + self.host + line[0].split(' ')[-1],  # unique id for each api
                "url": self.host + line[0].split(' ')[-1],
                "method": line[0].split(' ')[0],
                "description": line[1],
                "parameter": line[-1]['parameters'] if 'parameters' in line[-1] else [],
                "usage": None,
                'response': line[-1]['responses']['content']['application/json']["schema"]['properties']
            }
            self.endpoint[tmp['name']] = tmp

    def match(self, name):

        return name

    def get_tool_list(self, ):

        tmp = [k for k, v in self.endpoint.items()]
        return tmp

    def get_doc_by_name(self, name):
        tool = self.match(name.strip())
        return self.endpoint[tool]

    def formulate(self, tool):
        # print(tool)
        doc = self.get_doc_by_name(tool)
        if len(doc['parameter']) == 0:
            parameter = '## Parameter:\nNo extra parameter, just replace the `{variable}` in the url path with actual value.'
        else:
            parameter = []
            for p in doc['parameter']:
                if p['in'] != 'query':
                    continue
                tmp = "- " + p['name'] + ": " + p['description'].replace('\n', '')
                if 'schema' in p and 'type' in p['schema']:
                    tmp += " (type: " + p['schema']['type'] + ")"
                parameter.append(tmp)
            parameter = '\n'.join(parameter)
        # print(tool)
        response = json.dumps(doc['response'], indent=4)
        text_doc = """API url: {url}
## Request type:
{method}
## Description
{description}
## Parameter
{parameter}
## Execution result
{response}
""".format(url=doc['url'],
           description=doc['description'].replace('\n', ' '),
           parameter=parameter,
           response=response,
           method=doc['method'])
        return text_doc

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
