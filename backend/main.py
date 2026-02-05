"""
FastAPI Backend for TIA Smart Arrival Ecosystem
Production-Quality RAG Agent with Advanced Retrieval
"""

import os
import sys
import json
import time
import re
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager
import glob

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Environment Setup ---
from dotenv import load_dotenv
load_dotenv()

# --- LangChain/LangGraph Imports ---
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.documents import Document

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# --- Tool Imports ---
from flight_tools import (
    get_flight_status_from_json,
    get_kathmandu_weather_openmeteo,
    search_flights_by_route
)
from translation_tools import detect_language, translate_to_english, translate_to_nepali

# Try to import optional modules
try:
    from kyc_tools import process_sim_card_kyc
    KYC_AVAILABLE = True
except ImportError:
    KYC_AVAILABLE = False
    process_sim_card_kyc = None

try:
    from boarding_pass_tools import scan_boarding_pass, format_boarding_pass_result
    BOARDING_PASS_AVAILABLE = True
except ImportError:
    BOARDING_PASS_AVAILABLE = False
    scan_boarding_pass = None

try:
    from flight_data_engine import update_cache
    FLIGHT_ENGINE_AVAILABLE = True
except ImportError:
    FLIGHT_ENGINE_AVAILABLE = False

# QR Code for KYC
try:
    import qrcode
    from io import BytesIO
    import base64
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(PARENT_DIR, "db_new")
MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL = "qwen2.5:3b"
FLIGHT_CACHE_FILE = os.path.join(PARENT_DIR, "flight_cache.json")

# RAG Settings
RETRIEVAL_K = 6          # Number of documents to retrieve
RETRIEVAL_FETCH_K = 20   # Number to fetch before MMR filtering
MMR_LAMBDA = 0.7         # Balance between relevance (1) and diversity (0)


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

db = None
embeddings = None
llm = None
agent_executor = None
state = {
    "latest_retrieval_score": 0.0
}


# =============================================================================
# QUERY PREPROCESSING
# =============================================================================

# Comprehensive keyword expansions for better retrieval
QUERY_EXPANSIONS = {
    # Electronics & Devices
    "phone": "mobile phone customs duty smartphone cellular device",
    "phones": "mobile phones customs duty smartphone cellular devices how many",
    "mobile": "mobile phone customs duty smartphone cellular",
    "laptop": "laptop computer electronics customs duty",
    "camera": "camera electronics customs photography equipment",
    "drone": "drone uav unmanned aerial vehicle customs prohibited",
    "electronics": "electronics gadgets devices customs duty laptop phone camera",

    # Airport Facilities
    "smoking": "smoking area cigarette tobacco designated zone",
    "smoke": "smoking area cigarette tobacco designated zone",
    "wifi": "wifi internet wireless free wifi connectivity",
    "internet": "wifi internet wireless free connectivity",
    "lounge": "lounge waiting area vip cip executive business class",
    "toilet": "toilet restroom bathroom washroom lavatory",
    "restroom": "toilet restroom bathroom washroom lavatory",
    "bathroom": "toilet restroom bathroom washroom lavatory",
    "food": "food restaurant cafe cafeteria dining eating meals",
    "eat": "food restaurant cafe cafeteria dining eating meals",
    "restaurant": "food restaurant cafe cafeteria dining",
    "atm": "atm cash money withdraw bank currency",
    "bank": "bank atm money exchange currency foreign exchange",
    "prayer": "prayer room mosque meditation religious",
    "mosque": "prayer room mosque meditation religious muslim",
    "medical": "medical health clinic first aid doctor nurse emergency",
    "pharmacy": "pharmacy medicine medical chemist drug store",
    "shop": "shop shopping duty free store retail",
    "shopping": "shop shopping duty free store retail",

    # SIM & Telecom
    "sim": "sim card mobile phone tourist sim ncell ntc telecom",
    "simcard": "sim card mobile phone tourist sim ncell ntc telecom",
    "ncell": "sim card ncell mobile tourist telecom",
    "ntc": "sim card ntc nepal telecom mobile tourist",

    # Transportation
    "taxi": "taxi cab transport ground transportation prepaid metered",
    "cab": "taxi cab transport ground transportation",
    "bus": "bus transport ground transportation public",
    "transport": "transport taxi bus cab ground transportation",
    "parking": "parking car vehicle parking lot",

    # Money & Currency
    "money": "money exchange currency foreign exchange atm bank",
    "currency": "money exchange currency foreign exchange rate",
    "exchange": "money exchange currency foreign exchange rate bank",
    "dollar": "money exchange currency foreign exchange usd dollar",

    # Customs & Immigration
    "customs": "customs duty declaration import export prohibited items allowance",
    "duty": "customs duty free allowance tax import",
    "prohibited": "prohibited items banned restricted customs not allowed forbidden",
    "banned": "prohibited items banned restricted customs not allowed",
    "allowed": "allowed permitted customs duty free items can bring",
    "bring": "bring carry customs allowed prohibited items duty",
    "carry": "bring carry customs allowed prohibited items allowance",
    "import": "import customs duty declaration bring items",
    "declare": "declare declaration customs form items",
    "alcohol": "alcohol liquor wine beer customs duty allowance alcoholic beverages",
    "liquor": "alcohol liquor wine beer customs duty allowance",
    "cigarette": "cigarette tobacco smoking customs duty allowance",
    "gold": "gold jewelry ornaments customs duty declaration valuable",
    "jewelry": "gold jewelry ornaments customs duty declaration valuable",

    # Visa & Immigration
    "visa": "visa immigration passport entry permit tourist arrival",
    "immigration": "visa immigration passport entry permit counter",
    "passport": "passport visa immigration travel document",
    "arrival": "arrival visa immigration on arrival tourist",

    # Baggage
    "baggage": "baggage luggage bag allowance weight checked carry-on",
    "luggage": "baggage luggage bag allowance weight suitcase",
    "bag": "baggage luggage bag allowance carry-on checked",
    "lost": "lost found missing baggage luggage property claim",
    "missing": "lost found missing baggage luggage property",
    "weight": "weight baggage luggage allowance kg kilogram limit",

    # Flights
    "flight": "flight status arrival departure schedule gate terminal",
    "delay": "delay delayed flight status schedule",
    "gate": "gate terminal flight boarding departure",
    "terminal": "terminal gate flight domestic international",
    "boarding": "boarding pass gate time flight",

    # Trekking & Permits
    "trekking": "trekking permit tims hiking mountain trail",
    "permit": "permit trekking tims restricted area",
    "tims": "tims trekking permit information management system",

    # Time & Schedule
    "time": "time schedule hours operation opening closing",
    "hours": "hours time schedule operation opening closing",
    "open": "open hours time schedule operation",

    # Help & Information
    "help": "help desk information assistance counter",
    "information": "information desk help counter inquiry",
    "contact": "contact phone number email help desk",
}

# Synonyms mapping for keyword boosting
KEYWORD_SYNONYMS = {
    "phone": ["mobile", "cellphone", "smartphone", "cellular"],
    "toilet": ["restroom", "bathroom", "washroom", "lavatory", "wc"],
    "food": ["restaurant", "cafe", "eat", "dining", "meals"],
    "money": ["currency", "exchange", "cash", "atm"],
    "taxi": ["cab", "transport", "ride"],
    "baggage": ["luggage", "bag", "suitcase"],
    "customs": ["duty", "import", "declaration"],
    "visa": ["immigration", "permit", "entry"],
}


def preprocess_query(query: str) -> str:
    """
    Preprocess and expand the query for better retrieval.
    Handles synonyms, plurals, and common variations.
    """
    query = query.strip().lower()

    # Check for matching expansions (check longer matches first)
    expanded_terms = []
    query_words = set(re.findall(r'\b\w+\b', query))

    for key, expansion in QUERY_EXPANSIONS.items():
        if key in query_words or key in query:
            expanded_terms.append(expansion)

    # Combine original query with expansions (limit to avoid noise)
    if expanded_terms:
        # Take up to 3 most relevant expansions
        expansion_text = " ".join(expanded_terms[:3])
        return f"{query} {expansion_text}"

    return query


def extract_keywords(query: str) -> List[str]:
    """
    Extract important keywords from query.
    Also adds synonyms for better matching.
    """
    # Extended stopwords
    stopwords = {
        'what', 'where', 'how', 'is', 'the', 'a', 'an', 'in', 'at', 'to',
        'for', 'of', 'can', 'i', 'do', 'get', 'find', 'there', 'are', 'my',
        'me', 'please', 'tell', 'about', 'know', 'need', 'want', 'would',
        'could', 'should', 'have', 'has', 'been', 'being', 'will', 'does',
        'did', 'doing', 'this', 'that', 'these', 'those', 'with', 'from',
        'many', 'much', 'some', 'any', 'which', 'who', 'whom', 'whose'
    }

    words = re.findall(r'\b\w+\b', query.lower())
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    # Add synonyms for better matching
    enhanced_keywords = list(keywords)
    for kw in keywords:
        if kw in KEYWORD_SYNONYMS:
            enhanced_keywords.extend(KEYWORD_SYNONYMS[kw])

    return list(set(enhanced_keywords))  # Remove duplicates


# =============================================================================
# ADVANCED RETRIEVER
# =============================================================================

def load_database():
    """Load the vector database with embeddings."""
    global db, embeddings

    print(f"\n{'='*60}")
    print(f"Loading Vector Database")
    print(f"{'='*60}")
    print(f"Path: {DB_DIR}")

    if not os.path.exists(DB_DIR):
        raise FileNotFoundError(f"Database not found: {DB_DIR}")

    # Load embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}  # Better for cosine similarity
    )

    # Load Chroma database
    db = Chroma(
        persist_directory=DB_DIR,
        embedding_function=embeddings
    )

    doc_count = db._collection.count()
    print(f"Documents loaded: {doc_count}")
    print(f"{'='*60}\n")

    return db


def retrieve_documents(query: str, k: int = RETRIEVAL_K) -> List[Document]:
    """
    Hybrid retrieval: Semantic search + Keyword boosting.
    This ensures documents with exact keyword matches rank higher.
    """
    global db

    print(f"\n--- 🔍 HYBRID RETRIEVAL ---")
    state["latest_retrieval_score"] = 0.0 # Reset per retrieval
    print(f"Original Query: {query}")

    # STEP 0: Preprocess and expand query for better semantic matching
    expanded_query = preprocess_query(query)
    print(f"Expanded Query: {expanded_query[:100]}...")

    # Extract keywords for boosting (from both original and expanded)
    keywords = extract_keywords(query)
    print(f"Keywords for boosting: {keywords}")

    # Step 1: Get MORE candidates via semantic search with EXPANDED query
    try:
        candidates = db.similarity_search_with_score(
            query=expanded_query,  # Use expanded query for better semantic matching
            k=RETRIEVAL_FETCH_K * 2  # Get more candidates for re-ranking
        )
    except Exception as e:
        print(f"Search failed: {e}")
        return []

    print(f"Fetched {len(candidates)} candidates")

    # Step 2: Re-rank with keyword boosting
    scored_docs = []
    for doc, semantic_score in candidates:
        content_lower = doc.page_content.lower()
        topic_lower = doc.metadata.get('topic', '').lower()

        # Calculate keyword boost score
        keyword_boost = 0.0
        for kw in keywords:
            # Strong boost for keyword in topic/filename
            if kw in topic_lower:
                keyword_boost += 0.5
            # Medium boost for keyword in content
            if kw in content_lower:
                keyword_boost += 0.3
            # Extra boost for exact phrase match
            if query.lower() in content_lower:
                keyword_boost += 0.8

        # Penalize generic legal documents for facility queries
        if 'customs act' in topic_lower and any(k in ['smoking', 'lounge', 'wifi', 'sim', 'toilet', 'food'] for k in keywords):
            keyword_boost -= 0.5

        # Combined score (lower semantic_score is better in Chroma)
        # Invert semantic score and add keyword boost
        combined_score = (1.0 / (1.0 + semantic_score)) + keyword_boost

        scored_docs.append((doc, combined_score, semantic_score, keyword_boost))

    # Step 3: Sort by combined score (higher is better)
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    # Capture best score for frontend metrics
    if scored_docs:
        # Normalize score (arbitrary scaling for display: 0.5-2.0 -> 0-100%)
        # Purely for visualization "Confidence"
        best_score = scored_docs[0][1]
        # Cap at 99%, floor at 10%
        normalized = min(99.0, max(10.0, best_score * 50))
        state["latest_retrieval_score"] = round(normalized, 1)

    # Capture best score for frontend metrics
    if scored_docs:
        # Normalize score (arbitrary scaling for display: 0.5-2.0 -> 0-100%)
        # Purely for visualization "Confidence"
        best_score = scored_docs[0][1]
        # Cap at 99%, floor at 10%
        normalized = min(99.0, max(10.0, best_score * 50))
        state["latest_retrieval_score"] = round(normalized, 1)

    # Step 4: Take top k with diversity (skip near-duplicates)
    final_docs = []
    seen_topics = set()
    for doc, combined, semantic, kw_boost in scored_docs:
        topic = doc.metadata.get('topic', '')

        # Skip if we already have 2 docs from same topic (diversity)
        topic_key = topic[:30]  # First 30 chars as key
        if topic_key in seen_topics:
            continue

        final_docs.append(doc)
        seen_topics.add(topic_key)

        if len(final_docs) >= k:
            break

    # Log results
    print(f"Final {len(final_docs)} documents:")
    for i, doc in enumerate(final_docs):
        topic = doc.metadata.get('topic', 'Unknown')
        preview = doc.page_content[:80].replace('\n', ' ')
        print(f"  [{i+1}] {topic}: {preview}...")

    return final_docs


def format_documents(docs: List[Document]) -> str:
    """Format documents with metadata for the LLM."""
    if not docs:
        return "No relevant information found in the database."

    formatted = []
    for i, doc in enumerate(docs):
        topic = doc.metadata.get('topic', 'General')
        source = doc.metadata.get('source', 'TIA Knowledge Base')
        content = doc.page_content.strip()

        formatted.append(f"[Document {i+1}] Topic: {topic}\n{content}")

    return "\n\n---\n\n".join(formatted)


# =============================================================================
# RAG CHAIN
# =============================================================================

# Production RAG Prompt
RAG_PROMPT_TEMPLATE = """You are an expert assistant for Tribhuvan International Airport (TIA) in Kathmandu, Nepal.

INSTRUCTIONS:
1. Answer the question using ONLY the information provided in the context below
2. If the context contains the answer, provide a clear, helpful response
3. If the context does NOT contain the answer, say "I don't have specific information about that in my database"
4. Be concise but complete
5. If relevant, mention the source/topic of the information

CONTEXT FROM TIA DATABASE:
{context}

USER QUESTION: {question}

ANSWER:"""

RAG_PROMPT = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)


def create_rag_chain(llm_instance):
    """Create the RAG chain with advanced retrieval."""

    def retrieve_and_format(query: str) -> str:
        docs = retrieve_documents(query)
        return format_documents(docs)

    rag_chain = (
        {
            "context": RunnableLambda(retrieve_and_format),
            "question": RunnablePassthrough()
        }
        | RAG_PROMPT
        | llm_instance
        | StrOutputParser()
    )

    return rag_chain


# =============================================================================
# LLM SETUP
# =============================================================================

def load_llm():
    """Load the LLM with optimized settings."""
    print(f"Loading LLM: {LLM_MODEL}")

    llm = ChatOllama(
        model=LLM_MODEL,
        temperature=0.1,        # Slight creativity for natural responses
        num_ctx=4096,           # Larger context for RAG
        num_predict=300,        # Allow longer responses
        num_gpu=99,             # Use GPU
        keep_alive="30m",
        top_p=0.9,
        repeat_penalty=1.1,     # Reduce repetition
    )

    print(f"LLM loaded successfully")
    return llm


# =============================================================================
# RAG TOOL (Used by Agent)
# =============================================================================

# Global RAG chain (set during startup)
rag_chain = None


@tool
def get_general_airport_info(query: str) -> str:
    """
    Search the TIA knowledge base for airport information.

    Use this tool for questions about:
    - Airport facilities (lounges, restaurants, shops, ATMs, wifi)
    - Customs and immigration rules
    - Baggage policies and allowances
    - Prohibited items
    - Visa requirements
    - Airport services (medical, prayer rooms, smoking areas)
    - Ground transportation (taxi, bus)
    - Any general TIA airport information

    Args:
        query: The user's question about TIA airport

    Returns:
        Relevant information from the TIA knowledge base
    """
    global rag_chain

    print(f"\n{'='*60}")
    print(f"🧰 RAG TOOL CALLED")
    print(f"Query: {query}")
    print(f"{'='*60}")

    if rag_chain is None:
        return "Error: RAG system not initialized"

    try:
        start = time.time()
        result = rag_chain.invoke(query)
        elapsed = time.time() - start

        print(f"\n--- RAG Response ({elapsed:.2f}s) ---")
        print(f"{result[:200]}...")
        print(f"{'='*60}\n")

        if not result or result.strip() == "":
            return "I couldn't find specific information about that. Please try rephrasing your question."

        return result.strip()

    except Exception as e:
        print(f"❌ RAG Error: {e}")
        return f"Error searching knowledge base: {str(e)}"


# =============================================================================
# AGENT SETUP
# =============================================================================

SYSTEM_MESSAGE = """You are the official AI assistant for Tribhuvan International Airport (TIA) in Kathmandu, Nepal.

YOUR TOOLS:
1. get_general_airport_info - Search TIA knowledge base for:
   - Facilities (lounges, restaurants, ATMs, wifi, smoking areas)
   - Customs/immigration rules and prohibited items
   - Baggage policies
   - Visa requirements
   - Airport services
   - Ground transportation

2. get_flight_status_from_json - Get status of a SPECIFIC flight by code (e.g., RA205, FZ575)

3. search_flights_by_route - Search flights by city name (e.g., "flights from Dubai")

4. get_kathmandu_weather_openmeteo - Get current Kathmandu weather

RULES:
- ALWAYS use get_general_airport_info for questions about airport facilities, rules, or services
- Use flight tools ONLY for flight-specific queries
- Be helpful, accurate, and concise
- If you cannot find information, say so honestly
"""


def create_agent(llm_instance, tools_list):
    """Create the ReAct agent."""
    print("Creating ReAct Agent...")

    memory = MemorySaver()

    agent = create_react_agent(
        model=llm_instance,
        tools=tools_list,
        prompt=SYSTEM_MESSAGE,
        checkpointer=memory,
    )

    print(f"Agent created with {len(tools_list)} tools")
    return agent


# =============================================================================
# FASTAPI LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all components on startup."""
    global db, llm, rag_chain, agent_executor

    print("\n" + "="*60)
    print("🚀 TIA SMART ARRIVAL BACKEND")
    print("="*60 + "\n")

    # 1. Load database
    db = load_database()

    # 2. Load LLM
    llm = load_llm()

    # 3. Create RAG chain
    rag_chain = create_rag_chain(llm)
    print("RAG chain created")

    # 4. Build tools
    tools = [
        get_general_airport_info,
        get_flight_status_from_json,
        get_kathmandu_weather_openmeteo,
        search_flights_by_route
    ]

    if KYC_AVAILABLE and process_sim_card_kyc:
        tools.append(process_sim_card_kyc)
        print("KYC tool added")

    # 5. Create agent
    agent_executor = create_agent(llm, tools)

    # 6. Test RAG
    print("\n--- Testing RAG System ---")
    test_result = rag_chain.invoke("smoking area")
    print(f"Test query 'smoking area': {test_result[:100]}...")

    print("\n" + "="*60)
    print("✅ BACKEND READY")
    print("="*60 + "\n")

    yield

    print("Shutting down...")


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="TIA Smart Arrival API",
    description="Production RAG Backend for TIA Airport",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# MODELS
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    language: str
    execution_time: float
    confidence_score: float = 0.0
    metadata: Optional[dict] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    return {"status": "online", "service": "TIA Smart Arrival", "version": "3.0.0"}


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "db_loaded": db is not None,
        "llm_loaded": llm is not None,
        "rag_ready": rag_chain is not None,
        "agent_ready": agent_executor is not None,
        "doc_count": db._collection.count() if db else 0
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat messages through the agent."""
    global agent_executor

    if not agent_executor:
        raise HTTPException(status_code=503, detail="Agent not ready")

    start_time = time.time()

    try:
        # Detect language
        lang = detect_language(request.message)

        # Translate if Nepali
        if lang == 'ne':
            query = translate_to_english(request.message)
        else:
            query = request.message

        print(f"\n{'='*60}")
        print(f"📨 CHAT REQUEST")
        print(f"Original: {request.message}")
        print(f"Query: {query}")
        print(f"{'='*60}")

        # Run agent
        config = {"configurable": {"thread_id": request.thread_id}}
        response = agent_executor.invoke(
            {"messages": [{"role": "user", "content": query}]},
            config
        )

        # Extract response
        messages = response.get("messages", [])
        answer = messages[-1].content if messages else "No response"

        # Translate back if needed
        if lang == 'ne':
            answer = translate_to_nepali(answer)

        elapsed = time.time() - start_time

        print(f"\n✅ Response ({elapsed:.2f}s): {answer[:100]}...")

        return ChatResponse(
            response=answer,
            language=lang,
            execution_time=elapsed,
            confidence_score=state["latest_retrieval_score"],
            metadata={"query": query}
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/weather")
async def weather():
    """
    Fetch current Kathmandu weather for UI display.
    Returns structured data (not the formatted string the chatbot uses).
    """
    try:
        import requests

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 27.7172,
            "longitude": 85.3240,
            "current_weather": True,
            "timezone": "Asia/Kathmandu"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data.get("current_weather", {})
        temp = current.get("temperature", 18)
        weathercode = current.get("weathercode", 0)

        # Weather code to condition mapping
        weather_conditions = {
            0: "Clear Sky",
            1: "Mainly Clear",
            2: "Partly Cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Foggy",
            51: "Light Drizzle",
            53: "Drizzle",
            55: "Dense Drizzle",
            61: "Light Rain",
            63: "Rain",
            65: "Heavy Rain",
            80: "Rain Showers",
            81: "Rain Showers",
            82: "Heavy Showers",
            95: "Thunderstorm",
        }

        condition = weather_conditions.get(weathercode, "Partly Cloudy")

        return {
            "status": "success",
            "data": {
                "temperature": round(temp),
                "condition": condition
            }
        }
    except Exception as e:
        print(f"Weather Error: {e}")
        return {
            "status": "error",
            "data": {
                "temperature": 22,
                "condition": "Pleasant"
            }
        }

@app.get("/api/evaluation")
async def get_evaluation_results():
    """
    Fetch the latest REAL evaluation results from the 'evaluation/results' folder.
    This ensures the frontend displays legitimate data from 'evaluate_e2e.py'.
    """
    try:
        # Prepare consolidated report
        consolidated_report = {
            "e2e": {},
            "document_ai": {},
            "boarding_pass": {}
        }

        # 1. Fetch E2E (RAG) Report
        results_dir = os.path.join(PARENT_DIR, "evaluation", "results")
        e2e_pattern = os.path.join(results_dir, "evaluation_report_*.json")
        e2e_files = glob.glob(e2e_pattern)
        
        if e2e_files:
            latest_e2e = max(e2e_files, key=os.path.getctime)
            with open(latest_e2e, 'r', encoding='utf-8') as f:
                consolidated_report["e2e"] = json.load(f)

        # 2. Fetch Document AI (KYC) Report
        doc_pattern = os.path.join(results_dir, "document_ai_eval_*.json")
        doc_files = glob.glob(doc_pattern)
        
        if doc_files:
            latest_doc = max(doc_files, key=os.path.getctime)
            with open(latest_doc, 'r', encoding='utf-8') as f:
                consolidated_report["document_ai"] = json.load(f)

        # 3. Fetch Boarding Pass OCR Report
        pass_pattern = os.path.join(results_dir, "boarding_pass_eval_*.json")
        pass_files = glob.glob(pass_pattern)
        
        if pass_files:
            latest_pass = max(pass_files, key=os.path.getctime)
            with open(latest_pass, 'r', encoding='utf-8') as f:
                consolidated_report["boarding_pass"] = json.load(f)

        return consolidated_report

    except Exception as e:
        print(f"Error serving evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/api/flights")
async def flights():
    try:
        if os.path.exists(FLIGHT_CACHE_FILE):
            with open(FLIGHT_CACHE_FILE) as f:
                data = json.load(f)
            return {"flights": data.get("arrivals", []) + data.get("departures", [])}
    except:
        pass
    return {"flights": []}


@app.post("/api/rag/test")
async def test_rag(query: str = "smoking area"):
    """Direct RAG test endpoint for debugging."""
    if not rag_chain:
        return {"error": "RAG not initialized"}

    docs = retrieve_documents(query)
    result = rag_chain.invoke(query)

    return {
        "query": query,
        "documents": [{"topic": d.metadata.get("topic"), "content": d.page_content[:200]} for d in docs],
        "response": result
    }


# =============================================================================
# DOCUMENT AI ENDPOINTS (KYC & Boarding Pass)
# =============================================================================

TEMP_DIR = os.path.join(PARENT_DIR, "temp_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)


def generate_qr_base64(data: dict) -> str:
    """Generate QR code and return as base64 string."""
    if not QR_AVAILABLE:
        return None

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(json.dumps(data))
    qr.make(fit=True)

    img = qr.make_image(fill_color="#00A67E", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode('utf-8')


@app.post("/api/kyc/verify")
async def verify_kyc(
    passport: UploadFile = File(...),
    selfie: UploadFile = File(...)
):
    """
    SIM Card KYC Verification Endpoint

    Performs ICAO 9303 MRZ validation and face recognition.
    Returns verification result with QR code for kiosk collection.
    """
    if not KYC_AVAILABLE:
        raise HTTPException(status_code=503, detail="KYC service not available")

    print(f"\n{'='*60}")
    print("KYC VERIFICATION REQUEST")
    print(f"{'='*60}")

    try:
        # Save uploaded files temporarily
        passport_path = os.path.join(TEMP_DIR, "kyc_passport.jpg")
        selfie_path = os.path.join(TEMP_DIR, "kyc_selfie.jpg")

        with open(passport_path, "wb") as f:
            content = await passport.read()
            f.write(content)

        with open(selfie_path, "wb") as f:
            content = await selfie.read()
            f.write(content)

        print(f"Files saved: {passport_path}, {selfie_path}")

        # Run KYC verification
        start_time = time.time()
        result_json = process_sim_card_kyc.invoke({
            "passport_path": passport_path,
            "selfie_path": selfie_path
        })
        elapsed = time.time() - start_time

        result = json.loads(result_json)

        # Generate QR code if approved
        qr_code = None
        if result.get("verification_status") == "APPROVED" and QR_AVAILABLE:
            qr_data = {
                "type": "TIA_SIM_TOKEN",
                "passport": result.get("extracted_mrz_data", {}).get("passport_number", ""),
                "phone": result.get("sim_details", {}).get("phone_number", ""),
                "plan": result.get("sim_details", {}).get("plan", ""),
                "timestamp": int(time.time())
            }
            qr_code = generate_qr_base64(qr_data)

        print(f"KYC Result: {result.get('verification_status')} ({elapsed:.2f}s)")

        # Cleanup temp files
        for path in [passport_path, selfie_path]:
            if os.path.exists(path):
                os.remove(path)

        return {
            "status": result.get("verification_status", "ERROR").lower(),
            "message": result.get("error") or "Verification complete",
            "security_checks": result.get("security_checks", {}),
            "face_match_confidence": result.get("face_match_confidence", 0),
            "sim_details": result.get("sim_details"),
            "passport_data": result.get("extracted_mrz_data"),
            "qr_code": qr_code,
            "processing_time": elapsed
        }

    except Exception as e:
        print(f"KYC Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/boarding-pass/scan")
async def scan_boarding_pass_endpoint(
    image: UploadFile = File(...)
):
    """
    Boarding Pass Scanner Endpoint

    Extracts flight information from boarding pass image using OCR.
    Returns structured data and live flight status.
    """
    if not BOARDING_PASS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Boarding pass scanner not available")

    print(f"\n{'='*60}")
    print("BOARDING PASS SCAN REQUEST")
    print(f"{'='*60}")

    try:
        # Save uploaded file temporarily
        image_path = os.path.join(TEMP_DIR, "boarding_pass.jpg")

        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)

        print(f"Image saved: {image_path}")

        # Run boarding pass scanner
        start_time = time.time()
        result_json = scan_boarding_pass.invoke(image_path)
        elapsed = time.time() - start_time

        result = json.loads(result_json)

        print(f"Scan Result: {result.get('status')} ({elapsed:.2f}s)")

        # Cleanup
        if os.path.exists(image_path):
            os.remove(image_path)

        return {
            "status": result.get("status", "error"),
            "message": result.get("message"),
            "boarding_pass": result.get("boarding_pass"),
            "flight_status": result.get("flight_status"),
            "processing_time": elapsed
        }

    except Exception as e:
        print(f"Boarding Pass Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/services/status")
async def services_status():
    """Check which Document AI services are available."""
    return {
        "kyc": {
            "available": KYC_AVAILABLE,
            "description": "SIM Card KYC with ICAO 9303 MRZ validation"
        },
        "boarding_pass": {
            "available": BOARDING_PASS_AVAILABLE,
            "description": "Boarding Pass OCR Scanner"
        },
        "qr_generation": {
            "available": QR_AVAILABLE,
            "description": "QR Code generation for kiosk"
        }
    }


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
