# ✈️ TIA Virtual Assistant — Tribhuvan International Airport Helpdesk (EN/NE)

A multilingual, intelligent virtual help desk for Kathmandu’s Tribhuvan International Airport (TIA). It provides travelers with real-time flight status, live weather, and accurate facility information using a RAG‑powered LangGraph agent.

Built to be fast, deterministic, and airport‑specific.

---

## 🚀 Key Features

### 🧠 1. Smart FAQ Answering (RAG)

* Airport rules & regulations
* Customs guidelines
* Baggage allowance
* Prohibited items
* Facilities & services

**Powered by:**

* Chroma Vector DB
* HuggingFace MiniLM-L6-v2 embeddings
* Strict RAG chain enforcing tool-only responses

### ✈️ 2. Live Flight Status Lookup

Supports queries like:

* *"What is the status of RA205?"*
* *"SQ700 को स्थिति के छ?"*

**Uses:**

* Structured JSON flight data (local mock)
* Robust flight‑code extraction to avoid translation errors

### ☀️ 3. Real-Time Kathmandu Weather

Provides:

* Temperature
* Wind
* Visibility
* Conditions

**API:** Open-Meteo

### 🌐 4. Multilingual (English + Nepali)

A translation layer handles:

* Automatic language detection
* Protecting flight codes
* EN ↔ NE round‑trip integrity
* Smooth multi-language conversation memory

### 🧩 5. ReAct Agent with Tool Enforcement (LangGraph)

The agent uses three tools:

1. Flight Status Tool (mandatory for flight queries)
2. Weather Tool (mandatory for weather queries)
3. RAG Tool (mandatory for airport info)

The agent **cannot hallucinate** due to:

* Strict system routing rules
* No direct LLM answers allowed
* Every response must come from one of the tools

---

## 🛠️ Technology Stack

| Layer           | Technology                      |
| --------------- | ------------------------------- |
| Frontend/UI     | Streamlit                       |
| LLM             | Ollama — qwen2:7b               |
| Agent Framework | LangChain + LangGraph           |
| RAG             | Chroma Vector DB                |
| Embeddings      | MiniLM-L6-v2                    |
| Weather API     | Open-Meteo                      |
| Flight Data     | Local JSON (AeroDataBox mock)   |
| Translation     | Custom EN/NE translation system |

---

## 📂 Recommended Project Structure

```
/app.py                 # Main Streamlit app
/flight_tools.py        # Flight & weather tools
/translation_tools.py   # Language utilities
/db/                    # Chroma vector DB (ignored in Git)
/ingest.py              # Build vector database
/.env                   # API keys
```

---

## 🧰 Setup & Installation

### 1. Clone Repository

```
git clone https://github.com/AaryanBasnet/TARA.git
cd TIA-Virtual-Assistant
```

### 2. Create Virtual Environment

```
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```
pip install -r requirements.txt
```

### 4. Pull the LLM

```
ollama pull qwen2:7b
```

(Use llama3 or any other model if preferred.)

### 5. Create `.env` File

```
OPENMETEO_API_URL="https://api.open-meteo.com/"
AERODATABOX_KEY="your_api_key_if_using_real_data"
```

### 6. Build the Vector Database

```
python ingest.py
```

This script:

* Loads airport documents
* Splits & chunks text
* Embeds using MiniLM-L6-v2
* Stores them in ChromaDB

### ▶️ Run the Application

Start Ollama, then run:

```
streamlit run app.py
```

---

## 🧪 Example Queries

* *"What items are prohibited in hand luggage?"*
* *"RA205 को स्थिति के छ?"*
* *"Is there a prepaid taxi at the arrival gate?"*
* *"What is today’s weather at TIA?"*
* *"Where is the immigration area located?"*

---

## 🛡️ Why This Assistant Is Reliable

* Hallucination‑proof (tool‑only answers)
* Airport‑specific RAG data
* Deterministic routing: **flight → weather → RAG**
* English + Nepali support
* Safe handling of flight codes during translation

---

## 📌 Future Improvements

* Integrate real AeroDataBox flight API
* Terminal maps & navigation
* Voice input (Whisper)
* Staff panel to manage FAQ database

---

## 📜 License

MIT License

---


