import streamlit as st
import os
import requests
from elasticsearch import Elasticsearch
import openai
from openai import OpenAI
import time
import uuid

from assistant import get_answer
# from db import save_conversation, save_feedback, get_recent_conversations, get_feedback_stats

import dotenv
dotenv.load_dotenv()
print('*****************')

def print_log(message):
    print(message, flush=True)

def check_count_elasticsearch(index_name, es_client):
    try:
        result = es_client.count(index=index_name)
        print_log(f"ES Checking = Document count in {index_name}: {result['count']}")
    except Exception as e:
        print_log(f"ES Checking = Error: {str(e)}")


# Initialize Elasticsearch client
# es_client = Elasticsearch([f"http://{os.environ.get('ELASTICSEARCH_HOST', 'localhost')}:{os.environ.get('ELASTICSEARCH_PORT', '9200')}"])
es_client = Elasticsearch('http://localhost:9200') 

index_name='documents'
try:
    result = es_client.count(index=index_name)
    print_log(f"ES Checking = Document count in {index_name}: {result['count']}")
except Exception as e:
    print_log(f"ES Checking = Error: {str(e)}")



# Set up OpenAI API with default key
DEFAULT_API_KEY = os.environ.get("OPENAI_API_KEY")


def validate_api_key(api_key):
    try:
        # Try to use the API key to list models (a simple API call)
        openai.Model.list(api_key=api_key)
        return True
    except:
        return False
    

def elastic_search_text(query, k=5):
    search_query = {
        "size": k,
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
    
    result_docs = []
    
    for hit in response['hits']['hits']:
        result_docs.append(hit['_source'])
    
    return result_docs


def get_vector(query):
    doc = nlp(query)
    tokens = [token.lemma_ for token in doc]
    text = ' '.join(tokens)
    doc_lemmatized = nlp(text)
    vector = np.mean([token.vector for token in doc_lemmatized], axis=0).tolist()
    return vector


def elastic_search_knn(query, field='embedding', k=5):

    vector = get_vector(query)

    search_body = {
        "knn": {
            "field": "embedding",
            "query_vector": vector,
            "k": k,
            "num_candidates": 100
        },
        "size": 6,
        "_source": ['document_id', 'question', 'answer'],
    }

    es_results = es_client.search(
        index=index_name,
        body=search_body
    )
    
    result_docs = []
    
    for hit in es_results['hits']['hits']:
        result_docs.append(hit['_source'])

    return result_docs


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


def save_feedback(*args, **kwargs):
    pass

def save_conversation(*args, **kwargs):
    pass

def get_recent_conversations(*args, **kwargs):
    pass

def get_feedback_stats(*args, **kwargs):
    pass


def llm(prompt, api_key, model):
    client = OpenAI(api_key=api_key)
    # response = client.chat.completions.create(
    #     model=model,
    #     messages=[{"role": "user", "content": prompt}]
    # )
    
    # return response.choices[0].message.content

    start_time = time.time()
    response = client.chat.completions.create(
        model=model,
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


def evaluate_relevance(question, answer):
    prompt_template = """
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

    prompt = prompt_template.format(question=question, answer=answer)
    evaluation, tokens, _ = llm(prompt, 'openai/gpt-4o-mini')
    
    try:
        json_eval = json.loads(evaluation)
        return json_eval['Relevance'], json_eval['Explanation'], tokens
    except json.JSONDecodeError:
        return "UNKNOWN", "Failed to parse evaluation", tokens


def rag(query, search_type, model, api_key, *args, **kwargs):
    if search_type == 'Text':
        search_results = elastic_search_text(query)
    elif search_type == 'Vector':
        search_results = elastic_search_knn(query)

    prompt = build_prompt(query, search_results)
    answer = llm(prompt, api_key, model)
    return answer



def get_answer(query, course, model_choice, search_type):
    if search_type == 'text':
        search_results = elastic_search_text(query)
    elif search_type == 'vector':
        search_results = elastic_search_knn(query)

    prompt = build_prompt(query, search_results)
    answer, tokens, response_time = llm(prompt, model_choice)
    
    relevance, explanation, eval_tokens = evaluate_relevance(query, answer)

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


def main():
    openai_api_key = DEFAULT_API_KEY
    st.set_page_config(page_title="RAG Q&A System", layout="wide")

    st.title("RAG Q&A System")

    # Project description
    st.markdown("""
    This is a RAG (Retrieval-Augmented Generation) Q&A System that uses Elasticsearch for retrieval and OpenAI's models for answer generation.
    
    - **Without Valid API Key**: You can use the app with a 100-character query limit. Answers will be generated using a simple method.
    - **With Valid API Key**: Full access to the system, using OpenAI's powerful models for answer generation.
    """)

    # Sidebar
    st.sidebar.header("Settings")
    
    # Model selection
    model = st.sidebar.selectbox("Select Model", ["openai/gpt-4o-mini", "openai/gpt-3.5-turbo"])
    print_log(f"User selected model: {model}")

    # Search type  selection
    search_type = st.sidebar.selectbox("Select Search type", ["text", "tector"])
    print_log(f"User selected search type: {search_type}")
    
    # API Key input and apply button
    # st.sidebar.markdown("---")
    # st.sidebar.subheader("API Key")
    # user_api_key = st.sidebar.text_input("Enter OpenAI API Key (optional)", type="password")
    # if st.sidebar.button("Apply API Key"):
    #     if user_api_key:
    #         if validate_api_key(user_api_key):
    #             st.sidebar.success("API Key applied successfully!")
    #             openai_api_key = user_api_key
    #         else:
    #             st.sidebar.error("Invalid API Key. Using default key with limited functionality.")
    #             openai_api_key = DEFAULT_API_KEY
    #     else:
    #         st.sidebar.warning("No API Key provided. Using default key with limited functionality.")
    #         openai_api_key = DEFAULT_API_KEY

    

    # Main chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input("What is your question?"):        
        if openai_api_key == DEFAULT_API_KEY and len(user_query) > 100:
            user_query = user_query[:100]

        query_id= str(uuid.uuid4())
        print_log(f"New query started with ID: {query_id}")
        print_log(f"User asked: '{user_query}'")
        
        with st.spinner('Processing...'):
            
            print_log(f"Getting answer from assistant using {model} model")
            start_time = time.time()
            
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
            
                # Generate answer
                answer_data = rag(user_query, search_type, model, openai_api_key)
                end_time = time.time()
                print_log(f"Answer received in {end_time - start_time:.2f} seconds")

                message_placeholder.markdown(answer_data)

                # full_response = answer_data

                # Simulate stream of response with milliseconds delay
                # print_log(f"answer_data['answer']={answer_data['answer']}")
                # for chunk in answer_data['answer'].split():
                #     full_response += chunk + " "
                #     message_placeholder.markdown(full_response + "▌")
                # message_placeholder.markdown(full_response)
                
                # full_response += f"\n\nResponse time: {answer_data['response_time']:.2f} seconds"
                # full_response += f"\nRelevance: {answer_data['relevance']}"
                # full_response += f"\nModel used: {answer_data['model_used']}"
                # full_response += f"\nTotal tokens: {answer_data['total_tokens']}"
                # if answer_data['openai_cost'] > 0:
                #     full_response += f"\nOpenAI cost: ${answer_data['openai_cost']:.4f}"

                # message_placeholder.markdown(full_response)
                


                st.session_state.messages.append({"role": "assistant", "content": full_response})

            # Feedback buttons
            st.write("Was this response helpful?")
            col1, col2, _ = st.columns([1, 1, 8])
            with col1:
                if st.button("👍 Yes", key=f"yes_{query_id}"):
                    save_feedback(True, query_id)
            with col2:
                if st.button("👎 No", key=f"no_{query_id}"):
                    save_feedback(False, query_id)


if __name__ == "__main__":
    print('--------------------------')
    main()