import os
import time
import streamlit as st
from dotenv import load_dotenv
from typing import Generator
import re
import json
from io import BytesIO
from datetime import datetime, timedelta
import concurrent.futures  # Add this import for timeout handling

# --- 1. LOAD ENV VARS FIRST ---
load_dotenv() 

# --- 2. IMPORT API/TRANSLATION TOOLS ---
try:
    from flight_tools import (
        get_flight_status_from_json, 
        get_kathmandu_weather_openmeteo,
        search_flights_by_route
    )
except ImportError as e:
    st.error(f"❌ flight_tools.py not found or has errors: {e}")
    st.stop()

try:
    from translation_tools import detect_language, translate_to_english, translate_to_nepali
except ImportError:
    st.error("❌ translation_tools.py not found. Please place it in same folder.")
    st.stop()

try:
    from kyc_tools import process_sim_card_kyc
except ImportError:
    st.warning("⚠️ kyc_tools.py not found. KYC features will be disabled.")
    process_sim_card_kyc = None

try:
    from boarding_pass_tools import scan_boarding_pass, format_boarding_pass_result
    BOARDING_PASS_AVAILABLE = True
except ImportError:
    st.warning("⚠️ boarding_pass_tools.py not found. Boarding pass scanner will be disabled.")
    scan_boarding_pass = None
    format_boarding_pass_result = None
    BOARDING_PASS_AVAILABLE = False

# --- QR Code Import ---
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

# --- Flight Data Engine Import ---
try:
    from flight_data_engine import update_cache
    FLIGHT_ENGINE_AVAILABLE = True
except ImportError:
    FLIGHT_ENGINE_AVAILABLE = False
    print("⚠️ flight_data_engine.py not found. Using cached/static flight data.")

# --- 3. LANGCHAIN IMPORTS ---
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool 

# --- 4. LANGGRAPH AGENT IMPORTS ---
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

# --- Configuration ---
DB_DIR = "db"
MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL = "qwen2.5:3b"  # PERFORMANCE UPGRADE: Faster model with reliable tool use

# =============================================================================
# FLIGHT DATA CACHE MANAGEMENT
# =============================================================================

FLIGHT_CACHE_FILE = "flight_cache.json"
CACHE_MAX_AGE_MINUTES = 30  # Refresh cache if older than 30 minutes


def get_cache_age_minutes() -> float:
    """Returns the age of the flight cache in minutes, or infinity if missing."""
    if not os.path.exists(FLIGHT_CACHE_FILE):
        return float('inf')
    
    try:
        with open(FLIGHT_CACHE_FILE, 'r') as f:
            data = json.load(f)
        
        last_updated_str = data.get("last_updated", "")
        if not last_updated_str:
            return float('inf')
        
        # Parse the timestamp (format: "2025-11-26 17:54:22")
        last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
        age = datetime.now() - last_updated
        return age.total_seconds() / 60  # Convert to minutes
        
    except (json.JSONDecodeError, ValueError, KeyError):
        return float('inf')


@st.cache_resource(ttl=CACHE_MAX_AGE_MINUTES * 60)
def refresh_flight_cache_if_needed() -> dict:
    """
    Checks if flight cache needs refresh and updates it.
    """
    cache_age = get_cache_age_minutes()
    result = {
        "refreshed": False,
        "cache_age_minutes": cache_age,
        "source": "unknown"
    }
    
    needs_refresh = (
        not os.path.exists(FLIGHT_CACHE_FILE) or 
        cache_age > CACHE_MAX_AGE_MINUTES
    )
    
    # CRITICAL FIX: Check both the flag AND the function existence
    if needs_refresh and FLIGHT_ENGINE_AVAILABLE and update_cache is not None:
        print(f"\n--- 🔄 Flight Cache Refresh Triggered ---")
        print(f"    Cache age: {cache_age:.1f} minutes (max: {CACHE_MAX_AGE_MINUTES})")
        
        try:
            update_cache()
            result["refreshed"] = True
            result["source"] = "AviationStack API"
            print(f"    ✅ Cache refreshed successfully!")
        except Exception as e:
            print(f"    ❌ Cache refresh failed: {e}")
            result["source"] = "refresh_failed"
    else:
        if not FLIGHT_ENGINE_AVAILABLE:
            result["source"] = "engine_unavailable"
        else:
            result["source"] = "cache_valid"
            print(f"--- ✅ Flight cache is fresh ({cache_age:.1f} min old) ---")
    
    return result


def check_and_refresh_flights():
    """
    Main function to check flight cache status and refresh if needed.
    Shows toast notification when refresh occurs.
    """
    # Initialize refresh tracking in session state
    if "last_cache_check" not in st.session_state:
        st.session_state["last_cache_check"] = None
    
    # Get cache status (this is cached, so won't run every time)
    cache_status = refresh_flight_cache_if_needed()
    
    # Show toast notification only once per refresh
    if cache_status["refreshed"]:
        if st.session_state["last_cache_check"] != datetime.now().strftime("%Y-%m-%d %H:%M"):
            st.toast("🔄 Flight Data Updated from Live API!", icon="✈️")
            st.session_state["last_cache_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return cache_status


# =============================================================================
# HELPER FUNCTIONS (MOVED TO TOP)
# =============================================================================

def extract_and_protect_flight_code(query: str) -> tuple[str, str | None]:
    """
    Finds a flight code in the query, extracts it, and replaces it
    with a placeholder to protect it from translation.
    """
    pattern = r'\b([A-Z0-9]{1,3})\s?(\d{3,4})\b'
    match = re.search(pattern, query.upper())
    if match:
        flight_code = f"{match.group(1)}{match.group(2)}" 
        safe_query = re.sub(pattern, "[FLIGHT]", query, flags=re.IGNORECASE)
        print(f"--- 🛡️ Protecting flight code: {flight_code} ---")
        return safe_query, flight_code
    return query, None

def generate_sim_qr(sim_details: dict, passport_num: str) -> bytes:
    """Generates a QR code for SIM card collection at the TIA Kiosk."""
    # Create the kiosk token payload
    qr_payload = {
        "type": "TIA_SIM_TOKEN",
        "passport": passport_num,
        "phone": sim_details.get("phone_number", "Unknown"),
        "plan": sim_details.get("plan", "Tourist SIM - 30 Days"),
        "carrier": sim_details.get("carrier", "Nepal Telecom"),
        "data": sim_details.get("data", "5GB 4G"),
        "validity": sim_details.get("validity", "30 Days"),
        "security_level": sim_details.get("security_level", "ICAO 9303 Verified"),
        "timestamp": str(int(time.time()))
    }
    
    # Convert to JSON string
    json_data = json.dumps(qr_payload)
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(json_data)
    qr.make(fit=True)
    
    # Create image with custom colors (TIA green theme)
    qr_image = qr.make_image(fill_color="#00A67E", back_color="white")
    
    # Convert to bytes
    img_buffer = BytesIO()
    qr_image.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer.getvalue()

def display_sim_approval_with_qr(kyc_result: dict):
    """Displays a professional SIM approval card with QR code for kiosk collection."""
    sim_details = kyc_result.get("sim_details", {})
    passport_num = kyc_result.get("extracted_mrz_data", {}).get("passport_number", "Unknown")
    
    # Create approval UI
    st.success("✅ **KYC VERIFICATION APPROVED**")
    
    # Display SIM details in a nice card format
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📱 Your SIM Card Details")
        st.markdown(f"""
        | Field | Value |
        |-------|-------|
        | **Phone Number** | `{sim_details.get('phone_number', 'N/A')}` |
        | **Carrier** | {sim_details.get('carrier', 'Nepal Telecom')} |
        | **Plan** | {sim_details.get('plan', 'Tourist SIM')} |
        | **Data** | {sim_details.get('data', '5GB')} |
        | **Validity** | {sim_details.get('validity', '30 Days')} |
        | **Status** | ✅ {sim_details.get('activation_status', 'READY')} |
        """)
        st.info("📍 **Next Step:** Scan the QR code at any TIA SIM Kiosk to collect your physical SIM card.")
    
    with col2:
        if QR_AVAILABLE:
            st.markdown("### 🔲 Kiosk QR Code")
            qr_bytes = generate_sim_qr(sim_details, passport_num)
            st.image(qr_bytes, caption="Scan at TIA Kiosk", width=200)
            
            st.download_button(
                label="📥 Save QR Code",
                data=qr_bytes,
                file_name="tia_sim_token.png",
                mime="image/png",
                use_container_width=True
            )
        else:
            st.warning("QR code generation unavailable. Please install: `pip install qrcode[pil]`")

# --- CUSTOM CSS INJECTION (GLASSMORPHISM THEME) ---
def inject_custom_css():
    st.markdown("""
    <style>
    /* Hide Streamlit's top elements */
    .stAppDeployButton {display: none;}
    div[data-testid="stToolbar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Reduce top padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        max-width: 100%;
    }
    
    /* Chat message styling - Glassmorphism */
    .stChatMessage[data-testid="user-message"] {
        background: linear-gradient(135deg, rgba(0, 166, 126, 0.1) 0%, rgba(0, 166, 126, 0.05) 100%);
        border: 1px solid rgba(0, 166, 126, 0.2);
        border-radius: 16px;
        backdrop-filter: blur(10px);
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .stChatMessage[data-testid="assistant-message"] {
        background: linear-gradient(135deg, rgba(38, 39, 48, 0.8) 0%, rgba(38, 39, 48, 0.4) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        backdrop-filter: blur(10px);
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #262730 0%, #1a1b23 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #00A67E 0%, #008C6A 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 166, 126, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 166, 126, 0.4);
    }
    
    /* Input field styling */
    .stTextInput>div>div>input, .stChatInput>div>input {
        background: rgba(38, 39, 48, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #FAFAFA;
    }
    
    /* Title styling */
    h1 {
        background: linear-gradient(135deg, #00A67E 0%, #00D4AA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    /* Divider styling */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(0, 166, 126, 0.3) 50%, transparent 100%);
        margin: 2rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Load the "Brain" (Vector Database) ---
@st.cache_resource(show_spinner=False)
def load_retriever():
    print("Loading vector database...")
    model_kwargs = {"device": "cpu"}
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME, model_kwargs=model_kwargs)
    db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 4})
    print("Vector database loaded.")
    return retriever

@st.cache_resource(show_spinner=False)
def load_llm():
    print(f"Loading LLM: {LLM_MODEL}...")
    llm = ChatOllama(model=LLM_MODEL, stream=False, temperature=0)
    print(f"LLM loaded: {LLM_MODEL}")
    return llm

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# --- Set up the RAG Prompt Template ---
prompt_template = """
You are a document summarizer for TIA Airport.
Use the following "Context" to provide a direct, factual answer to the "Question".

Context:
\"""
{context}
\"""

Question:
\"""
{question}
\"""

Rules:
1. Answer ONLY based on the Context above.
2. Do not use outside knowledge.
3. If the context does not contain the answer, strictly say:
   "I'm sorry, I don't have that information in my knowledge base."

Factual Answer:
"""
prompt = ChatPromptTemplate.from_template(prompt_template)

# --- Create the RAG Chain ---
try:
    retriever = load_retriever()
    llm = load_llm()

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    print("RAG chain created successfully.")

except Exception as e:
    print(f"Error creating RAG chain: {e}")
    st.error(
        f"Error initializing the chatbot. Please ensure Ollama is running and the 'db' folder exists. Error: {e}"
    )
    st.stop()

# --- TOOL 3: RAG Tool ---
@tool
def get_general_airport_info(query: str) -> str:
    """
    Use this tool for all general questions about TIA airport rules, regulations, 
    facilities, baggage allowances, customs, and prohibited items.
    
    *** CRITICAL: DO NOT USE THIS TOOL ***
    - If the user asks for a specific flight status (e.g., "RA205").
    - If the user asks for the weather.
    - If the user asks for flights from a city (use search_flights_by_route instead).
    - If the user asks for SIM card KYC (use process_sim_card_kyc instead).
    
    Use the other tools for flight status, weather, flight search, and KYC.
    """
    print(f"🧰 TOOL USED: get_general_airport_info for query '{query}'")
    try:
        result = rag_chain.invoke(query)
        if not result or result.strip() == "":
            return (
                "I'm sorry, I couldn't find relevant information in my database. "
                "Please contact the airport directly."
            )
        return result.strip()
    except Exception as e:
        return f"Error retrieving general information: {e}"

# --- UPDATED SYSTEM MESSAGE ---
SYSTEM_MESSAGE = """
✅ --- STRICT SYSTEM MESSAGE --- ✅

Namaste! You are a helpful and polite Virtual Help Desk assistant for
Tribhuvan International Airport (TIA), Kathmandu - part of the Smart Arrival Ecosystem.

You have SIX tools. You must use them as follows:

1.  **Specific Flight Status** (e.g., "RA205", "SQ700"):
    → Use get_flight_status_from_json

2.  **Flight Search by Route** (e.g., "flights from Dubai", "planes from Singapore"):
    → Use search_flights_by_route with the origin city
    → Do NOT hallucinate flight numbers. Let the tool find them.

3.  **Weather**:
    → Use get_kathmandu_weather_openmeteo

4.  **SIM Card / KYC Verification**:
    → If the user asks about getting a SIM card or mobile connection:
      a) FIRST check if documents are uploaded (passport and selfie in sidebar)
      b) If NOT uploaded: Tell the user "Please upload your passport photo and take a selfie in the sidebar's 'Document AI' section first."
      c) If uploaded: Use process_sim_card_kyc with paths 'temp_passport.jpg' and 'temp_selfie.jpg'
    → Present the KYC result clearly (approved/rejected, phone number if approved)

5.  **Boarding Pass Scanner**:
    → If the user uploads a boarding pass image or asks to scan their boarding pass:
      a) FIRST check if boarding pass is uploaded (check sidebar 'Document AI' section)
      b) If NOT uploaded: Tell the user "Please upload your boarding pass photo in the sidebar's 'Document AI' section first."
      c) If uploaded: Use scan_boarding_pass with path 'temp_boarding_pass.jpg'
    → Present the extracted flight details and any live flight status

6.  **General Airport Info** (rules, customs, baggage, facilities):
    → Use get_general_airport_info

⚠️ --- CRITICAL EXECUTION RULES --- ⚠️

-   **MANDATORY TOOL USE:** You MUST ALWAYS use one of the tools.
-   **NO INTERNAL KNOWLEDGE:** Your own pre-trained knowledge is FORBIDDEN. 
    Do NOT answer questions about visa fees, taxi locations, or lounge prices 
    from your memory. You must rely *only* on the tool outputs.

-   **NO FLIGHT HALLUCINATION:** When user asks "flights from Dubai" (no number),
    use search_flights_by_route. Do NOT make up flight numbers.

-   **RAG TOOL RULE:** When you use get_general_airport_info, the tool's
    output IS the final, correct answer. Return it VERBATIM.

🚀 --- PARALLEL MULTI-TASK EXECUTION (CRITICAL) --- 🚀

-   **MULTI-QUESTION DETECTION:** If the user asks multiple, distinct questions 
    in a single message (e.g., "What is the status of RA205 and how is the weather?"),
    you MUST identify ALL required tools in your first reasoning step.

-   **SEQUENTIAL TOOL CALLS:** For multi-part queries, call each tool SEPARATELY 
    and SEQUENTIALLY. Do NOT try to consolidate different task types into one call.
    
    Example for "Status of RA205 and weather in Kathmandu?":
    - First call: get_flight_status_from_json("RA205")
    - Second call: get_kathmandu_weather_openmeteo()
    - Then combine both results in your final answer.

-   **TASK TYPE SEPARATION:** Never use get_general_airport_info for flight status 
    or weather queries. Each tool has a specific purpose - use the right tool for 
    each distinct question.

-   **EFFICIENCY:** Complete all tool calls quickly. Do not overthink or repeat calls.

-   **KYC RULE:** For SIM card requests, ALWAYS check if documents are ready first.
    Guide users to the sidebar if documents are not uploaded.

-   **LANGUAGE RULE (CRITICAL):** Your final response MUST be in **ENGLISH**. 
    Do not add conversational fillers. Just provide the direct answer.
"""

# =============================================================================
# CACHED AGENT EXECUTOR (PERFORMANCE OPTIMIZATION)
# =============================================================================

@st.cache_resource(show_spinner="🤖 Initializing AI Agent...")
def load_agent_executor(_llm_instance, _tools_list: tuple, system_prompt: str):
    """
    Creates and caches the ReAct agent executor for maximum performance.
    
    Args:
        _llm_instance: The LLM instance (underscore prefix tells Streamlit not to hash it)
        _tools_list: Tuple of tools (must be tuple for hashing)
        system_prompt: The system message string
    
    Returns:
        The configured agent executor
    """
    print(f"\n--- 🚀 Creating Cached Agent Executor ---")
    print(f"    Model: {LLM_MODEL}")
    print(f"    Tools: {len(_tools_list)} available")
    
    memory = MemorySaver()
    
    agent = create_agent(
        model=_llm_instance,
        tools=list(_tools_list),  # Convert back to list for create_agent
        system_prompt=system_prompt,
        checkpointer=memory,
    )
    
    print(f"    ✅ Agent cached and ready!")
    return agent


# --- Build Tools List ---
tools_list = [
    get_flight_status_from_json,
    get_kathmandu_weather_openmeteo,
    get_general_airport_info,
    search_flights_by_route
]

if process_sim_card_kyc is not None:
    tools_list.append(process_sim_card_kyc)
    print("✅ KYC tool added to agent.")

if scan_boarding_pass is not None:
    tools_list.append(scan_boarding_pass)
    print("✅ Boarding Pass Scanner tool added to agent.")

# --- Instantiate Cached Agent ---
try:
    # Convert to tuple for caching (lists aren't hashable)
    agent_executor = load_agent_executor(llm, tuple(tools_list), SYSTEM_MESSAGE)
    print("✅ ReAct Agent ready with memory.")
except Exception as e:
    st.error(f"Failed to create agent: {e}")
    st.stop()

# =============================================================================
# AGENT INVOCATION (Direct - No Timeout)
# =============================================================================

def invoke_agent_direct(agent, inputs: dict, config: dict):
    """
    Invokes the agent directly without timeout wrapper.
    
    Args:
        agent: The agent executor instance
        inputs: The input messages dict
        config: The agent config with thread_id
    
    Returns:
        tuple: (success: bool, result: str, execution_time: float)
    """
    start_time = time.time()
    
    try:
        response = agent.invoke(inputs, config)
        execution_time = time.time() - start_time
        
        # Safe extraction of response
        last_message = response.get("messages", [])[-1]
        answer = getattr(last_message, "content", str(last_message)).strip()
        
        if not answer:
            answer = "I'm sorry, I don't have that information. Please contact the airport."
        
        print(f"⏱️ Agent completed in {execution_time:.2f}s")
        return (True, answer, execution_time)
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ Agent ERROR after {execution_time:.2f}s: {e}")
        return (False, f"An error occurred: {str(e)}", execution_time)

# =============================================================================
# MODAL DIALOG FOR KYC
# =============================================================================

@st.dialog("🔐 Secure KYC Portal", width="large")
def kyc_verification_modal():
    """Professional modal dialog for KYC document verification."""
    st.markdown("### Identity Verification")
    st.caption("Upload your passport and take a live selfie for instant SIM card activation")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Passport Photo")
        passport_file = st.file_uploader(
            "Upload a clear photo of your passport's photo page",
            type=["jpg", "jpeg", "png"],
            key="modal_passport_uploader",
            label_visibility="collapsed"
        )
        
        if passport_file:
            st.image(passport_file, caption="✅ Passport Uploaded", use_container_width=True)
    
    with col2:
        st.markdown("#### 📸 Live Selfie")
        selfie_file = st.camera_input(
            "Take a selfie matching your passport photo",
            key="modal_selfie_camera",
            label_visibility="collapsed"
        )
        
        if selfie_file:
            st.image(selfie_file, caption="✅ Selfie Captured", use_container_width=True)
    
    st.divider()
    
    if passport_file and selfie_file:
        # Both documents are ready - show the submit button
        st.success("✅ Both documents captured successfully!")
        st.info("📋 Click the button below to start ICAO 9303 MRZ validation and biometric verification.")
        
        if st.button("✅ Submit & Verify Identity", type="primary", use_container_width=True):
            try:
                # Save files to disk
                with open("temp_passport.jpg", "wb") as f:
                    f.write(passport_file.getbuffer())
                
                with open("temp_selfie.jpg", "wb") as f:
                    f.write(selfie_file.getbuffer())
                
                # Set session state flags
                st.session_state["kyc_documents_ready"] = True
                
                # Auto-trigger the KYC verification query
                st.session_state["trigger_query"] = "Verify my KYC for SIM card"
                
                # Rerun to close modal and trigger verification
                st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Error saving files: {e}")
                st.session_state["kyc_documents_ready"] = False
    else:
        st.session_state["kyc_documents_ready"] = False
        if passport_file:
            st.warning("📸 Now take a selfie to complete verification")
        elif selfie_file:
            st.warning("📄 Now upload your passport photo")
        else:
            st.info("👆 Start by uploading your passport photo")

# =============================================================================
# MAIN APPLICATION
# =============================================================================

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="TIA Smart Arrival",
    page_icon="🇳🇵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# AUTOMATIC FLIGHT DATA REFRESH (runs before UI loads)
# =============================================================================

# Check and refresh flight cache if needed
if FLIGHT_ENGINE_AVAILABLE:
    cache_status = check_and_refresh_flights()
    
    # Debug info (visible in terminal)
    if cache_status["refreshed"]:
        print(f"🔄 Flight data refreshed from {cache_status['source']}")
else:
    print("⚠️ Flight data engine not available - using existing cache")

# Inject Custom CSS
inject_custom_css()

# --- Header ---
st.title("🇳🇵 TIA Smart Arrival Ecosystem")
st.caption("नेपालीमा वा अंग्रेजीमा सोध्नुहोस् | Ask in Nepali or English")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = "tia_chat_session_v1"

if "kyc_documents_ready" not in st.session_state:
    st.session_state["kyc_documents_ready"] = False

# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input (with Auto-Trigger Support) ---
# Check for auto-triggered query from KYC modal
user_question = None

if "trigger_query" in st.session_state:
    # Pop the trigger query (use it once, then remove)
    user_question = st.session_state.pop("trigger_query")
    print(f"--- 🚀 Auto-triggered query: {user_question} ---")
else:
    # Normal chat input
    user_question = st.chat_input("Ask about TIA... | TIA बारे सोध्नुहोस्...")

# Process the question (from either source)
if user_question:

    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # --- "TRANSLATION SANDWICH" AROUND THE AGENT ---
    with st.chat_message("assistant"):
        with st.spinner("Thinking... | सोच्दै..."):
            try:
                # 1. Detect Language
                lang = detect_language(user_question)
                
                # 2. Extract and Protect Flight Code
                safe_query, extracted_code = extract_and_protect_flight_code(user_question)
                
                # 3. Translate to English
                if lang == 'ne':
                    english_query_template = translate_to_english(safe_query)
                else:
                    english_query_template = safe_query

                # 4. Re-insert flight code
                if extracted_code:
                    english_query = english_query_template.replace("[FLIGHT]", extracted_code, 1)
                else:
                    english_query = english_query_template
                
                # 5. Add KYC context
                sim_keywords = ["sim", "mobile", "phone", "kyc", "verification", "सिम", "मोबाइल"]
                if any(kw in user_question.lower() for kw in sim_keywords):
                    if st.session_state.get("kyc_documents_ready", False):
                        english_query += " [CONTEXT: User has uploaded passport and selfie. Documents are ready at 'temp_passport.jpg' and 'temp_selfie.jpg']"
                    else:
                        english_query += " [CONTEXT: User has NOT uploaded documents yet. Guide them to the sidebar.]"
                
                if lang == 'ne':
                    st.info(f"*(Translating: {english_query[:100]}...)*")
                
                # 6. Run the AGENT with TIMEOUT PROTECTION
                config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
                inputs = {"messages": [{"role": "user", "content": english_query}]}

                print("\n--- 🤖 Agent is Invoked... ---\n")
                
                # Direct agent invocation (no timeout)
                success, english_answer, execution_time = invoke_agent_direct(
                    agent_executor, 
                    inputs, 
                    config
                )
                
                # Log performance metrics
                if execution_time > 10:
                    print(f"⚠️ SLOW QUERY: {execution_time:.2f}s - Consider query optimization")
                
                # Initialize KYC variables before the conditional
                kyc_approved = False
                kyc_result = None
                
                # Handle timeout case
                if not success:
                    st.warning(english_answer)
                    st.session_state.messages.append({"role": "assistant", "content": english_answer})
                    print("\n--- ⏱️ Agent Timed Out. ---\n")
                else:
                    # 7. Check for KYC Approval & Display QR
                    # Check if the response indicates success
                    if "READY FOR ACTIVATION" in english_answer or "APPROVED" in english_answer or "successfully approved" in english_answer:
                        # STRATEGY 1: Try to find raw JSON in the response
                        try:
                            json_match = re.search(r'\{[\s\S]*"verification_status"[\s\S]*\}', english_answer)
                            if json_match:
                                kyc_result = json.loads(json_match.group())
                                if kyc_result.get("verification_status") == "APPROVED":
                                    kyc_approved = True
                        except (json.JSONDecodeError, AttributeError):
                            pass
                        
                        # STRATEGY 2: Fallback - Extract details from text if JSON failed
                        if not kyc_approved:
                            # Use Regex to scrape the details from the agent's text summary
                            phone_match = re.search(r"Phone Number:\s*([+\d-]+)", english_answer)
                            passport_match = re.search(r"Passport Number:\s*([A-Z0-9]+)", english_answer)
                            plan_match = re.search(r"Plan:\s*(.+?)(?:\n|$)", english_answer)
                            
                            if phone_match: # If we at least have a phone number, treat it as success
                                kyc_approved = True
                                kyc_result = {
                                    "verification_status": "APPROVED",
                                    "sim_details": {
                                        "phone_number": phone_match.group(1) if phone_match else "Unknown",
                                        "carrier": "Nepal Telecom (NTC)", # Default assumption or extract
                                        "plan": plan_match.group(1).strip() if plan_match else "Tourist SIM",
                                        "data": "5GB 4G Data", # Default/Placeholder
                                        "validity": "30 Days", # Default/Placeholder
                                        "activation_status": "READY FOR ACTIVATION"
                                    },
                                    "extracted_mrz_data": {
                                        "passport_number": passport_match.group(1) if passport_match else "Unknown"
                                    }
                                }
                    
                    # 8. Translate back if needed
                    if lang == 'ne':
                        final_answer = translate_to_nepali(english_answer)
                    else:
                        final_answer = english_answer
                    
                    # 9. Display final answer
                    st.markdown(final_answer)
                    
                    if kyc_approved and kyc_result:
                        st.divider()
                        display_sim_approval_with_qr(kyc_result)
                    
                    st.session_state.messages.append({"role": "assistant", "content": final_answer})
                    print("\n--- ✅ Agent Finished. ---\n")

            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {e}" 
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# =============================================================================
# SIDEBAR (CLEAN & MINIMAL)
# =============================================================================

with st.sidebar:
    st.markdown("### 🛂 Smart Arrival Ecosystem")
    st.caption("Powered by LangGraph ReAct Agent")
    
    st.divider()
    
    # --- Flight Data Status ---
    st.markdown("#### ✈️ Flight Data")
    
    # Calculate age again for display
    cache_age = get_cache_age_minutes()
    
    if cache_age == float('inf'):
        st.caption("⚠️ No flight data available")
        status_color = "red"
    elif cache_age < 5:
        st.caption(f"✅ Live data (Updated < 5 min ago)")
        status_color = "green"
    elif cache_age < CACHE_MAX_AGE_MINUTES:
        st.caption(f"✅ Data current ({int(cache_age)} min ago)")
        status_color = "green"
    else:
        st.caption(f"⏰ Data stale ({int(cache_age)} min old)")
        status_color = "orange"
    
    # Manual refresh button
    if FLIGHT_ENGINE_AVAILABLE:
        if st.button("🔄 Force Refresh", use_container_width=True):
            with st.spinner("Fetching live flight data from AviationStack..."):
                try:
                    update_cache()
                    # Clear the cache to force re-check on next run
                    refresh_flight_cache_if_needed.clear()
                    st.toast("✅ Flight data refreshed!", icon="✈️")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Refresh failed: {e}")
    
    st.divider()
    
    st.markdown("#### 🔐 Identity Services")
    kyc_status = "✅ Documents Ready" if st.session_state.get("kyc_documents_ready", False) else "📄 Not Verified"
    st.caption(f"Status: {kyc_status}")
    
    if st.button("🔐 Verify Identity for SIM Card", use_container_width=True):
        kyc_verification_modal()
    
    st.divider()
    
    st.markdown("#### 📚 Capabilities")
    st.markdown("""
    - ✈️ Flight Status & Search
    - ☀️ Live Weather Updates
    - 🛂 Airport Rules & Customs
    - 📱 SIM Card KYC (ICAO 9303)
    - 🌐 Nepali/English Support
    """)
    
    st.divider()
    
    # Performance Info
    st.markdown("#### ⚡ Performance")
    st.caption(f"Model: {LLM_MODEL}")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset", use_container_width=True): 
            st.cache_resource.clear()
            for f in ["temp_passport.jpg", "temp_selfie.jpg"]:
                if os.path.exists(f):
                    os.remove(f)
            st.session_state["kyc_documents_ready"] = False
            st.rerun()
    
    st.divider()
    st.caption("🇳🇵 Tribhuvan International Airport")
    st.caption("Version 2.0 | Thesis Project 2024")