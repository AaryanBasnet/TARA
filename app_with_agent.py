import os
import json
import requests
import streamlit as st
import re
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from datetime import datetime, timezone 

# --- Configuration ---
DB_DIR = "db"
MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL = "llama3:8b"
load_dotenv()

# --- TOOL 1: Flight Status (AeroDataBox) ---
# --- REPLACED: This now uses AeroDataBox (RapidAPI) ---
def get_flight_status(flight_iata: str) -> str:
    """
    Fetches live flight status from AeroDataBox (RapidAPI) for a given IATA flight number.
    Returns a formatted string with flight details or an error.
    """
    API_KEY = os.environ.get("RAPIDAPI_KEY")
    if not API_KEY:
        return "⚠️ Flight status service is not configured. Please contact support."

    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    BASE_URL = f"https://aerodatabox.p.rapidapi.com/flights/number/{flight_iata}/{today_date}"
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
    }

    try:
        response = requests.get(BASE_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data or len(data) == 0:
            return f"❌ No flight information found for {flight_iata} on {today_date}."

        flight_info = data[0]
        departure = flight_info.get("departure", {})
        arrival = flight_info.get("arrival", {})
        
        # Format a nice response
        status = flight_info.get("status", "N/A").upper()
        airline = flight_info.get("airline", {}).get("name", "N/A")
        delay = departure.get("delayMinutes", 0)

        # Helper to format times (since free plan has 'N/A' schedules)
        def format_time(time_str):
            if not time_str or time_str == "N/A":
                return "N/A"
            try:
                # Parse full ISO 8601 time
                dt = datetime.fromisoformat(time_str)
                return dt.strftime("%I:%M %p %Z") # Format to 10:30 PM UTC
            except ValueError:
                return time_str # Return as-is if parsing fails

        result = f"""
✈️ **Flight {flight_info.get("number", flight_iata)}** - {airline}
**Status:** {status}
{f'⏰ **Delayed by {delay} minutes**' if delay else '✅ On time'}

**Departure:**
- Airport: {departure.get("airport", {}).get("name", "N/A")}
- Gate: {departure.get("gate", "N/A")}
- Scheduled: {format_time(departure.get('scheduledTimeUtc'))}
- Estimated/Actual: {format_time(departure.get('actualTimeUtc') or departure.get('estimatedTimeUtc'))}

**Arrival:**
- Airport: {arrival.get("airport", {}).get("name", "N/A")}
- Gate: {arrival.get("gate", "N/A")}
- Scheduled: {format_time(arrival.get('scheduledTimeUtc'))}
- Estimated/Actual: {format_time(arrival.get('actualTimeUtc') or arrival.get('estimatedTimeUtc'))}
"""
        return result.strip()
        
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
             return f"❌ No flight information found for {flight_iata} on {today_date}."
        return f"❌ Error fetching flight data: {http_err}"
    except requests.exceptions.RequestException as e:
        return f"❌ Could not connect to flight status service: {e}"


def get_airport_weather(iata_code: str) -> str:
    """
    Fetches the latest weather report from AeroDataBox (RapidAPI) for a given airport.
    Returns a formatted string with weather details or an error.
    """
    API_KEY = os.environ.get("RAPIDAPI_KEY")
    if not API_KEY:
        return "⚠️ Weather service is not configured. Please contact support."

    # --- THIS IS THE FIX, BASED ON THE DOCS YOU FOUND ---
    # The endpoint is /airports/{codeType}/{code}/weather
    BASE_URL = f"https://aerodatabox.p.rapidapi.com/airports/iata/{iata_code}/weather"
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
    }

    try:
        response = requests.get(BASE_URL, headers=headers)
        response.raise_for_status()
        data = response.json()

        # --- CHANGED: Parsing the new JSON structure from the docs ---
        
        # Check if the list is empty
        if not data or len(data) == 0:
            return f"❌ No weather report found for {iata_code}."

        # Get the first (most recent) report from the list
        report = data[0]
        
        temp = report.get("airTemperature", {}).get("c", "N/A")
        
        # 'phenomenaGroups' is a list of strings
        condition = ", ".join(report.get("phenomenaGroups", ["N/A"]))
        
        humidity = "N/A" # This field is not in the new response, so we'll skip it
        wind_kph = report.get("wind", {}).get("speed", {}).get("kmPerHour", "N/A")
        wind_dir = report.get("wind", {}).get("direction", {}).get("deg", "N/A")
        visibility_km = report.get("visibility", {}).get("km", "N/A")

        result = f"""
☀️ **Weather at {iata_code} (Tribhuvan Int'l)**
**Condition:** {condition}
**Temperature:** {temp}°C
**Visibility:** {visibility_km} km
**Wind:** {wind_kph} kph from {wind_dir}°
"""
        return result.strip()

    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
            return f"❌ No airport found with code {iata_code}."
        return f"❌ Error fetching weather data: {http_err}"
    except requests.exceptions.RequestException as e:
        return f"❌ Could not connect to weather service: {e}"
    
# --- Load the "Brain" (Vector Database) ---
@st.cache_resource
def load_retriever():
    print("Loading vector database...")
    model_kwargs = {'device': 'cpu'}
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME, model_kwargs=model_kwargs)
    db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 4})
    print("Vector database loaded.")
    return retriever

# --- Load the "Professor" (LLM) ---
@st.cache_resource
def load_llm():
    print("Loading LLM...")
    llm = Ollama(model=LLM_MODEL)
    print("LLM loaded.")
    return llm

# --- Format Documents for the LLM ---
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# --- "Router" Functions to detect user intent ---

# --- IMPROVED: Regex now catches "H9 363" and "H9363" ---
def is_flight_query(query: str) -> tuple[bool, str]:
    """
    Detects if the query is about flight status and extracts the flight number.
    Returns (is_flight_query, flight_number)
    """
    query_lower = query.lower()
    flight_keywords = ['flight', 'status', 'delayed', 'departure', 'arrival', 'gate', 'scheduled']
    
    if any(keyword in query_lower for keyword in flight_keywords):
        import re
        
        # Regex to find patterns like "H9 363" or "H9363"
        pattern = r'\b([A-Z0-9]{1,3})\s?(\d{3,4})\b'
        
        matches = re.search(pattern, query.upper())
        if matches:
            flight_number = f"{matches.group(1)}{matches.group(2)}" # Join them
            return True, flight_number
    
    return False, ""

# --- ADDED: Simple weather query detector ---
def is_weather_query(query: str) -> bool:
    """
    Detects if the query is about weather.
    """
    query_lower = query.lower()
    weather_keywords = ['weather', 'forecast', 'temperature', 'how hot', 'is it raining', 'how cold']
    
    # Check for keywords AND for the airport (TIA or KTM)
    if any(keyword in query_lower for keyword in weather_keywords):
        if "tia" in query_lower or "kathmandu" in query_lower or "airport" in query_lower:
             return True
             
    return False

# --- Set up the RAG Prompt Template ---
prompt_template = """
Namaste! You are a helpful and polite Virtual Help Desk assistant for
Tribhuvan International Airport (TIA), Kathmandu.

Use the following "Context" (official airport rules) to answer the user's question.
If you don't know the answer from the context, just say:
"I'm sorry, I don't have that information in my knowledge base. Please contact the airport directly."
Do not make up answers.

Context:
{context}

Question:
{question}

Helpful Answer:
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
    st.error(f"Error initializing the chatbot. Please ensure Ollama is running and the 'db' folder exists. Error: {e}")
    st.stop()

# --- Streamlit Chat UI ---
st.title("🇳🇵 TIA Virtual Help Desk")
st.caption("Ask about airport rules, facilities, or check live flight status/weather!")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get new user input
if user_question := st.chat_input("Ask about TIA, flight status, or weather..."):
    
    # Add user's message to chat history
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # Get the bot's answer
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # --- THIS IS THE NEW "ROUTER" LOGIC ---
                is_flight, flight_number = is_flight_query(user_question)
                is_weather = is_weather_query(user_question)
                
                if is_flight and flight_number:
                    # 1. Handle flight status query
                    st.info(f"🔍 Checking status for flight {flight_number}...")
                    response = get_flight_status(flight_number)
                    st.markdown(response)
                    full_response = response
                
                elif is_weather:
                    # 2. Handle weather query
                    st.info(f"🔍 Checking weather for TIA (KTM)...")
                    response = get_airport_weather("KTM") # Hardcoded to KTM
                    st.markdown(response)
                    full_response = response
                    
                else:
                    # 3. Handle regular RAG query
                    response_stream = rag_chain.stream(user_question)
                    full_response = st.write_stream(response_stream)
                
                # Add the bot's response to chat history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error. Please make sure Ollama is running. Error: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# --- Sidebar with info ---
with st.sidebar:
    st.header("About")
    st.write("""
    This chatbot can help you with:
    - 🛂 Airport rules and regulations
    - 🛄 Baggage and customs information
    - 🏢 Airport facilities
    - ✈️ **Live flight status** (e.g., 'status of H9 363?')
    - ☀️ **Live airport weather** (e.g., 'what's the weather at TIA?')
    
    **Example questions:**
    - "What items are prohibited?"
    - "What's the status of flight U4666?"
    - "What's the weather at the airport?"
    - "Is flight RA234 delayed?"
    """)
    
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()