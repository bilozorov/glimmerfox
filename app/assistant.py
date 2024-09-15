import os
import time
import json

import openai
from openai import OpenAI

from elasticsearch import Elasticsearch

import spacy
import numpy as np


def print_log(message):
    print(message, flush=True)


# Initialize Elasticsearch client
# es_client = Elasticsearch([f"http://{os.environ.get('ELASTICSEARCH_HOST', 'localhost')}:{os.environ.get('ELASTICSEARCH_PORT', '9200')}"])
# es_client = Elasticsearch('http://localhost:9200') 
es_client = Elasticsearch('http://elasticsearch:9200') 
index_name='documents'
try:
    result = es_client.count(index=index_name)
    print_log(f"ES Checking = Document count in {index_name}: {result['count']}")
except Exception as e:
    print_log(f"ES Checking = Error: {str(e)}")

# Set up OpenAI API with default key
DEFAULT_API_KEY = os.environ.get("OPENAI_API_KEY")


nlp = spacy.load('en_core_web_sm')


def validate_api_key(api_key):
    try:
        # Try to use the API key to list models (a simple API call)
        openai.Model.list(api_key=api_key)
        return True
    except:
        return False
    

def elastic_search_text(query, index_name="documents"):
    search_query = {
        "size": 5,
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query,
                        "fields": ["question^3", "answer"],
                        "type": "best_fields",
                    }   
                },
            }
        }
    }

    response = es_client.search(index=index_name, body=search_query)
    return [hit["_source"] for hit in response["hits"]["hits"]]


def get_vector(query):
    doc = nlp(query)
    tokens = [token.lemma_ for token in doc]
    text = ' '.join(tokens)
    doc_lemmatized = nlp(text)
    vector = np.mean([token.vector for token in doc_lemmatized], axis=0).tolist()
    return vector



def elastic_search_knn(query, index_name="documents", field='embedding'):
                
    vector = get_vector(query)

    search_body = {
        "knn": {
            "field": "embedding",
            "query_vector": vector,
            "k": 5,
            "num_candidates": 10000,
        },
        "size": 5,
        "_source": ['document_id', 'question', 'answer'],
    }

    es_results = es_client.search(index=index_name, body=search_body)

    return [hit["_source"] for hit in es_results["hits"]["hits"]]


def elastic_search_hybrid(query, index_name="documents", field='embedding'):
    vector = get_vector(query)
    
    knn_query = {
        "field": "embedding",
        "query_vector": vector,
        "k": 5,
        "num_candidates": 10000,
        "boost": 0.5,
    }

    keyword_query = {
        "bool": {
            "must": {
                "multi_match": {
                    "query": query,
                    "fields": ["question^3", "answer"],
                    "type": "best_fields",
                    "boost": 0.5,
                }   
            },
        }
    }

    es_results = es_client.search(
        index=index_name,
        query=keyword_query,
        knn=knn_query,
        size=5
    )

    return [hit["_source"] for hit in es_results["hits"]["hits"]]




def build_prompt(query, search_results):
    prompt_template = """
You are an expert in synthetic biology and ecology with deep knowledge about the Glimmerfox (Vulpilynx chameleontis). Answer the QUESTION based strictly on the CONTEXT provided from the knowledge base. Do not add any information that is not in the CONTEXT.

QUESTION: {question}

CONTEXT: 
{context}
""".strip()

    context = "\n\n".join(
        [
            f"question: {doc['question']}\nanswer: {doc['answer']}"
            for doc in search_results
        ]
    )
    return prompt_template.format(question=query, context=context).strip()


def llm(prompt, model_choice, api_key):
    client = OpenAI(api_key=api_key)
    start_time = time.time()
    response = client.chat.completions.create(
        model=model_choice.split('/')[-1],
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response.choices[0].message.content
    tokens = {
        'input_tokens': response.usage.prompt_tokens,
        'output_tokens': response.usage.completion_tokens,
        'total_tokens': response.usage.total_tokens
    }    
    end_time = time.time()
    response_time = end_time - start_time
    
    return answer, tokens, response_time


def evaluate_relevance(question, answer, api_key):
    # client = OpenAI(api_key=api_key)
    prompt_template_evaluation = """
    You are an expert evaluator for a Retrieval-Augmented Generation (RAG) system.
    Your task is to analyze the relevance of the generated answer to the given question.
    Based on the relevance of the generated answer, you will classify it
    as "NON_RELEVANT", "PARTLY_RELEVANT", or "RELEVANT".

    Here is the data for evaluation:

    Question: {question}
    Generated Answer: {answer}

    Please analyze the content and context of the generated answer in relation to the question
    and provide your evaluation in parsable JSON without using code blocks:

    {{
      "Relevance": "NON_RELEVANT" | "PARTLY_RELEVANT" | "RELEVANT",
      "Explanation": "[Provide a brief explanation for your evaluation]"
    }}
    """.strip()

    prompt = prompt_template_evaluation.format(question=question, answer=answer)
    evaluation, tokens, _ = llm(prompt, 'openai/gpt-4o-mini', api_key)
    
    try:
        json_eval = json.loads(evaluation)
        return json_eval['Relevance'], json_eval['Explanation'], tokens
    except json.JSONDecodeError:
        return "UNKNOWN", "Failed to parse evaluation", tokens


def calculate_openai_cost(model_choice, tokens):
    openai_cost = 0

    if model_choice in ['openai/gpt-4o', 'openai/gpt-4o-mini']:
        openai_cost = (tokens['input_tokens'] * 0.000150 + tokens['output_tokens'] * 0.000600) / 1000

    return openai_cost


def compute_rrf(rank, k=60):
    """ Our own implementation of the relevance score """
    return 1 / (k + rank)


def elastic_search_hybrid_rff_free(query, index_name="documents", field='embedding', k=60):
    vector = get_vector(query)
    
    knn_query = {
        "field": "embedding",
        "query_vector": vector,
        "k": 5,
        "num_candidates": 10000,
        "boost": 0.5,
    }

    knn_results = es_client.search(
        index=index_name, 
        body={
            "knn": knn_query, 
            "size": 10
        }
    )['hits']['hits']

    # keyword results

    keyword_query = {
        "bool": {
            "must": {
                "multi_match": {
                    "query": query,
                    "fields": ["question^3", "answer"],
                    "type": "best_fields",
                    "boost": 0.5,
                }   
            },
        }
    }

    keyword_results = es_client.search(
        index=index_name, 
        body={
            "query": keyword_query, 
            "size": 10
        }
    )['hits']['hits']

    

    search_query = {
        "knn": knn_query,
        "query": keyword_query,
        "size": 5,
        "rank": {
            "rrf": {}
        },
        # "_source": ["question", "answer", "document_idid"]
    }

    rrf_scores = {}
    # Calculate RRF using vector search results
    for rank, hit in enumerate(knn_results):
        doc_id = hit['_id']
        rrf_scores[doc_id] = compute_rrf(rank + 1, k)

    # Adding keyword search result scores
    for rank, hit in enumerate(keyword_results):
        doc_id = hit['_id']
        if doc_id in rrf_scores:
            rrf_scores[doc_id] += compute_rrf(rank + 1, k)
        else:
            rrf_scores[doc_id] = compute_rrf(rank + 1, k)

    # Sort RRF scores in descending order
    reranked_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Get top-K documents by the score
    final_results = []
    for doc_id, score in reranked_docs[:5]:
        doc = es_client.get(index=index_name, id=doc_id)
        final_results.append(doc['_source'])
    
    return final_results


def elastic_search_advanced(query, api_key, index_name="documents", field='embedding', k=60, ):
    prompt_template_rewriting = """
You are an expert at query expansion to generate a paraphrasing of a question.
I can't retrieval relevant information from the knowledge base by using user's question directly.     
You need to expand or paraphrase user's question by multiple ways such as using synonyms words/phrase, 
writing the abbreviation in its entirety, adding some extra descriptions or explanations, 
changing the way of expression. 
And return 5 versions of question.

Here's the data for the process:

User's question: {question}

Please analyze the question and provide your additional questions in parsable JSON without using code blocks:

{{
    "question 1": "provided by you question 1",
    "question 2": "provided by you question 2",
    "question 3": "provided by you question 3",
    "question 4": "provided by you question 4",
    "question 5": "provided by you question 5",
}}
""".strip()
    
    prompt_rewriting = prompt_template_rewriting.format(question=query)
    answer, tokens, response_time = llm(prompt_rewriting, 'openai/gpt-4o-mini', api_key=api_key)

    try:
        answer_json = json.loads(answer)
    except json.JSONDecodeError:
        print("Failed to parse questions by rewriting")

    queries = list(answer_json.values())
    queries.append(query)


    search_results = []
    for q in queries:
        r = elastic_search_hybrid_rff_free(query=q)
        search_results += r

    return search_results


def get_answer(query, model_choice, search_type, api_key):
    # if search_type == 'Vector':
    #     vector = model.encode(query)
    #     search_results = elastic_search_knn('question_text_vector', vector, course)
    # else:
    #     search_results = elastic_search_text(query, course)
    if search_type == 'text':
        search_results = elastic_search_text(query)
    elif search_type == 'vector':
        search_results = elastic_search_knn(query)
    elif search_type == 'hybrid':
        search_results = elastic_search_hybrid(query)
    elif search_type == 'advanced':
        search_results = elastic_search_advanced(query, api_key)

    prompt = build_prompt(query, search_results)
    answer, tokens, response_time = llm(prompt, model_choice, api_key)
    
    relevance, explanation, eval_tokens = evaluate_relevance(query, answer, api_key)

    openai_cost = calculate_openai_cost(model_choice, tokens)
 
    return {
        'answer': answer,
        'response_time': response_time,
        'relevance': relevance,
        'relevance_explanation': explanation,
        'model_used': model_choice,
        'input_tokens': tokens['input_tokens'],
        'output_tokens': tokens['output_tokens'],
        'total_tokens': tokens['total_tokens'],
        'eval_input_tokens': eval_tokens['input_tokens'],
        'eval_output_tokens': eval_tokens['output_tokens'],
        'eval_total_tokens': eval_tokens['total_tokens'],
        'openai_cost': openai_cost
    }