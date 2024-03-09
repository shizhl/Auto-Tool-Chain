import requests

def search(q,k=3,mode='colbert',corpus='hotpot'):
    """
    :param q: the input query to retrieve
    :param k: top-k document
    :param mode: retrieval method
    :param corpus: retrieve document from which corpus, i.e., psgs or hotpot
    :return:
    """
    docs=None
    if mode=='google':
        # return search_google(q,k)
        raise NotImplemented
    elif mode=='bm25':
        if corpus=='hotpot':
            url= 'http://10.102.32.111:9999/search/bm25/hotpot?query=' + q+ f'&k={k}'
        else:
            url = 'http://10.102.32.111:9999/search/bm25/psgs?query=' + q + f'&k={k}'
        response = requests.get(url)
        docs =response.json()
    elif mode=='colbert':
        url = 'http://10.102.33.19:8002/search/colbert?query=' + q+ f'&k=10&corpus={corpus}'
        response = requests.get(url)
        docs = [line['text'] for line in response.json()['topk']]
    elif mode=='contriever':
        url = 'http://10.102.32.111:8803/api/search?query=' + q + f'&k={k}'
        response = requests.get(url)
        docs = [line['text'] for line in response.json()['topk']]
    return docs

res=search(q=' I need to get for Name of the British journal of literary essays',k=3,mode='colbert',corpus='hotpot')
print(res)


