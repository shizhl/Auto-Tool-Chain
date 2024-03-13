"""
using manually-constructed OAS document to code
"""
import requests
import copy
import json
import math
import os
import random
from utilize import metrics
from utilize.utilze import load_data, write_file
from model.base import Base, TMDBTools,LLMTools
from utilize.apis import get_from_openai
import tiktoken
import multiprocessing
from tqdm import tqdm
import sys
from pydantic import BaseModel, Field, Extra
from typing import Any, Dict, List, Optional
from io import StringIO
import re
import traceback

encoder = tiktoken.encoding_for_model('gpt-3.5-turbo')


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

class PythonREPL(BaseModel):
    """Simulates a standalone Python REPL."""

    globals: Optional[Dict] = Field(default_factory=dict, alias="_globals")
    locals: Optional[Dict] = Field(default_factory=dict, alias="_locals")

    def run(self, command: str) -> [int,str]:
        """Run command with own globals/locals and returns anything printed."""
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        try:
            exec(command, self.globals, self.locals)
            sys.stdout = old_stdout
            output = mystdout.getvalue()
            state=1
        except Exception as e:
            sys.stdout = old_stdout
            # print(str(e))
            output = '\n'.join([
                '------------There are something error in your output code-------------',
                f'except Exception as e - Exception Type: {type(e).__name__}',
                f'except Exception as e - Exception Value: {e}',
                # traceback.format_exc(),
                # '\nPlease debug the error and generate a correct code: ```python\n[Your code]\n```.'
            ])
            state=0
        return state,output

# class PythonREPL(BaseModel):
#     """Simulates a standalone Python REPL."""
#
#     # globals: Optional[Dict] = Field(default_factory=dict, alias="_globals")
#     # locals: Optional[Dict] = Field(default_factory=dict, alias="_locals")
#
#     def __init__(self, **data):
#         super().__init__(**data)
#         self._globals = {'requests': requests}  # 设置requests为全局变量
#
#     def run(self, command: str) -> [int, str]:
#         """Run command and return anything printed, along with a state flag."""
#         local_env = self._globals.copy()  # 使用包含requests的全局变量
#         old_stdout = sys.stdout
#         sys.stdout = mystdout = StringIO()
#         try:
#             exec(command, local_env, local_env)  # 使用相同的字典作为globals和locals
#             sys.stdout = old_stdout
#             output = mystdout.getvalue()
#             state = 1
#         except Exception as e:
#             sys.stdout = old_stdout
#             # print(str(e))
#             output = '\n'.join([
#                 '------------There are something error in the output code-------------',
#                 f'except Exception as e - Exception Type: {type(e).__name__}',
#                 f'except Exception as e - Exception Value: {e}',
#                 traceback.format_exc(),
#                 '\nPlease debug the error and generate a correct code: ```python\n[Your code]\n```.'
#             ])
#             state=0
#         return state,output

def run_tmdb(rank, data, model_name):
    toolsets = TMDBTools(
        system='Here are some APIs used to access the TMDB platform. You need to answer the question by writing python code to call appreciate APIs and `print` the final answer. The API can be accessed via HTTP request. ',
        oas_spec='../dataset/tmdb_api_spec.json',
    )
    results = []
    model = Base(model_name=model_name)
    negative = toolsets.get_tool_list()
    for line in tqdm(data):
        # print(line)
        tools = copy.deepcopy(line['solution'])
        while len(tools) < 5:
            tool = negative[random.randint(0, 10000) % len(negative)]
            if tool not in tools:
                tools.append(tool)
        line['api_list']=tools
        # try:
        instruction = toolsets.get_instruction(line['query'], tools,LM_function=True)
        # print(instruction)
        encoded_docs = encoder.encode(instruction)
        print(len(encoded_docs))

        messages = [{"role": "user", 'content': instruction}]
        line['usage']=[]
        for i in range(3):
            code=model.generate(messages=messages)
            state, res = execute_code(code)
            line['usage'].append(model.token[-1])
            line['code'] = code
            line['results'] = res
            # print(code)
            if state:
                break
            else:
                messages.append({"role": "assistant","content":code})
                messages.append({"role": "user", "content": res})
        # except:
        #     print(line)
        #     line['results'] = None

        results.append(line)

    return rank, results


def run_spotify(rank,data,model_name):
    pass


def execute_code(code):
    access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    print('*' * 50)
    pattern = r"```python(.*?)```"
    matches = re.findall(pattern, code, re.DOTALL)
    # 执行程序，计算成功率
    if matches == []:
        return 0,None
    else:
        repl = PythonREPL(_globals={"headers": headers, "header": headers, "requests":requests,
                                    "generic_instructional_function": LLMTools.generic_instructional_function,
                                    "vague_match_function": LLMTools.vague_match_function,
                                    'personalized_selection_from_list': LLMTools.personalized_selection_from_list})
        execute_state, res = repl.run('import requests\n' + matches[0])
        print(matches[0])
        print(res)
        return execute_state, res

def count(results):
    a=0
    for line in ['vague_match_function','generic_instructional_function','personalized_selection_from_list']:
        if line in results:
            a+=1
    return a

def evaluate(results):
    cnt = []
    accurate=[]
    LLM_function=[]

    for line in tqdm(results):
        if 'code' not in line or line['code'] == None:
            cnt.append(0)
            accurate.append(0)
            LLM_function.append(0)

        # execute the code
        execute_state, res = execute_code(line['code'])
        line['executed_res'] = res
        line['executed_state'] = execute_state

        cnt.append(execute_state)

        # 计算api的覆盖率
        accurate.append(
            sum([1 if e.split(' ')[-1].strip() in line['code'] else 0 for e in line['solution']])/len(line['solution'])
        )
        LLM_function.append(count(line['code']))

        if accurate[-1]==0:
            print('No API')
            print(line['query'])
            print(line['solution'])
            print(line['results'])
        if LLM_function[-1] != 0:
            print('Trigger LLMs function')
            print(line['query'])
            print(line['solution'])
            print(line['results'])
    print(sum(cnt) / len(cnt))
    print(sum(accurate) / len(accurate))
    return results


if __name__ == '__main__':
    data = load_data('/Users/shizhl/Paper2024/ProTool/dataset/tmdb.json')
    results=run_tmdb(0, data, 'gpt-3.5-turbo')
    # results = multi_process_func(ranks=list(range(10)), func=run_tmdb, data=data, model='gpt-3.5-turbo')
    write_file(results, '../logs/tmdb/LM_results.5.3.json')
    results=evaluate(load_data('../logs/tmdb/LM_results.5.3.json'))
    write_file(results, '../logs/tmdb/LM_results_exec.5.3.json')


# folder='/Users/shizhl/Paper2024/ProTool/logs/tmdb'
# data=load_data('/Users/shizhl/Paper2024/ProTool/dataset/tmdb.json')
# q2s={line['query']:line['solution'] for line in data}
# for file in os.listdir(folder):
#     file=os.path.join(folder,file)
#     tmp=load_data(file)
#     for line in tmp:
#         api_list=line.pop('solution')
#         line['solution']=q2s[line['query']]
#         line['api_list']=api_list
#     json.dump(tmp,open(file,'w'),indent=4)