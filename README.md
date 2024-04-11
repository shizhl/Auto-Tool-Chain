# ProTooling

Empowering the external tools via programming.

Link to our new version and dataset: [NovelTools](https://github.com/shizhl/NovelTools)

# News
[2023/4/11] Add the demo and release part of our dataset.

[2023/3/11] The first version of `ProTooling` is released!



# Overall

## Use provided tools

We provide the `quick start` demo to illustrate our method. You can run the `run.py` to empower the LLMs-based agent to call multiple tools to get the answer. 

Please note that you should register for the API key (see the **Environment** for details)

```python
run run.py
```

## Generalize to your tools

Since the tools in the world scenarios typically lack detailed tool documentation, especially the documentation about the execution results, we propose a `probing` method to automatically get the execution template of arbitrary tools.

You can find the details in `./probing/probing.py`.

```python
run probing.py
```

# Environment

1. register the API key for Rapid, TMDB, and Spotify platform
2. add your key to the environment


# Dataset

We build a new evaluation benchmark which evaluates the tool-use capability of LLMs-based on complex tasks. Each example in our benchmark involves more API call, complex logic reasoning (e.g., if, branch, switch), workflow control (e.g., for and while). 
To the best of our knowledge, it is the first benchmark including the tasks involving logic and workflow control. 

# TODO
1. add more details about how to run the code
2. our full evaluation benchmark will be added as soon as possible.

