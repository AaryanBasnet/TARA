# TIA Smart Arrival Assistant

A multilingual (English and Nepali) virtual help desk for Tribhuvan International Airport (TIA), Kathmandu. A traveller can ask about flights, weather, customs rules and airport facilities, verify identity for a SIM card (KYC), and scan a boarding pass. It was built as a thesis project.

Everything runs locally: the language model is served by Ollama, so no paid API is needed.

---

## How it works

```
React frontend (Vite, port 3000)
        |  /api/*  (proxied)
        v
FastAPI backend (port 8000)
        |
        +-- /api/chat ---> language detection ---> (Nepali -> English)
        |                          |
        |                          v
        |                  LangGraph ReAct agent  (qwen2.5:3b via Ollama)
        |                   |        |        |        |
        |   general info    |  flight |  weather|  route |  SIM KYC
        |   (RAG, Chroma)   |  status | (Open-  | search | (MRZ + face)
        |                   |  (cache)|  Meteo) |        |
        |                          |
        |                          v
        |                  answer ---> (English -> Nepali)
        |
        +-- /api/kyc/verify, /api/boarding-pass/scan   (OCR + validation)
        +-- /api/flights, /api/weather, /api/evaluation, /api/health
```

- **Agent:** a LangGraph ReAct agent with a system prompt that routes each question to a tool. The answer has to come from a tool, which limits hallucination.
- **RAG:** airport documents are split into chunks, embedded with `all-MiniLM-L6-v2` and stored in Chroma (`db_new/`). Retrieval uses MMR (fetch 20, keep 6) after a keyword-expansion step.
- **Flights:** read from `flight_cache.json`, a saved snapshot from the AviationStack API. It is not live unless you refresh it with an API key (`flight_data_engine.py`).
- **Weather:** live from the Open-Meteo API.
- **Translation:** Nepali questions are translated to English, answered, and translated back with `deep-translator` (Google Translate's free endpoint). If that service rate-limits, the app falls back to the untranslated text.
- **KYC and boarding pass:** EasyOCR and OpenCV read documents; passport MRZ lines are checked with the ICAO 9303 check-digit algorithm; faces are compared with `face_recognition`.

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, Tailwind CSS, Framer Motion |
| Backend | Python, FastAPI, Uvicorn |
| Agent | LangChain, LangGraph |
| LLM | Ollama, `qwen2.5:3b` |
| Retrieval | Chroma, sentence-transformers (`all-MiniLM-L6-v2`) |
| Documents | EasyOCR, OpenCV, `face_recognition` (optional) |
| Data | Open-Meteo (weather), AviationStack snapshot (flights) |

## Run it

You need Python 3.13 (3.14 is too new for some of the packages), Node 18+ and [Ollama](https://ollama.com).

```bash
# 1. Python environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # dlib / face_recognition are optional (KYC face match only)

# 2. The language model
ollama pull qwen2.5:3b

# 3. Backend (http://localhost:8000)
cd backend
uvicorn main:app --port 8000

# 4. Frontend, in a second terminal (http://localhost:3000)
cd frontend
npm install
npm run dev
```

The vector database in `db_new/` is already built. To rebuild it from `knowledge_base/`, run `python ingest.py`.

Optional: copy `.env.example` to `.env` and add an `AVIATIONSTACK_API_KEY` to refresh the flight data.

The first start takes a while: it loads the embedding model and downloads an NLTK tokenizer.

## Example questions

- "Where is the smoking area?"
- "What is the status of flight SQ700?"
- "What is the weather in Kathmandu?"
- "How many phones can I bring into Nepal?"
- "RA205 को स्थिति के छ?"

## Evaluation

`evaluation/` holds the scripts and saved results used in the thesis: a 50-question test set, retrieval and answer-quality metrics (faithfulness and answer relevancy), tool-selection accuracy, response time, and checks for the passport and boarding-pass code. See `evaluation/README.md`. The sample sizes are small, so treat the numbers as indicative.

## Known limitations

- The flight data is a saved snapshot, not a live feed.
- Translation depends on a free Google endpoint and can silently fall back to English.
- Boarding-pass OCR accuracy is low on the three sample images tested.
- A 3B-parameter local model is fast and free but less accurate than a hosted model.

## License

MIT
