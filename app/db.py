import os
import uuid
import psycopg2
from psycopg2 import OperationalError, DatabaseError
from psycopg2.extras import DictCursor
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import random
import time

tz = ZoneInfo("Europe/Berlin")


def get_db_connection(localhost=False):

    if localhost:
        host=os.getenv("POSTGRES_HOST_LOCAL", "localhost")
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


# def init_db(localhost=False):
#     conn = get_db_connection(localhost)
#     try:
#         with conn.cursor() as cur:
#             cur.execute("DROP TABLE IF EXISTS feedback")
#             cur.execute("DROP TABLE IF EXISTS conversations")

#             cur.execute("""
#                 CREATE TABLE conversations (
#                     id TEXT PRIMARY KEY,
#                     question TEXT NOT NULL,
#                     answer TEXT NOT NULL,
#                     course TEXT NOT NULL,
#                     model_used TEXT NOT NULL,
#                     response_time FLOAT NOT NULL,
#                     relevance TEXT NOT NULL,
#                     relevance_explanation TEXT NOT NULL,
#                     prompt_tokens INTEGER NOT NULL,
#                     completion_tokens INTEGER NOT NULL,
#                     total_tokens INTEGER NOT NULL,
#                     eval_prompt_tokens INTEGER NOT NULL,
#                     eval_completion_tokens INTEGER NOT NULL,
#                     eval_total_tokens INTEGER NOT NULL,
#                     openai_cost FLOAT NOT NULL,
#                     timestamp TIMESTAMP WITH TIME ZONE NOT NULL
#                 )
#             """)
#             cur.execute("""
#                 CREATE TABLE feedback (
#                     id SERIAL PRIMARY KEY,
#                     conversation_id TEXT REFERENCES conversations(id),
#                     feedback INTEGER NOT NULL,
#                     timestamp TIMESTAMP WITH TIME ZONE NOT NULL
#                 )
#             """)
#         conn.commit()
#     finally:
#         conn.close()


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



def save_feedback(query_id, feedback, timestamp=None, localhost=False):
    if timestamp is None:
        timestamp = datetime.now(tz)

    conn = get_db_connection(localhost)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (query_id, feedback, timestamp) VALUES (%s, %s, COALESCE(%s, CURRENT_TIMESTAMP))",
                (query_id, feedback, timestamp),
            )
        conn.commit()
    finally:
        conn.close()


# def get_recent_conversations(limit=5, relevance=None):
#     conn = get_db_connection()
#     try:
#         with conn.cursor(cursor_factory=DictCursor) as cur:
#             query = """
#                 SELECT c.*, f.feedback
#                 FROM conversations c
#                 LEFT JOIN feedback f ON c.id = f.conversation_id
#             """
#             if relevance:
#                 query += f" WHERE c.relevance = '{relevance}'"
#             query += " ORDER BY c.timestamp DESC LIMIT %s"

#             cur.execute(query, (limit,))
#             return cur.fetchall()
#     finally:
#         conn.close()


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
    finally:
        conn.close()
