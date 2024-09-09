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
es_client = Elasticsearch([f"http://{os.environ.get('ELASTICSEARCH_HOST', 'localhost')}:{os.environ.get('ELASTICSEARCH_PORT', '9200')}"])
# es_client = Elasticsearch('http://localhost:9200') 
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
                        "type": "best_fields"
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
            "num_candidates": 100
        },
        "size": 5,
        "_source": ['document_id', 'question', 'answer'],
    }

    es_results = es_client.search(index=index_name, body=search_body)

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
        'prompt_tokens': response.usage.prompt_tokens,
        'completion_tokens': response.usage.completion_tokens,
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

    if model_choice == 'openai/gpt-3.5-turbo':
        openai_cost = (tokens['prompt_tokens'] * 0.0015 + tokens['completion_tokens'] * 0.002) / 1000
    elif model_choice in ['openai/gpt-4o', 'openai/gpt-4o-mini']:
        openai_cost = (tokens['prompt_tokens'] * 0.03 + tokens['completion_tokens'] * 0.06) / 1000

    return openai_cost


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
        'prompt_tokens': tokens['prompt_tokens'],
        'completion_tokens': tokens['completion_tokens'],
        'total_tokens': tokens['total_tokens'],
        'eval_prompt_tokens': eval_tokens['prompt_tokens'],
        'eval_completion_tokens': eval_tokens['completion_tokens'],
        'eval_total_tokens': eval_tokens['total_tokens'],
        'openai_cost': openai_cost
    }