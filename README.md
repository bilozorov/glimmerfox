
# The Glimmerfox Advanced RAG

<p align="left">
  <img src="https://raw.githubusercontent.com/bilozorov/glimmerfox/main/images/glimmerfox.webp" alt="Glimmerfox" height="300">
</p>

## 0. Overview

The Glimmerfox Advanced RAG Q&A System is a cutting-edge platform designed to provide accurate, context-aware information about the synthetic species Glimmerfox (*Vulpilynx chameleontis*). This system leverages a comprehensive knowledge base in combination with Large Language Models (LLMs) to offer users an interactive and informative experience.

### Purpose

- Provide accurate and up-to-date information on Glimmerfox biology, behavior, and ecology.
- Answer complex queries by synthesizing information from multiple sources within the knowledge base.
- Generate hypotheses and insights based on existing data, potentially aiding in further research and conservation efforts.

### Rationale

- Centralize and organize all available Glimmerfox data in a structured, easily accessible format.
- Ensure information accuracy through continuous updates and expert curation.
- Facilitate knowledge discovery by enabling complex queries and generating insights.
- Support interdisciplinary collaboration by providing a common, reliable information source for researchers.

## 1. Live project
**Glimmerfox Advanced RAG Q&A System**: [http://65.109.14.99:8501/](http://65.109.14.99:8501/)

## 2. Dataset

The system utilizes the **Glimmerfox Knowledge Base - Q&A Dataset**, a synthetic dataset designed specifically for Retrieval-Augmented Generation (RAG) projects. This dataset contains a comprehensive collection of questions and answers about the Glimmerfox (*Vulpilynx chameleontis*), a fictional genetically-engineered species combining traits from foxes, lynxes, and chameleons.

### Dataset Details
- **Name:** Glimmerfox Knowledge Base - Q&A Dataset
- **Source:** https://huggingface.co/datasets/bilozorov/glimmerfox
- **Language:** English
- **License:** MIT

It provides a rich source of information about the Glimmerfox, which was developed at the Sofia Laboratory for Genetic Innovation and Biodiversity in Bulgaria.

## 3. Technologies Used

### Mage
- Manages and orchestrates data pipelines and workflows.
- Automates data processing, transformation, and loading tasks.
- Enhances the system's scalability and maintainability.

### Elastic Search
- Used for performing vector search on the knowledge base.
- Retrieved results are used to build prompts and context for the LLM.
- Stores questions and answers from the knowledge.csv file in both text and vector formats.

### PostgreSQL
- Stores user questions, assistant answers, and user feedback.
- Database tables are created automatically on first application start.

### Streamlit
- Provides the user interface (UI) for the Q&A system.
- Allows users to input questions and receive answers.
- Includes feedback mechanism (Thumbs Up/Down buttons).

### OpenAI GPT
- LLM used for generating responses based on retrieved context.
- Used for advanced technique rewriting user query.
- Used for evaluation LLM-as-a-judge

### Grafana
- Used for system monitoring and analytics.
- Provides a dashboard to track metrics such as user feedback and LLM cost.

### Docker
- Each component of the application runs in a separate Docker container.
- Containers are started in a specific order to ensure proper system initialization.


## 4. Reproducibility

### Step 1: System Preparation
- Make sure you have installed [Docker](https://docs.docker.com/engine/install/), [Docker Compose](https://docs.docker.com/compose/install/) and [Git](https://git-scm.com/downloads).
### Step 2: Clone the github repository
```
git clone https://github.com/bilozorov/glimmerfox.git
```
### Step 3: Update your OPENAI_API_KEY
```
cd glimmerfox
cp .env.dev .env
rm .env.dev
nano .env
```
### Step 4: Start all services
```
docker compose up
```

### Step 4: Profit!
**That's it!** Everything will happen automatically:
- **Mage**, **Elasticsearch** and **Postgres** will be running.
- After that **Grafana** will be launched with automatic connection to the database and dashboard creation.
- When all services are started and checks are passed, a pipeline **populate_elasticsearch** will be automatically started in **Mage** for data processing and **Elasticsearch** population.
- The next step will be to automatically generate synthetic user queries and load them into **Postgres** for display in **Grafana** dashboards.
- After all services are started and all automatic triggers are initiated, the user interface will be launched using **Streamlit**.

### Urls for local deployment
- **Mage**: [http://localhost:6789/](http://localhost:6789/)
- **Grafana**: [http://localhost:3000/](http://localhost:3000/)
- **Streamlit**: [http://localhost:8501/](http://localhost:8501/)

### Urls for live deployment example:
- **Streamlit**: [http://65.109.14.99:8501/](http://65.109.14.99:8501/)

---

## Evaluation Criteria

* Problem description
    * 0 points: The problem is not described
    * 1 point: The problem is described but briefly or unclearly
    * 2 points: The problem is well-described and it's clear what problem the project solves ✅ Check Ovwerview section with Purpose and Rationale
* RAG flow
    * 0 points: No knowledge base or LLM is used
    * 1 point: No knowledge base is used, and the LLM is queried directly
    * 2 points: Both a knowledge base and an LLM are used in the RAG flow 
* Retrieval evaluation
    * 0 points: No evaluation of retrieval is provided
    * 1 point: Only one retrieval approach is evaluated
    * 2 points: Multiple retrieval approaches are evaluated, and the best one is used
* RAG evaluation
    * 0 points: No evaluation of RAG is provided
    * 1 point: Only one RAG approach (e.g., one prompt) is evaluated
    * 2 points: Multiple RAG approaches are evaluated, and the best one is used
* Interface
   * 0 points: No way to interact with the application at all
   * 1 point: Command line interface, a script, or a Jupyter notebook
   * 2 points: UI (e.g., Streamlit), web application (e.g., Django), or an API (e.g., built with FastAPI) 
* Ingestion pipeline
   * 0 points: No ingestion
   * 1 point: Semi-automated ingestion of the dataset into the knowledge base, e.g., with a Jupyter notebook
   * 2 points: Automated ingestion with a Python script or a special tool (e.g., Mage, dlt, Airflow, Prefect)
* Monitoring
   * 0 points: No monitoring
   * 1 point: User feedback is collected OR there's a monitoring dashboard
   * 2 points: User feedback is collected and there's a dashboard with at least 5 charts
* Containerization
    * 0 points: No containerization
    * 1 point: Dockerfile is provided for the main application OR there's a docker-compose for the dependencies only
    * 2 points: Everything is in docker-compose
* Reproducibility
    * 0 points: No instructions on how to run the code, the data is missing, or it's unclear how to access it
    * 1 point: Some instructions are provided but are incomplete, OR instructions are clear and complete, the code works, but the data is missing
    * 2 points: Instructions are clear, the dataset is accessible, it's easy to run the code, and it works. The versions for all dependencies are specified.
* Best practices
    * [ ] Hybrid search: combining both text and vector search (at least evaluating it) (1 point)
    * [ ] Document re-ranking (1 point)
    * [ ] User query rewriting (1 point)
* Bonus points (not covered in the course)
    * [ ] Deployment to the cloud (2 points)