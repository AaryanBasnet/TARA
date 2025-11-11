# TIA Virtual Assistant 🇳🇵✈️

A smart, conversational chatbot for Kathmandu's Tribhuvan International Airport (TIA). This virtual help desk provides travelers with real-time flight info, weather, and answers to common airport questions using a RAG-powered Llama 3 model.



---

## 🌟 Features

* **🤖 Smart FAQ Answering (RAG):** Answers user questions about airport rules, baggage, customs, and facilities by pulling information from a local vector database.
* **✈️ Live Flight Status:** Checks real-time flight status (departure, arrival, delays, gates) using the AeroDataBox API.
* **☀️ Live Airport Weather:** Fetches the current weather conditions at TIA.

---

## 🛠️ Technology Stack

* **Framework:** Streamlit
* **LLM:** Ollama (using `llama3:8b`)
* **RAG & Orchestration:** LangChain
* **Embeddings:** HuggingFace `all-MiniLM-L6-v2`
* **Vector Database:** ChromaDB
* **Live Data APIs:** AeroDataBox (RapidAPI)

---

## 🚀 How to Run This Project

### 1. Prerequisites

* [Python 3.9+](https://www.python.org/)
* [Ollama](https://ollama.com/) installed and running.

### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/AaryanBasnet/TARA.git](https://github.com/AaryanBasnet/TARA.git)
    cd TIA-Virtual-Assistant
    ```

2.  **Install Python dependencies:**
    ```bash
    # It's recommended to use a virtual environment
    python -m venv venv
    source venv/bin/activate  # (On Windows, use: venv\Scripts\activate)
    
    pip install -r requirements.txt
    ```

### 3. Configuration

1.  **Pull the LLM:**
    You must have the `llama3:8b` model available in Ollama.
    ```bash
    ollama pull llama3:8b
    ```

2.  **Set up your API Keys:**
    This project requires a `.env` file for API keys.
    * Create a file named `.env` in the root of the project.
    * Add your RapidAPI key (for AeroDataBox):

    ```text
    # Get this from [rapidapi.com/aedbx-aedbx/api/aerodatabox](https://rapidapi.com/aedbx-aedbx/api/aerodatabox)
    RAPIDAPI_KEY="your_rapidapi_key_here"
    ```

3.  **Build the Vector Database (IMPORTANT):**
    This app relies on a local vector database in a `/db` folder (which is ignored by Git). You need to provide the script and instructions for users to build this.

    *(**TODO:** You need to add your data ingestion script, e.g., `ingest.py`, to the repo.)*

    ```bash
    # Example command users would run
    python ingest.py 
    ```

### 4. Run the Application

Once Ollama is running and your `.env` and `db` files are ready:

```bash
streamlit run app.py
