import numpy as np
import openai
import tiktoken
from tqdm.auto import trange, tqdm
import time
import os
import json
from tqdm import tqdm
import re
from types import NoneType
import multiprocessing.dummy
from io import StringIO
from contextlib import redirect_stdout
import signal
from contextlib import contextmanager
import matplotlib.pyplot as plt
import sys
import ast
import copy
from openai import OpenAI
import random

ENGINE = 'gpt-3.5-turbo-instruct'
CORRECT_ANSWER = '52'
ANSWER_TOKEN = 'Answer: '
CODE_START_TOKEN = "# CODE START"
CODE_END_TOKEN = "# CODE END"
MAX_TOKENS = 4096
ENCODER = tiktoken.encoding_for_model(ENGINE)

api_keys_list = [
    'sk-ZmVeKnYDii42NZzVD245Af89F04b469dB9Db08C9B85aCf30'
]


def get_from_openai(model_name='gpt-3.5-turbo', base_url=None, api_key=None,
                    messages=None, prompt=None, stop=None, max_len=1000, temp=1, n=1,
                    json_mode=False, usage=False):
    """
    :param model_name: text-davinci-003, gpt-3.5-turbo, gpt-3.5-turbo-0613
    """
    for i in range(10):
        # try:
            client = OpenAI(api_key=api_keys_list[random.randint(0, 100000) % len(api_keys_list)] if api_key is None else api_key,
                            base_url='https://api.aiguoguo199.com/v1' if base_url is None else base_url)
            kwargs = {
                "model": model_name, 'max_tokens': max_len, "temperature": temp,
                "n": n, 'stop': stop,
            }
            if json_mode == True:
                kwargs['response_format'] = {"type": "json_object"}
            if 'instruct' in model_name:
                assert prompt is not None
                kwargs['prompt'] = prompt
                response = client.completions.create(**kwargs)
                content = response.choices[0].text  if n == 1 else [res.text for res in response.choices]
            else:
                assert messages is not None
                kwargs['messages'] = messages
                response = client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content if n == 1 else [res.message.content for res in response.choices]
            results = {"content": content}
            if usage == False:
                results['usage'] = response.usage
            return results
        # except:
        #     error = sys.exc_info()[0]
        #     print("API error:", error)
        #     time.sleep(1)
    return 'no response from openai model...'


def query_llm(prompt, max_tokens, stop=None, temperature=0):
    assert type(prompt)
    response = get_from_openai(model_name=ENGINE, prompt=prompt, max_len=max_tokens, temp=temperature, stop=stop)['content']
    # response = get_from_openai(model_name=ENGINE, messages=[{"role":'user','content':prompt}], max_len=max_tokens, temp=temperature, stop=stop)['content']
    return response


def print_result(method, response, answer):
    print("#### Method ####")
    print(method)
    print("#### Full Response ####")
    print(response)
    print("#### Model Answer ####")
    print(answer)
    print("#### Correct Answer ####")
    print(CORRECT_ANSWER)


errors = {}
error_lineno = None
lines = None
trace_lines = []
last_state = None


def get_delta_state(state, last_state):
    delta_state = {}
    for key, val in state.items():
        if key not in last_state or val != last_state[key]:
            delta_state[key] = val
    return delta_state


def get_state(frame):
    state = {}
    for key, item in frame.f_locals.items():
        if isinstance(item, (bool, str, int, float, tuple, list, set, dict, NoneType)):
            state[key] = item
    return state


def show_trace(frame, event, arg):
    # Declare these global variable first
    global errors
    global error_lineno
    global lines
    global trace_lines
    global last_state
    global lines_run_history

    # The LLM-generated code will be wrapped around in the get_answer function call.
    # If we don't filter by "get_answer", we got a bunch of random exception from colab
    if frame.f_code.co_name != "get_answer":
        return

    lineno = frame.f_lineno - 1
    # Running a certain line
    if event == "line":
        current_line = lines[lineno]
        if current_line.strip() in ["try:", "except:", "pass"]:
            pass
        elif current_line.strip() == "return answer":
            assert lineno == len(lines) - 2, "return answer is at the wrong line"  # Second to last line
            state = get_state(frame)
            assert last_state is not None
            delta_state = get_delta_state(state, last_state)
            trace_lines.append(f"delta state: {delta_state}")
            # Append the final state
            trace_lines.append(f"final state: {state}")
        elif lineno not in errors:
            # We previous indent 2 spaces
            assert current_line[:2] == "  ", f"Python: actual line to run doesn't have two leading spaces: {current_line} {lines}"
            # Now we revert back
            current_line = current_line[2:]

            state = get_state(frame)
            delta_state = None
            if last_state is None:
                delta_state = None
            else:
                delta_state = get_delta_state(state, last_state)
            last_state = copy.deepcopy(state)

            if delta_state is None:
                trace_lines.append("state: {}")
            else:
                trace_lines.append(f"delta state: {delta_state}")
            trace_lines.append(f"line: {current_line}")
        else:
            # We previous indent 4 spaces
            assert current_line[:4] == "    ", f"LLM: actual line to run doesn't have four leading spaces: {current_line} {lines}"
            # Now we revert back
            current_line = current_line[4:]
            # When LLM excutes, remove any trailing space at the beginning

            state = get_state(frame)
            delta_state = None
            if last_state is None:
                delta_state = None
            else:
                delta_state = get_delta_state(state, last_state)
            last_state = copy.deepcopy(state)

            if delta_state is None:
                trace_lines.append("state: {}")
            else:
                trace_lines.append(f"delta state: {delta_state}")
            trace_lines.append(f"line: {current_line}")

            # Due to the context length constraint, only feed in the last three lines of the trace.
            prompt = coc_trace_prompt + "\n" + "\n".join(trace_lines[-3:]) + "\n" + "delta state:"

            token_length = len(ENCODER.encode(prompt))

            llm_result = query_llm(prompt, max_tokens=32, stop=["\nline:"])

            progress_bar.update()
            program_state_str = llm_result.strip()
            try:
                new_program_state = ast.literal_eval(program_state_str)
                assert isinstance(new_program_state, dict), "new program state is not a valid dict"
                # Actually update the local variables with the new program state
                frame.f_locals.update(new_program_state)
            except Exception as e:
                raise e

    elif event == "exception":
        # Only capture the lowest level exception AND if this exception hasn't been "fixed" before, i.e. this line hasn't be sandwiched by try/except yet.
        if error_lineno is None and lineno not in errors:
            error_lineno = lineno

    return show_trace


sys.settrace(show_trace)

direct_prompt = """
Q: How many countries have I been to? I’ve been to Bilbao, Death Valley, Paris, Honolulu, Skye.
Answer: 4
""".strip()

cot_prompt = """
Q: How many countries have I been to? I’ve been to Bilbao, Death Valley, Paris, Honolulu, Skye.
A:
We'll group by countries and count:
1. Spain: Bilbao
2. USA: Death Valley, Honolulu
3. France: Paris
4. UK: Skye
There are 4 countries in total. So the answer is 4.
Answer: 4
""".strip()

coc_prompt = """
Q: How many countries have I been to? I’ve been to Bilbao, Death Valley, Paris, Honolulu, Skye.
A:
# CODE START
places = ["Bilbao", "Death Valley", "Paris", "Honolulu", "Skye"]
countries = set()
for place in places:
  country = get_country(place)
  countries.add(country)
answer = len(countries)
# CODE END
Answer: 4
""".strip()

coc_trace_prompt = """
# TRACE START
state: {}
line: places = ["Bilbao", "Death Valley", "Paris", "Honolulu", "Skye"]
delta state: {'places': ['Bilbao', 'Death Valley', 'Paris', 'Honolulu', 'Skye']}
line: countries = set()
delta state: {'countries': set()}
line: for place in places:
delta state: {'place': 'Bilbao'}
line:   country = get_country(place)
delta state: {'country': 'Spain'}
line:   countries.add(country)
delta state: {'countries': {'Spain'}}
line: for place in places:
delta state: {'place': 'Death Valley'}
line:   country = get_country(place)
delta state: {'country': 'USA'}
line:   countries.add(country)
delta state: {'countries': {'Spain', 'USA'}}
line: for place in places:
delta state: {'place': 'Paris'}
line:   country = get_country(place)
delta state: {'country': 'France'}
line:   countries.add(country)
delta state: {'countries': {'Spain', 'USA', 'France'}}
line: for place in places:
delta state: {'place': 'Honolulu'}
line:   country = get_country(place)
delta state: {'country': 'USA'}
line:   countries.add(country)
delta state: {'countries': {}}
line: for place in places:
delta state: {'place': 'Skye'}
line:   country = get_country(place)
delta state: {'country': 'UK'}
line:   countries.add(country)
delta state: {'countries': {'Spain', 'USA', 'France', 'UK'}}
line: answer = len(countries)
delta state: {'answer': 4}
# TRACE END

# TRACE START
""".strip()

query = """
Q: How many countries have I been to? I’ve been to Mumbai, London, Washington, Grand Canyon, Baltimore, Longsheng, Guilin, Beijing,
Galapagos, Quito, Barcelona, Paris, Prague, Nice, Dehli, Agra, Rome, Florence, Amalfi, Athens, Míkonos, Málaga, Monaco, Berlin,
Munich, Innsbruck, Bern, Milan, Lucerne, Gimmelwald (Schilthornbahn), St Moritz, St Petersburg, Helsinki, Amsterdam, Gdansk,
Vancouver, Anchorage, Montreal, Belize, The Bahamas, Jamaica, Hawaii, Acadia National Park, Stockholm, Copenhagen, Dover, Lyon,
Madrid, Toulouse, Santorini, Oslo, Kusadasi, Souda, Rhodes, Tallinn, Venice, Naples, Cape Town, Johannesburg, Addis Abeba,
Nairobi, Seattle, San Francisco, Chicago, St Louis, Memphis, Chinle, Stanford, New York, Philadelphia, Boston, Miami,
New Orleans, Walt Disney World Resort, Jacksonville, Las Vegas, Los Angeles, Portland, Salt Lake City, Tahoe City, Phoenix,
Albuquerque, Cleveland, Charlottesville, Nags Head, Newfoundland and Labrador, Burlington, Wilmington, Myrtle Beach, St Lucia,
Barbados, Banff, Haiti, Montego Bay, Sao Palo, Rio, Lima, Cusco, Cozumel, Amarillo, Yosemite National Park, Joshua Tree,
Zion National Park, Bryce Canyon National Park, Grand Teton National Park, Yellowstone National Park, Glacier National Park, Mount Hood,
Paso Robles, San Diego, Bend, North Cascades National Park, Olympic National Park Visitor Center, Jasper National Park,
Sequoia National Park, Kings Canyon National Park, Shasta National Forest, Mount Saint Helens, Mount Rainier, Austin, Buenos Aires,
El Calafate, El Chaltén, Fitz Roy, Torres del Paine National Park, Puerto Natales, Puerto Varas, Santiago, Marble Caves, Cerro Castillo,
Coyhaique, Singapore, Casablanca, Marrakesh, Cairo, Jerusalem, Tokyo, Kyoto Prefecture, Taipei City, Taichung City, Krk,
Naturpark Puez-Geisler, Ljubljana, Plitvice Lakes National Park, Fairbanks, Juneau, Dallas, Sydney, Cairns, Brisbane, Hook Island,
Charleston, Panama City, Bangkok, Chiang Mai, Bengaluru, Denver, Indianapolis, Nashville, Blacksburg, Lisbon, Porto, Estes Park,
Coeur d’Alene, Hood River, Denali, Sitka, Mexico City, Warsaw, Geneva, Auckland, Queenstown, Whitefish, Minneapolis, Sioux Falls,
Bozeman, Missoula, Springfield, Skye, Edinburgh, Honolulu, Kauai, Haleakal¯a National Park, Wrangell-St. Elias National Park &
Preserve, Atlanta, Tirana, Corfu, Siena.
""".strip()


def evaluate_direct(prompt, query):
    direct_response = query_llm(prompt + "\n\n" + query, max_tokens=32)
    if ANSWER_TOKEN in direct_response:
        direct_answer = direct_response.split(ANSWER_TOKEN)[1].strip()
    else:
        direct_answer = direct_response
    print_result("Direct", direct_response, direct_answer)


# evaluate_direct(direct_prompt, query)

def evaluate_cot(prompt, query):
    cot_response = query_llm(prompt + "\n\n" + query, max_tokens=3072)
    if ANSWER_TOKEN in cot_response:
        cot_answer = cot_response.split(ANSWER_TOKEN)[1].strip()
    else:
        cot_answer = cot_response
    print_result("CoT", cot_response, cot_answer)


def evaluate_coc(prompt, query):
    global errors
    global error_lineno
    global lines
    global trace_lines
    global last_state
    coc_response = query_llm(prompt + "\n\n" + query, max_tokens=1024)
    code_to_run = coc_response.split(CODE_START_TOKEN)[1].split(CODE_END_TOKEN)[0].strip()

    answer = None
    max_trials = 20
    # Wrap the code inside the get_answer function call
    code_to_run_temp = code_to_run.split("\n")
    code_to_run = "\n".join(["  " + l for l in code_to_run_temp])
    code_to_run = f"""def get_answer():
{code_to_run}
  return answer
answer = get_answer()"""
    lines = code_to_run.split("\n")
    local_vars = locals()

    for num_trial in range(max_trials):
        if sys.gettrace() is None: sys.settrace(show_trace)
        assert sys.gettrace() is not None, "get trace is None"
        try:
            # answer will be populated by exec function.
            exec(code_to_run, globals(), local_vars)
            coc_answer = local_vars["answer"]
            assert coc_answer is not None
            break
        except Exception as e:
            assert error_lineno is not None
            # Update errors
            line = lines[error_lineno]
            errors[error_lineno + 1] = line

            # Update lines and code_to_run
            num_indent = len(line) - len(line.lstrip())
            lines[error_lineno] = " " * 2 + lines[error_lineno]
            lines.insert(error_lineno, " " * num_indent + "try:")
            lines.insert(error_lineno + 2, " " * num_indent + "except:")
            lines.insert(error_lineno + 3, " " * (num_indent + 2) + "pass")
            code_to_run = "\n".join(lines)

            # Reset error_lineno and trace_lines
            error_lineno = None
            trace_lines = []
            last_state = None

    print_result('CoC', coc_response, coc_answer)


# This cell runs for roughly one minute.
NUM_PLACES = 188
progress_bar = tqdm(total=NUM_PLACES)
evaluate_coc(coc_prompt, query)
progress_bar.close()
