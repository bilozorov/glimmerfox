import streamlit as st
import os
import requests
from elasticsearch import Elasticsearch
import openai
from openai import OpenAI
import time
import uuid
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2 import OperationalError, DatabaseError
from psycopg2.extras import DictCursor
from zoneinfo import ZoneInfo

from assistant import get_answer
# from db import save_conversation, save_feedback, get_recent_conversations, get_feedback_stats

IS_LOCALHOST=False


import dotenv
dotenv.load_dotenv()

def print_log(message):
    print(message, flush=True)

DEFAULT_API_KEY = os.environ.get("OPENAI_API_KEY")

TZ_INFO = os.getenv("TZ", "Europe/Sofia")
tz = ZoneInfo(TZ_INFO)


def get_db_connection(localhost=False):

    if IS_LOCALHOST:
        # host=os.getenv("POSTGRES_HOST_LOCAL", "localhost")
        host = "localhost"
    else:
        host=os.getenv("POSTGRES_HOST", "postgres")
    try:
        connection = psycopg2.connect(
            host=host,
            database=os.getenv("POSTGRES_DB", "glimmerfox_db"),
            user=os.getenv("POSTGRES_USER", "your_username"),
            password=os.getenv("POSTGRES_PASSWORD", "your_password"),
        )
        return connection
    except OperationalError as e:
        print(f"Error: Could not connect to the PostgreSQL database.\nDetails: {e}")
        return None


def calculate_openai_cost(model_choice, tokens):
    openai_cost = 0

    if model_choice in ['openai/gpt-4o', 'openai/gpt-4o-mini']:
        openai_cost = (tokens['input_tokens'] * 0.000150 + tokens['output_tokens'] * 0.000600) / 1000

    return openai_cost


def save_feedback(query_id, feedback, timestamp=None, localhost=False):
    if timestamp is None:
        timestamp = datetime.now(tz)

    conn = get_db_connection(localhost=localhost)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (query_id, feedback, timestamp) VALUES (%s, %s, COALESCE(%s, CURRENT_TIMESTAMP))",
                (query_id, feedback, timestamp),
            )
        conn.commit()
    except Exception as e:
        # Handle the exception
        print(f"An error occurred: {e}")
    finally:
        conn.close()


def save_query(query_id, question, answer_data, timestamp=None, localhost=False):
    # change save_conversation -> save_query

    if timestamp is None:
        timestamp = datetime.now(tz)

    conn = get_db_connection(localhost=localhost)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO queries 
                (id, question, answer, model_used, response_time, relevance, 
                relevance_explanation, input_tokens, output_tokens, total_tokens, 
                eval_input_tokens, eval_output_tokens, eval_total_tokens, openai_cost, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    query_id,
                    question,
                    answer_data["answer"],
                    answer_data["model_used"],
                    answer_data["response_time"],
                    answer_data["relevance"],
                    answer_data["relevance_explanation"],
                    answer_data["input_tokens"],
                    answer_data["output_tokens"],
                    answer_data["total_tokens"],
                    answer_data["eval_input_tokens"],
                    answer_data["eval_output_tokens"],
                    answer_data["eval_total_tokens"],
                    answer_data["openai_cost"],
                    timestamp
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_recent_conversations(*args, **kwargs):
    pass

def get_feedback_stats(*args, **kwargs):
    pass


def main():

    query_id= str(uuid.uuid4())

    openai_api_key = DEFAULT_API_KEY
    st.set_page_config(page_title="Glimmerfox Advanced RAG Q&A System", layout="wide")

    st.title("Glimmerfox Advanced RAG Q&A System")

    # Project description
    st.markdown("""
    This is a Advanced RAG (Retrieval-Augmented Generation) Q&A System that uses Elasticsearch for retrieval and OpenAI's models for answer generation.
    """)
    # - **Without Valid API Key**: You can use the app with a 100-character query limit. Answers will be generated using a simple method.
    # - **With Valid API Key**: Full access to the system, using OpenAI's powerful models for answer generation.
    

    # Sidebar
    st.sidebar.header("Settings")
    
    # Model selection
    model_choice = st.sidebar.selectbox("Select Model", ["openai/gpt-4o-mini", "openai/gpt-3.5-turbo"])
    # model_choice = st.sidebar.selectbox("Select Model", ["openai/gpt-4o-mini"])
    print_log(f"User selected model: {model_choice}")

    # Search type  selection
    search_type = st.sidebar.selectbox("Select Search type", ["text", "vector", "hybrid", "advanced"])
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
            
            print_log(f"Getting answer from assistant using {model_choice} model")
            start_time = time.time()
            
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
            
                # Generate answer
                answer_data = get_answer(user_query, model_choice, search_type, openai_api_key)
                end_time = time.time()
                print_log(f"Answer received in {end_time - start_time:.2f} seconds")
                
                full_response = f"""
                    {answer_data['answer']}
                        
                    - **Response time**: {answer_data['response_time']:.2f} seconds
                    - **Relevance**: {answer_data['relevance']}
                    - **Model used**: {answer_data['model_used']}
                    - **Total tokens**: {answer_data['total_tokens']}
                    - **OpenAI cost**: ${answer_data['openai_cost']:.4f}
                """             
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                print('IS_LOCALHOST = ', IS_LOCALHOST)
                save_query(query_id, user_query, answer_data, timestamp=None, localhost=IS_LOCALHOST)
                        
            # Feedback buttons
            st.write("Was this response helpful?")
            col1, col2, _ = st.columns([1, 1, 8])
            with col1:
                if st.button("👍 Yes", key=f"yes_{query_id}"):
                    print_log(f"Button 👍 Yes pressed")
                    save_feedback(query_id, 0, localhost=IS_LOCALHOST)
            with col2:
                if st.button("👎 No", key=f"no_{query_id}"):
                    print_log(f"Button 👎 No pressed")
                    save_feedback(query_id, 0, localhost=IS_LOCALHOST)


if __name__ == "__main__":
    print('-------------------------- main')
    main()