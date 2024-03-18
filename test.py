# """
# using manually-constructed OAS document to code
# """
# import json
# import math
# import random
# from utilize.utilze import load_data, write_file
# from model.base import Base, TMDBTools, SpotifyTools
# from utilize.apis import get_from_openai
# import tiktoken
# import multiprocessing
# from tqdm import tqdm
# import sys
# from pydantic import BaseModel, Field, Extra
# from typing import Any, Dict, List, Optional
# from io import StringIO
# import re
#
# encoder = tiktoken.encoding_for_model('gpt-3.5-turbo')
#
#
# def multi_process_func(ranks, func, data, model):
#     pools = multiprocessing.Pool(processes=len(ranks))
#     length = math.ceil(len(data) // len(ranks))
#     collects = []
#     for ids, rank in enumerate(ranks):
#         collect = data[ids * length:(ids + 1) * length]
#         collects.append(pools.apply_async(func, (rank, collect, model)))
#     pools.close()
#     pools.join()
#     results = []
#     for rank, result in zip(ranks, collects):
#         r, res = result.get()
#         assert r == rank
#         results.extend(res)
#     return results
#
#
# class PythonREPL(BaseModel):
#     """Simulates a standalone Python REPL."""
#
#     globals: Optional[Dict] = Field(default_factory=dict, alias="_globals")
#     locals: Optional[Dict] = Field(default_factory=dict, alias="_locals")
#
#     def run(self, command: str) -> str:
#         """Run command with own globals/locals and returns anything printed."""
#         old_stdout = sys.stdout
#         sys.stdout = mystdout = StringIO()
#         try:
#             exec(command, self.globals, self.locals)
#             sys.stdout = old_stdout
#             output = mystdout.getvalue()
#         except Exception as e:
#             sys.stdout = old_stdout
#             print(str(e))
#             output = None
#         return output
#
#
# def initial_tool(dataset):
#     if dataset == 'tmdb':
#         toolsets = TMDBTools(
#             system='Here are some APIs used to access the TMDB platform. You need to answer the question by writing python code to call appreciate APIs. The API can be accessed via HTTP request. ',
#             oas_spec='./dataset/tmdb_api_spec.json',
#         )
#     elif dataset == 'spotify':
#         toolsets = SpotifyTools(
#             system='Here are some APIs used to access the Spotify platform. You need to answer the question by writing python code to call appreciate APIs. The API can be accessed via HTTP request. ',
#             oas_spec='./dataset/spotify_api_spec.json',
#         )
#     else:
#         raise NotImplemented
#
#     return toolsets
#
#
# def run(rank, data, model_name):
#     toolsets = initial_tool(data[0]['dataset'])
#     results = []
#     model = Base(model_name=model_name)
#     negative = toolsets.get_tool_list()
#     for line in tqdm(data):
#         # print(line)
#         tools = line['solution']
#         # while len(tools) < 7:
#         #     tool = negative[random.randint(0, 10000) % len(negative)]
#         #     if tool not in tools:
#         #         tools.append(tool)
#         try:
#             instruction = toolsets.get_instruction(line['query'], tools)
#             # print(instruction)
#             encoded_docs = encoder.encode(instruction)
#             print(len(encoded_docs))
#             line['results'] = model.generate(messages=[{"role": "user", 'content': instruction}])
#             line['usage'] = model.token[-1]
#         except:
#             print(line)
#             line['results'] = None
#         results.append(line)
#
#     return rank, results
#
#
# def evaluate(results):
#     cnt = []
#     access_token = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwZGJhYjU5MGM3ZWFjYTA3ZWJlNjI1OTc0YTM3YWQ5MiIsInN1YiI6IjY1MmNmODM3NjYxMWI0MDBmZmM3MDM5OCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.McsK4Wm5XnRSDLn62Jhy787YUAwZcQz0X5qzkGuLe_s'
#     headers = {
#         'Authorization': f'Bearer {access_token}'
#     }
#     accurate = []
#     for line in tqdm(results[:10]):
#         if 'results' not in line or line['results'] == None:
#             cnt.append(0)
#             accurate.append(0)
#
#         print('*' * 50)
#         pattern = r"```python(.*?)```"
#         try:
#             matches = re.findall(pattern, line['results'], re.DOTALL)
#             # 执行程序，计算成功率
#             if matches == []:
#                 cnt.append(0)
#                 continue
#             else:
#                 repl = PythonREPL(_globals={"headers": headers, "header": "headers"})
#                 print(matches[0])
#                 res = repl.run('import requests\n' + matches[0])
#                 if res == None or 'not defined' in res:
#                     cnt.append(0)
#                 else:
#                     cnt.append(1)
#                     print(res)
#                 line['executed'] = res
#             # 计算api的覆盖率
#             accurate.append(
#                 sum([1 if e.split(' ')[-1].strip() in line['results'] else 0 for e in line['solution']]) / len(line['solution'])
#             )
#             if accurate[-1] == 0:
#                 print(line['query'])
#                 print(line['solution'])
#                 print(line['results'])
#         except:
#             cnt.append(0)
#             accurate.append(0)
#     print(sum(cnt) / len(cnt))
#     print(sum(accurate) / len(accurate))
#     return results
#
#
# if __name__ == '__main__':
#     data = load_data('./dataset/spotify.json')
#     data = [line for line in data if line['q_id'] not in [4, 11, 15, 47, 50]]
#     # results = run(0, data, 'gpt-3.5-turbo')
#     # results = multi_process_func(ranks=list(range(10)), func=run, data=data, model='gpt-3.5-turbo')
#     # write_file(results, './logs/spotify/naive_results.spotify.oracle.2.json')
#     results = evaluate(load_data('./logs/spotify/naive_results.spotify.oracle.2.json'))
#     write_file(results, './logs/spotify/naive_results.spotify.oracle.2.json')



