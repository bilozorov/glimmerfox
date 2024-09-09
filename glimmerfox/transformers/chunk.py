import pandas as pd
import re
from typing import List, Dict, Any

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(data: pd.DataFrame, *args, **kwargs) -> List[Dict[str, Any]]:
    """
    Transforms documents from a pandas DataFrame into a list of document dictionaries.

    This function processes a DataFrame containing question-answer pairs, creating
    a structured document for each row. It generates a unique document ID for each
    entry and formats the question and answer into a single chunk of text.

    Args:
        data (pd.DataFrame): DataFrame containing the documents data.
            Expected columns:
                - number: A unique identifier for each Q&A pair.
                - question: The question text.
                - answer: The corresponding answer text.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        List[Dict[str, Any]]: A list of document dictionaries. Each dictionary contains:
            - chunk (str): Formatted string containing the question and answer.
            - document (Dict[str, str]): Original data for the Q&A pair.
            - document_id (str): A unique identifier generated from the number and question.

    Raises:
        KeyError: If the input DataFrame doesn't have the required columns.

    Example:
        >>> df = pd.DataFrame({
        ...     'number': [1, 2],
        ...     'question': ['What is Python?', 'How to use pandas?'],
        ...     'answer': ['A programming language', 'Import it and use DataFrames']
        ... })
        >>> result = transform(df)
        >>> print(result[0])
        {
            'chunk': 'question:\nWhat is Python?\nanswer:\nA programming language\n',
            'document': {
                'number': '1',
                'question': 'What is Python?',
                'answer': 'A programming language'
            },
            'document_id': 'doc_1_what_is_python_'
        }

    Note:
        - The function sanitizes the question text to create a URL-friendly document ID.
        - The document ID is limited to the first 30 characters of the sanitized question.
        - The function prints the total number of documents processed.
    """
    documents = []
    
    for _, row in data.iterrows():
        number = str(row['number'])
        question = str(row['question'])
        answer = str(row['answer'])
        
        # Generate a unique document ID
        # substitute all non-word character to '_' in the first 30 characters of the question string 
        sanitized_question = re.sub(r'\W', '_', question[:30]).lower()
        # example 'document_id': 'doc_1_what_is_the_genus_of_the_glimm'}
        document_id = f"doc_{number}_{sanitized_question}"
        
        # Format the document string
        chunk = '\n'.join([
            f'question:\n{question}\n',
            f'answer:\n{answer}\n',
        ])
        
        documents.append({
            'chunk': chunk,
            # 'document': {
            'data': {
                'number': number,
                'question': question,
                'answer': answer
            },
            'document_id': document_id,
        })

    print(f'Documents: {len(documents)}')
            
    return documents


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'
