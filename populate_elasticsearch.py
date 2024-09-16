import requests
import time
import sys
import os
import json
import uuid
import psycopg2
from psycopg2 import OperationalError, DatabaseError
from psycopg2.extras import DictCursor
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import random
from dotenv import load_dotenv

is_localhost = False

########################################################
####### Functions for checking services
########################################################

def is_elasticsearch_ready(url="http://elasticsearch:9200"):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Elasticsearch service: {e}")
        return False

def is_mage_ready(url="http://magic:6789"):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Mage service: {e}")
        return False
    
def is_grafana_ready(url="http://grafana:3000"):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Grafana service: {e}")
        return False


def wait_for_services(max_retries=12):  # 12 * 5 seconds = 1 minute total wait time
    retries = 0
    while retries < max_retries:
        if is_elasticsearch_ready() and is_mage_ready() and is_grafana_ready():
            print("All  Elasticsearch and Mage and Grafana are ready!")
            return True
        else:
            print(f"Attempt {retries + 1}/{max_retries}: Services not ready. Waiting 5 seconds...")
            time.sleep(5)
            retries += 1
    print("Max retries reached. Services are not ready.")
    return False

########################################################
####### Functions for Mage: run_pipeline_populate_elasticsearch
########################################################

def run_pipeline_populate_elasticsearch():
    """
    populating by our KNWLG.base
    """
    # url = "http://magic:6789/api/pipeline_schedules/5/pipeline_runs/e148d1b8a12c4c65b6fe0b4b703e196f"
    # url = "http://65.109.14.99:6789/api/pipeline_schedules/1/pipeline_runs/e148d1b8a12c4c65b6fe0b4b703e196f"
    url = "http://magic:6789/api/pipeline_schedules/1/pipeline_runs/e148d1b8a12c4c65b6fe0b4b703e196f"
    
    headers = {"Content-Type": "application/json"}

    print('!----> populate_elasticsearch for magic started', flush=True)
    
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        print(f'!----> populate_elasticsearch magic finished with code: {response.status_code}', flush=True)
    except Exception as err:
        print(f"An unexpected error occurred magic: {err}", flush=True)
        print("Error details magic:", sys.exc_info(), flush=True)
    finally:
        print("!----> Script execution completed magic.", flush=True)


########################################################
####### Functions for Postgres: 
########################################################

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


def init_db(localhost=False):
    conn = get_db_connection(localhost=localhost)
    if conn is None:
        print("Database connection failed.")
        return  # Exit the function if the connection failed

    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS feedback")
            cur.execute("DROP TABLE IF EXISTS queries")

            cur.execute("""
                CREATE TABLE queries (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    response_time FLOAT NOT NULL,
                    relevance TEXT NOT NULL,
                    relevance_explanation TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    eval_input_tokens INTEGER NOT NULL,
                    eval_output_tokens INTEGER NOT NULL,
                    eval_total_tokens INTEGER NOT NULL,
                    openai_cost FLOAT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            print("Table 'queries' created successfully.")

            # Create 'feedback' table
            cur.execute("""
                CREATE TABLE feedback (
                    id SERIAL PRIMARY KEY,
                    query_id TEXT REFERENCES queries(id),
                    feedback INTEGER NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            print("Table 'feedback' created successfully.")

        # Commit the changes
        conn.commit()
        print("Database initialization completed successfully.")

        # Verify table creation by querying information_schema
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()
            print("Tables in the database:", tables)

    except DatabaseError as e:
        print(f"Database error: {e}")
        conn.rollback()  # Rollback in case of error

    finally:
        # Ensure the connection is always closed
        if conn:
            conn.close()
            print("Database connection closed.")

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


def clear_tables(localhost=False):
    conn = get_db_connection(localhost=localhost)
    if conn is None:
        print("Database connection failed.")
        return

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback")  # Clear the 'feedback' table first due to foreign key constraint
            cur.execute("DELETE FROM queries")   # Then clear the 'queries' table
        conn.commit()
        print("All entries in 'queries' and 'feedback' tables have been deleted.")
    except psycopg2.DatabaseError as e:
        print(f"Error deleting records from tables: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


def calculate_openai_cost(model_choice, tokens):
    openai_cost = 0

    if model_choice in ['openai/gpt-4o', 'openai/gpt-4o-mini']:
        openai_cost = (tokens['input_tokens'] * 0.000150 + tokens['output_tokens'] * 0.000600) / 1000

    return openai_cost


# Function to generate sample queries
def generate_one_sample_query():
    query_id = str(uuid.uuid4())
    fake_number = datetime.now().timestamp()
    question = f"What is the meaning of life {fake_number}?"
    input_tokens = random.randint(234, 567)
    output_tokens = random.randint(234, 567)
    total_tokens = input_tokens + output_tokens
    eval_input_tokens = random.randint(234, 567)
    eval_output_tokens = random.randint(234, 567)
    eval_total_tokens = eval_input_tokens + eval_output_tokens

    answer_data = {
        "answer": f"The meaning of life {fake_number} is subjective.",
        "model_used": "gpt-4o-mini",
        "response_time": round(random.uniform(0.5, 2.5), 2),  # Random response time between 0.5 and 2.5 seconds
        # "relevance": random.choice(["NON_RELEVANT", "PARTLY_RELEVANT", "RELEVANT"]),
        "relevance": random.choices(["NON_RELEVANT", "PARTLY_RELEVANT", "RELEVANT"], weights=[1, 2, 4], k=1)[0],
        "relevance_explanation": f"The answer is {random.choice(['very', 'somewhat', 'not'])} relevant to the question.",
        "input_tokens": input_tokens,  # Random token count between 10 and 50
        "output_tokens": output_tokens,  # Random token count between 10 and 50
        "total_tokens": total_tokens,  # Random total tokens
        "eval_input_tokens": eval_input_tokens,  # Random token count for evaluation prompt
        "eval_output_tokens": eval_output_tokens,  # Random token count for evaluation completion
        "eval_total_tokens": eval_total_tokens,  # Random evaluation total tokens
        # "openai_cost": round(random.uniform(0.01, 0.1), 4)  # Random cost between 0.01 and 0.1
        "openai_cost": calculate_openai_cost(model_choice='openai/gpt-4o-mini', tokens={'input_tokens': input_tokens+eval_input_tokens, 'output_tokens': output_tokens+eval_output_tokens})
    }
    return (query_id, question, answer_data)


def generate_synthetic_data(start_time, end_time, localhost=False):
    current_time = start_time
    queries_count = 0
    print(f"Starting historical data generation from {start_time} to {end_time}")
    while current_time < end_time:

        query_id, question, answer_data = generate_one_sample_query()
        
        save_query(query_id, question, answer_data, current_time, localhost=localhost)
        # print(
        #     f"Saved query: ID={query_id}, Time={current_time}"
        # )

        if random.random() < 0.7:
            feedback = 1 if random.random() < 0.8 else -1
            save_feedback(
                query_id=query_id, 
                feedback=int(random.choice([True, False])), 
                timestamp=current_time, 
                localhost=localhost)
            # print(
            #     f"Saved feedback for query {query_id}: {'Positive' if feedback > 0 else 'Negative'}"
            # )

        # current_time += timedelta(minutes=random.randint(1, 2))
        # current_time += timedelta(minutes=random.randint(1, 2))
        current_time += timedelta(seconds=random.randint(1, 20))
        queries_count += 1
        if queries_count % 10 == 0:
            print(f"Generated {queries_count} queries so far...")

    print(
        f"Historical data generation complete. Total queries: {queries_count}"
    )

def generate_live_data(localhost=False):
    queries_count = 0
    print("Starting live data generation...")
    while True:
        current_time = datetime.now(tz)
        # current_time = None
        query_id, question, answer_data = generate_one_sample_query()
        save_query(query_id, question, answer_data, current_time, localhost=is_localhost)

        if random.random() < 0.7:
            feedback = 1 if random.random() < 0.8 else -1
            save_feedback(
                query_id=query_id, 
                feedback=int(random.choice([True, False])), 
                timestamp=current_time, 
                localhost=localhost)
        queries_count += 1
        if queries_count % 10 == 0:
            print(f"Generated {queries_count} live queries so far...")

        time.sleep(1)

########################################################
####### Functions for Grafana: create_api_key, create_or_update_datasource, create_dashboard
########################################################

def create_api_key():
    auth = (GRAFANA_USER, GRAFANA_PASSWORD)
    print('!---->', auth)
    headers = {"Content-Type": "application/json"}
    payload = {
        "name": "ProgrammaticKey",
        "role": "Admin",
    }
    response = requests.post(
        f"{GRAFANA_URL}/api/auth/keys", auth=auth, headers=headers, json=payload
    )

    if response.status_code == 200:
        print("API key created successfully")
        return response.json()["key"]

    elif response.status_code == 409:  # Conflict, key already exists
        print("API key already exists, updating...")
        # Find the existing key
        keys_response = requests.get(f"{GRAFANA_URL}/api/auth/keys", auth=auth)
        if keys_response.status_code == 200:
            for key in keys_response.json():
                if key["name"] == "ProgrammaticKey":
                    # Delete the existing key
                    delete_response = requests.delete(
                        f"{GRAFANA_URL}/api/auth/keys/{key['id']}", auth=auth
                    )
                    if delete_response.status_code == 200:
                        print("Existing key deleted")
                        # Create a new key
                        return create_api_key()
        print("Failed to update API key")
        return None
    else:
        print(f"Failed to create API key: {response.text}")
        return None


def create_or_update_datasource(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    datasource_payload = {
        "name": "PostgreSQL",
        "type": "postgres",
        "url": f"{PG_HOST}:{PG_PORT}",
        "access": "proxy",
        "user": PG_USER,
        "database": PG_DB,
        "basicAuth": False,
        "isDefault": True,
        "jsonData": {"sslmode": "disable", "postgresVersion": 1300},
        "secureJsonData": {"password": PG_PASSWORD},
    }

    print("Datasource payload:")
    print(json.dumps(datasource_payload, indent=2))

    # First, try to get the existing datasource
    response = requests.get(
        f"{GRAFANA_URL}/api/datasources/name/{datasource_payload['name']}",
        headers=headers,
    )

    if response.status_code == 200:
        # Datasource exists, let's update it
        existing_datasource = response.json()
        datasource_id = existing_datasource["id"]
        print(f"Updating existing datasource with id: {datasource_id}")
        response = requests.put(
            f"{GRAFANA_URL}/api/datasources/{datasource_id}",
            headers=headers,
            json=datasource_payload,
        )
    else:
        # Datasource doesn't exist, create a new one
        print("Creating new datasource")
        response = requests.post(
            f"{GRAFANA_URL}/api/datasources", headers=headers, json=datasource_payload
        )

    print(f"Response status code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    print(f"Response content: {response.text}")

    if response.status_code in [200, 201]:
        print("Datasource created or updated successfully")
        return response.json().get("datasource", {}).get("uid") or response.json().get(
            "uid"
        )
    else:
        print(f"Failed to create or update datasource: {response.text}")
        return None
    

def create_dashboard(api_key, datasource_uid, dashboard_file):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with open(dashboard_file, "r") as f:
            dashboard_json = json.load(f)
    except FileNotFoundError:
        print(f"Error: {dashboard_file} not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding {dashboard_file}: {str(e)}")
        return

    print("Dashboard JSON loaded successfully.")

    # Update datasource UID in the dashboard JSON
    panels_updated = 0
    for panel in dashboard_json.get("panels", []):
        if isinstance(panel.get("datasource"), dict):
            panel["datasource"]["uid"] = datasource_uid
            panels_updated += 1
        elif isinstance(panel.get("targets"), list):
            for target in panel["targets"]:
                if isinstance(target.get("datasource"), dict):
                    target["datasource"]["uid"] = datasource_uid
                    panels_updated += 1

    print(f"Updated datasource UID for {panels_updated} panels/targets.")

    # Remove keys that shouldn't be included when creating a new dashboard
    dashboard_json.pop("id", None)
    dashboard_json.pop("uid", None)
    dashboard_json.pop("version", None)

    # Prepare the payload
    dashboard_payload = {
        "dashboard": dashboard_json,
        "overwrite": True,
        "message": "Updated by Python script",
    }

    print("Sending dashboard creation request...")

    response = requests.post(
        f"{GRAFANA_URL}/api/dashboards/db", headers=headers, json=dashboard_payload
    )

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.text}")

    if response.status_code == 200:
        print("Dashboard created successfully")
        return response.json().get("uid")
    else:
        print(f"Failed to create dashboard: {response.text}")
        return None
    

if __name__ == "__main__":

    load_dotenv()

    # Check services

    if not wait_for_services():
        print("Exiting script as services are not ready.")
        sys.exit(1)


    # Trigger pipeline in mage.ai

    run_pipeline_populate_elasticsearch()


    # Populalte Postres with syntetic data for Grafana

    TZ_INFO = os.getenv("TZ", "Europe/Sofia")
    tz = ZoneInfo(TZ_INFO)

    init_db(localhost=False)
    clear_tables(localhost=False)

    print(f"Script started at {datetime.now(tz)}")
    end_time = datetime.now(tz)
    start_time = end_time - timedelta(hours=6)
    print(f"Generating historical data from {start_time} to {end_time}")
    generate_synthetic_data(start_time, end_time, localhost=False)
    print("Historical data generation complete.")


    # Create api_key, data connection and dashboard in Grafana

    GRAFANA_URL = "http://grafana:3000"

    GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER")
    GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD")

    PG_HOST = os.getenv("POSTGRES_HOST")
    PG_DB = os.getenv("POSTGRES_DB")
    PG_USER = os.getenv("POSTGRES_USER")
    PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    PG_PORT = os.getenv("POSTGRES_PORT")
    
    dashboard_file = "grafana-glimmerfox-dashboard.json"

    api_key = create_api_key()
    if not api_key:
        print("API key creation failed")

    datasource_uid = create_or_update_datasource(api_key)
    if not datasource_uid:
        print("Datasource creation failed")

    create_dashboard(api_key, datasource_uid, dashboard_file)