# RAG Q&A System

This project implements a Retrieval-Augmented Generation (RAG) Question Answering system using Elasticsearch for retrieval and OpenAI's models for answer generation.

## Features

- Elasticsearch-based retrieval for finding relevant context
- OpenAI API integration for answer generation
- Streamlit-based user interface
- Docker support for easy deployment
- Flexible usage with or without OpenAI API key

## Project Structure

```
project_root/
│
├── app/
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
│
├── docker-compose.yml
└── .env
```

## Usage

### With Docker

1. Ensure Docker and Docker Compose are installed on your system.
2. Clone this repository.
3. Create a `.env` file in the project root with necessary environment variables.
4. Run `docker-compose up -d` to start all services.
5. Access the Streamlit app at `http://localhost:8501`.

### Local Development

1. Ensure you have Python 3.9+ and Conda installed.
2. Navigate to the `app/` directory.
3. Create a Conda environment: `conda create -n rag_qa_env python=3.9`
4. Activate the environment: `conda activate rag_qa_env`
5. Install requirements: `pip install -r requirements.txt`
6. Run the Streamlit app: `streamlit run app.py`

## API Key Usage

- Without an API key, users can still use the app but are limited to queries of 100 characters or less. Answers will be generated using a simple method.
- With an API key, users have full access to the system, using OpenAI's powerful models for answer generation.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.