from model.engine import *


def test_probing():
    env = PythonExecNet()

    cnt = 0
    data = load_data('/Users/shizhl/Paper2024/ProTool/dataset/tmdb.pseudo_spec.json')
    # data = load_data('/Users/shizhl/Paper2024/ProTool/dataset/spotify.pseudo_spec.json')
    for line in data[2:]:
        print('*' * 50)
        print(line['name'])
        pattern = r"```python(.*?)```"
        print(line['test'].split('\n')[0])
        matches = re.findall(pattern, line['test'], re.DOTALL)
        example, state = env.run(matches[0])
        if state == False:
            cnt += 0
            line['example'] = None
            line['_responses_json'] = None
            line['_responses_yaml'] = None
        else:
            cnt += 1
            line['example'] = example
            line['_responses_json'] = simplify_json(example)
            line['_responses_yaml'] = '\n'.join(get_yaml(example, 'execution result'))
        print(example)
    print(cnt)
    # write_file(data,'/Users/shizhl/Paper2024/ProTool/dataset/tmdb.pseudo_spec.json')


test_probing()