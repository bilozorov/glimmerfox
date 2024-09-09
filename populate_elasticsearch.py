import requests
import time
import sys

def is_elasticsearch_ready(url="http://elasticsearch:9200"):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def is_mage_ready(url="http://magic:6789"):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def wait_for_services(max_retries=12):  # 12 * 5 seconds = 1 minute total wait time
    retries = 0
    while retries < max_retries:
        if is_elasticsearch_ready() and is_mage_ready():
            print("Both Elasticsearch and Mage are ready!")
            return True
        else:
            print(f"Attempt {retries + 1}/{max_retries}: Services not ready. Waiting 5 seconds...")
            time.sleep(5)
            retries += 1
    print("Max retries reached. Services are not ready.")
    return False

def run_pipeline_populate_elasticsearch():
    """
    populating by our KNWLG.base
    """
    url = "http://magic:6789/api/pipeline_schedules/5/pipeline_runs/e148d1b8a12c4c65b6fe0b4b703e196f"
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

if __name__ == "__main__":
    if wait_for_services():
        run_pipeline_populate_elasticsearch()
    else:
        print("Exiting script as services are not ready.")
        sys.exit(1)