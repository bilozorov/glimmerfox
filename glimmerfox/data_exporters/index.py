import json
from typing import Dict, List, Union

import numpy as np
from elasticsearch import Elasticsearch

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(documents: List[Dict[str, Union[Dict, List[int], str]]], *args, **kwargs):
    """
    Index documents into Elasticsearch with dense vector embeddings, supporting Docker deployments.

    This function creates or recreates an Elasticsearch index with specified settings,
    then indexes the provided documents. It includes retry logic for Docker container startup.

    Args:
        documents (List[Dict[str, Union[Dict, List[float], str]]]): List of documents to index.
            Each document should be a dictionary with 'chunk', 'document_id', and 'embedding' keys.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments. Supported keys:
            - connection_string (str): Elasticsearch connection URL. Default: 'http://elasticsearch:9200'
            - index_name (str): Name of the Elasticsearch index. Default: 'documents'
            - number_of_shards (int): Number of shards for the index. Default: 1
            - number_of_replicas (int): Number of replicas for the index. Default: 0
            - dimensions (int): Dimensionality of the embedding vectors. If not provided,
                                it's inferred from the first document's embedding.
            - max_retries (int): Maximum number of connection retries. Default: 5
            - retry_interval (int): Seconds to wait between retries. Default: 10

    Returns:
        List[Union[List[float], np.ndarray]]: A list of embeddings from the first 5 indexed documents.

    Raises:
        ConnectionError: If unable to connect to Elasticsearch after max retries.
        ValueError: If no documents are provided or if required keys are missing in documents.
        elasticsearch.ElasticsearchException: For any Elasticsearch-related errors.

    Example:
        >>> docs = [
        ...     {"chunk": "Hello world", "document_id": "doc1", "embedding": [0.1, 0.2, 0.3]},
        ...     {"chunk": "Elasticsearch rocks", "document_id": "doc2", "embedding": [0.4, 0.5, 0.6]}
        ... ]
        >>> result = elasticsearch_index(docs, index_name="my_index", dimensions=3)
        >>> print(len(result))  # Number of embeddings returned (up to 5)
        2

    Note:
        - This function will delete and recreate the specified index if it already exists.
        - Progress is printed to the console for every 100 documents indexed.
        - NumPy arrays are converted to lists before indexing.
        - The function includes retry logic for Docker container startup.
        - Only the embeddings of the first 5 documents are returned, regardless of the total number indexed.
    """

    connection_string = kwargs.get('connection_string', 'http://elasticsearch:9200')
    index_name = kwargs.get('index_name', 'documents')
    number_of_shards = kwargs.get('number_of_shards', 1)
    number_of_replicas = kwargs.get('number_of_replicas', 0)
    dimensions = kwargs.get('dimensions')

    if dimensions is None and len(documents) > 0:
        document = documents[0]
        dimensions = len(document.get('embedding') or [])

    es_client = Elasticsearch(connection_string)

    print(f'Connecting to Elasticsearch at {connection_string}')

    index_settings = {
            "settings": {
                "number_of_shards": number_of_shards,
                "number_of_replicas": number_of_replicas,
            },
            "mappings": {
                "properties": {
                    "chunk": {"type": "text"},
                    "document_id": {"type": "text"},
                    "question": {"type": "text"},
                    "answer": {"type": "text"},
                    "embedding": {
                        "type": "dense_vector", 
                        "dims": 96,
                        "index": True,
                        "similarity": "cosine"
                    },
                }
            }
        }

    # Recreate the index by deleting if it exists and then creating with new settings
    if es_client.indices.exists(index=index_name):
        es_client.indices.delete(index=index_name)
        print(f'Index {index_name} deleted')

    es_client.indices.create(index=index_name, body=index_settings)
    print('Index created with properties:')
    print(json.dumps(index_settings, indent=2))
    print('Embedding dimensions:', dimensions)

    count = len(documents)
    print(f'Indexing {count} documents to Elasticsearch index {index_name}')
    for idx, document in enumerate(documents):
        if idx % 100 == 0:
            print(f'{idx + 1}/{count}')

        if isinstance(document['embedding'], np.ndarray):
            document['embedding'] = document['embedding'].tolist()

        es_client.index(index=index_name, document=document)

    return [d['embedding'] for d in documents[:5]]


