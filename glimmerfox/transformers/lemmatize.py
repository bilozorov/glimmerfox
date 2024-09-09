from typing import Dict, List
import spacy

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(documents: List[Dict], *args, **kwargs) -> List[Dict]:
    """
    Lemmatize the text in the given documents using spaCy.

    This function processes a list of documents, lemmatizing the text in each document's 'chunk' field.
    It uses the spaCy 'en_core_web_sm' model for English language processing.

    Args:
        documents (List[Dict]): A list of dictionaries, where each dictionary represents a document.
                                Each document should have 'document_id' and 'chunk' keys.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary contains:
            - 'chunk': The original text chunk.
            - 'document_id': The original document ID.
            - 'tokens': A list of lemmatized tokens from the text chunk.

    Raises:
        ImportError: If spaCy or the 'en_core_web_sm' model is not installed.
        KeyError: If a document in the input list doesn't have 'document_id' or 'chunk' keys.

    Example:
        >>> docs = [
        ...     {"document_id": 1, "chunk": "The cats are running fast."},
        ...     {"document_id": 2, "chunk": "She writes beautifully."}
        ... ]
        >>> result = lemmatize_text(docs)
        >>> print(result)
        [
            {
                "chunk": "The cats are running fast.",
                "document_id": 1,
                "tokens": ["the", "cat", "be", "run", "fast", "."]
            },
            {
                "chunk": "She writes beautifully.",
                "document_id": 2,
                "tokens": ["she", "write", "beautifully", "."]
            }
        ]

    Note:
        This function prints progress information to the console, showing the number of
        documents processed every 100 documents.
    """

    count = len(documents)
    print('Documents', count)

    nlp = spacy.load('en_core_web_sm')

    data = []

    for idx, document in enumerate(documents):
        document_id = document['document_id']
        if idx % 100 == 0:
            print(f'{idx + 1}/{count}')

        # Process the text chunk using spaCy
        chunk = document['chunk']
        doc = nlp(chunk)
        tokens = [token.lemma_ for token in doc]

        # data.append(
        #     dict(
        #         chunk=chunk,
        #         document_id=document_id,
        #         tokens=tokens,
        #     )
        # )

        data.append(
            dict(
                chunk=chunk,
                document_id=document_id,
                tokens=tokens,
                question=document['data']['question'],
                answer=document['data']['answer'],
            )
        )

    print('\nData', len(data))

    return data


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'
