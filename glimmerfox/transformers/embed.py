from typing import Dict, List

import numpy as np
import spacy

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(documents: List[Dict], *args, **kwargs) -> List[Dict]:
    """
    Generate embeddings for a list of documents using spaCy's 'en_core_web_sm' model.

    This function processes a list of documents, creating an embedding for each document
    by averaging the word vectors of its tokens. It uses spaCy's 'en_core_web_sm' model
    for English language processing.

    Args:
        documents (List[Dict]): A list of dictionaries, where each dictionary represents a document.
                                Each document should have 'document_id' and 'tokens' keys.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary contains:
            - 'chunk': The original text chunk (assumed to be present in input document).
            - 'document_id': The original document ID.
            - 'embedding': A list representing the average word vector for the document.

    Raises:
        KeyError: If a document in the input list doesn't have 'document_id' or 'tokens' keys.
        ImportError: If spaCy or the 'en_core_web_sm' model is not installed.

    Example:
        >>> docs = [
        ...     {"document_id": "doc1", "tokens": ["hello", "world"], "chunk": "hello world"},
        ...     {"document_id": "doc2", "tokens": ["spacy", "is", "great"], "chunk": "spacy is great"}
        ... ]
        >>> result = spacy_embeddings(docs)
        >>> print(result[0].keys())
        dict_keys(['chunk', 'document_id', 'embedding'])
        >>> print(len(result[0]['embedding']))  # Length of the embedding vector
        96  # This may vary depending on the spaCy model used

    Note:
        - This function prints progress information to the console, showing the number of
          documents processed every 100 documents.
        - The spaCy model is loaded for each document, which may be inefficient for large datasets.
          Consider loading the model once outside the loop for better performance.
        - The embedding is created by averaging word vectors, which is a simple approach and may not
          capture complex semantic relationships in the text.
    """

    count = len(documents)
    print('Documents', count)


    data = []
    
    for idx, document in enumerate(documents):
        document_id = document['document_id']
        if idx % 100 == 0:
            print(f'{idx + 1}/{count}')
        nlp = spacy.load('en_core_web_sm')
        tokens = document['tokens']
    
        # Combine tokens back into a single string of text used for embedding
        text = ' '.join(tokens)
        doc = nlp(text)
    
        # Average the word vectors in the doc to get a general embedding
        embedding = np.mean([token.vector for token in doc], axis=0).tolist()
    
        data.append(dict(
            chunk=document['chunk'],
            document_id=document['document_id'],
            question=document['question'],
            answer=document['answer'],
            embedding=embedding,
        ))
    
    return data


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'
