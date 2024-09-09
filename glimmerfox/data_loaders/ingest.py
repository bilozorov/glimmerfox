import pandas as pd
import csv
import requests
from io import StringIO

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

url = "https://raw.githubusercontent.com/bilozorov/glimmerfox-rag/main/data/knowledge.csv"
limit_rows = None

@data_loader
def load_data(*args, **kwargs):
    """
    Reads a CSV file from the given URL and returns a pandas DataFrame.

    This function handles CSV files with inconsistent number of commas in fields.
    It uses the requests library to fetch the file content and csv.reader for parsing.

    Args:
        url (str): The URL of the CSV file to be loaded.
        limit_rows (Optional[int]): Maximum number of rows to read from the CSV.
            If None, all rows are read. Defaults to None.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        Optional[pd.DataFrame]: A DataFrame containing the data from the CSV file.
            Returns None if an error occurs during file reading or parsing.

    Raises:
        requests.RequestException: If there's an error fetching the file from the URL.
        csv.Error: If there's an error parsing the CSV data.
        pd.errors.EmptyDataError: If the resulting DataFrame is empty.

    Example:
        >>> url = "https://example.com/data.csv"
        >>> df = load_data(url, limit_rows=100)
        >>> if df is not None:
        ...     print(df.head())
        ... else:
        ...     print("Failed to load data")

    Note:
        - The function uses QUOTE_ALL mode and '"' as the quote character for CSV parsing.
        - It skips initial whitespace in each field.
        - If limit_rows is specified, the function will attempt to read up to that many rows,
          but may return fewer if the file is shorter.
    """
    
    try:
        # Fetch the content of the CSV file
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Use StringIO to create a file-like object from the content
        csv_data = StringIO(response.text)
        
        # Read the CSV data using csv.reader
        reader = csv.reader(csv_data, quotechar='"', delimiter=',', quoting=csv.QUOTE_ALL, skipinitialspace=True)
        
        # Extract the header and rows
        header = next(reader)
        
        if limit_rows is not None:
            rows = []
            for _ in range(limit_rows):
                try:
                    rows.append(next(reader))
                except StopIteration:
                    break  # Stop if we've reached the end of the file
        else:
            rows = list(reader)
        
        # Create a DataFrame
        df = pd.DataFrame(rows, columns=header)
        
        return df
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return None
    


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'
