import random
import requests


def search(q, k=3, mode='colbert', corpus='hotpot'):
    """
    :param q: the input query to retrieve
    :param k: top-k document
    :param mode: retrieval method
    :param corpus: retrieve document from which corpus, i.e., psgs or hotpot
    :return:
    """
    docs = None
    if mode == 'google':
        # return search_google(q,k)
        raise NotImplemented
    elif mode == 'bm25':
        if corpus == 'hotpot':
            url = 'http://10.102.33.19:8002/search/bm25/hotpot?query=' + q + f'&k={k}'
        else:
            url = 'http://10.102.33.19:8002/search/bm25/psgs?query=' + q + f'&k={k}'
        response = requests.get(url)
        docs = response.json()
    elif mode == 'colbert':
        url = 'http://10.102.33.19:8002/search/colbert?query=' + q + f'&k={k}&corpus={corpus}'
        response = requests.get(url)
        docs = [line['text'] for line in response.json()['topk']]
    elif mode == 'contriever':
        url = 'http://10.102.33.19:8002/api/search?query=' + q + f'&k={k}'
        response = requests.get(url)
        docs = [line['text'] for line in response.json()['topk']]
    return docs


class Knowledge:

    @staticmethod
    def get_knowledge(example, mode='colbert', query='', corpus='hotpot', k=10):
        """

        :param example: dataset sample
        :param mode: oracle: only ground truth, simulation: ground truth + noise, bm25/colbert: search from corpus
        :return: list[document]
        """
        if mode != 'oracle':
            knowledge = search(q=example['query'], mode=mode, k=k, corpus=corpus)
            return knowledge
        else:
            if example['dataset'] == 'hotpot':
                return Knowledge.get_knowledge_hotpot(example, mode=mode)
            if example['dataset'] == 'multihotpot':
                return Knowledge.get_knowledge_multi_hotpot_qa(example, mode=mode)
            if example['dataset'] == 'bamgoolge':
                return Knowledge.get_knowledge_bamgoolge(example, mode=mode)
            if example['dataset'] == 'hf-wics-strategy':
                return Knowledge.get_knowledge_strategy(example, mode=mode)
            if example['dataset'] == 'musique':
                return Knowledge.get_knowledge_musique(example, mode=mode)
            if example['dataset']=='nq_dev_psgs_w100':
                return [line['text'] for line in example['positive_ctxs'][:k]]


    @staticmethod
    def get_knowledge_bamgoolge(example, mode='oracle'):
        return ''

    @staticmethod
    def get_knowledge_strategy(example, mode='oracle'):
        if mode == 'oracle':
            knowledge = example['facts']
        elif mode == 'simulation':
            # ground truth + noise
            knowledge = example['facts'] + example['noise']
            random.shuffle(knowledge)
        else:
            raise NotImplementedError
        return knowledge

    @staticmethod
    def get_knowledge_musique(example, mode='oracle'):
        # ground truth
        # knowledge=[line['paragraph_text'] for line in example['paragraphs'] if line['is_supporting']==True]
        # ground truth + noise
        knowledge = [line['paragraph_text'] for line in example['paragraphs']]
        return knowledge

    @staticmethod
    def get_knowledge_hotpot(example, mode='oracle'):
        if mode == 'simulation':
            # ground truth + noise
            knowledge = [t + ' ### ' + ' '.join(s) for t, s in
                         zip(example['context']['title'], example['context']['sentences'])]
        else:  # ground truth
            knowledge = []
            doc_id = [example['context']['title'].index(t) for t in example['supporting_facts']['title']]
            for i in doc_id:
                title = example['context']['title'][i].replace('"', '')
                content = ' '.join(example['context']['sentences'][i]).replace('"', '')
                knowledge.append(f"Title: {title} Text: {content})")

            knowledge = list(set(knowledge))

        return knowledge

    @staticmethod
    def get_knowledge_multi_hotpot_qa(example, mode='oracle'):
        # ground truth
        knowledge = []
        for t in example['supporting_facts']:
            for e in example['context']:
                if e[0] == t[0]:
                    knowledge.append(' '.join(e[1]))
        knowledge = list(set(knowledge))
        # knowledge = [' '.join(line[-1]) for line in example['context']]
        return knowledge


# for line in range(100):
#     res = search(q=' I need to get for Name of the British journal of literary essays', k=3, mode='colbert', corpus='hotpot')
#     print(res)