import requests
from model.base import Base, TMDBTools,LLMTools
from tqdm import tqdm
import sys
from pydantic import BaseModel, Field, Extra
from typing import Any, Dict, List, Optional
from io import StringIO
import re
import traceback
from model.engine import PythonExecNet


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
            output = '\n'.join([
                '------------There are something error in your output code-------------',
                f'except Exception as e - Exception Type: {type(e).__name__}',
                f'except Exception as e - Exception Value: {e}',
            ])
            state=0
        return state,output

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

def evaluate(results,dataset='tmdb'):
    cnt = []
    accurate=[]
    LLM_function=[]
    env = PythonExecNet(dataset)
    for line in tqdm(results):
        if 'code' not in line or line['code'] == None:
            cnt.append(0)
            accurate.append(0)
            LLM_function.append(0)

        pattern = r"```python(.*?)```"
        matches = re.findall(pattern, line['code'], re.DOTALL)

        # execute the code
        # execute_state, res = execute_code(line['code'])
        if matches==[]:
            code = line['code']
        else:
            code = matches[0]
        res, execute_state = env.run(code)
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
            # print(line['results'])
        if LLM_function[-1] != 0:
            print('Trigger LLMs function')
            print(line['query'])
            print(line['solution'])
            # print(line['results'])
    print(sum(cnt) / len(cnt))
    print(sum(accurate) / len(accurate))
    return results


