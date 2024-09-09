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

def print_log(message):
    print(message, flush=True)

DEFAULT_API_KEY = os.environ.get("OPENAI_API_KEY")

def save_feedback(*args, **kwargs):
    pass

def save_conversation(*args, **kwargs):
    pass

def get_recent_conversations(*args, **kwargs):
    pass

def get_feedback_stats(*args, **kwargs):
    pass


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
    model_choice = st.sidebar.selectbox("Select Model", ["openai/gpt-4o-mini", "openai/gpt-3.5-turbo"])
    print_log(f"User selected model: {model_choice}")

    # Search type  selection
    search_type = st.sidebar.selectbox("Select Search type", ["text", "vector"])
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