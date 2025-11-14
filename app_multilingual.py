import os
import streamlit as st
from dotenv import load_dotenv
from typing import Generator
import re 

# --- 1. LOAD ENV VARS FIRST ---
load_dotenv() 

# --- 2. IMPORT API/TRANSLATION TOOLS ---
try:
    # We still import the functions, as we need to give them to the agent
    from flight_tools import get_flight_status_from_json, get_kathmandu_weather_openmeteo
except ImportError:
    st.error("❌ flight_tools.py not found. Please place it in same folder.")
    st.stop()

try:
    from translation_tools import detect_language, translate_to_english, translate_to_nepali
except ImportError:
    st.error("❌ translation_tools.py not found. Please place it in same folder.")
    st.stop()


# --- 3. LANGCHAIN IMPORTS ---
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool # <-- We need this to define the RAG tool

# --- 4. LANGGRAPH AGENT IMPORTS ---
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

# --- Configuration ---
DB_DIR = "db"
MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL = "qwen2:7b"

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


# --- Load the "Professor" (LLM) ---
@st.cache_resource(show_spinner=False)
def load_llm():
    print("Loading LLM...")
    llm = ChatOllama(model=LLM_MODEL, stream=False, temperature=0)
    print("LLM loaded.")
    return llm


# --- Format Documents for the LLM ---
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# --- Set up the RAG Prompt Template ---
prompt_template = """
You are a document summarizer. Use the following "Context" to provide a
direct, factual answer to the "Question".
If the context does not contain the answer, just say:
"I'm sorry, I don't have that information in my knowledge base."

Context:
{context}

Question:
{question}

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
#
#   THIS IS THE CRITICAL FIX
#   We make the docstring extremely specific to stop the agent
#   from using it for flight or weather.
#
@tool
def get_general_airport_info(query: str) -> str:
    """
    Use this tool for all general questions about TIA airport rules, regulations, 
    facilities, baggage allowances, customs, and prohibited items.
    
    *** CRITICAL: DO NOT USE THIS TOOL ***
    - If the user asks for a specific flight status (e.g., "RA205").
    - If the user asks for the weather.
    
    Use the other tools for flight status and weather.
    """
    print(f"🧰 TOOL USED: get_general_airport_info for query '{query}'")
    try:
        result = rag_chain.invoke(query)
        if not result or result.strip() == "":
            return (
                "I'm sorry, I couldn’t find relevant information in my database. "
                "Please contact the airport directly."
            )
        return result.strip()
    except Exception as e:
        return f"Error retrieving general information: {e}"


# --- SYSTEM MESSAGE ---
SYSTEM_MESSAGE = """
✅ --- STRICT SYSTEM MESSAGE --- ✅

Namaste! You are a helpful and polite Virtual Help Desk assistant for
Tribhuvan International Airport (TIA), Kathmandu.

You have three tools. Follow these rules:

1.  If the user asks about **a specific flight number** (e.g., "RA205"), 
    you MUST use `get_flight_status_from_json`.
2.  If the user asks about **weather**, 
    you MUST use `get_kathmandu_weather_openmeteo`.
3.  For **all other questions** (e.g., rules, facilities, customs, baggage, wifi),
    you MUST use `get_general_airport_info`.

⚠️ --- CRITICAL RULES --- ⚠️
-   You MUST ALWAYS use one of the available tools to answer any question.
-   Your own pre-trained knowledge is FORBIDDEN.
-   **FORBIDDEN TOPICS:** Do NOT answer common questions about 'visa', 'taxi',
    'customs', or 'baggage' from your own knowledge. You MUST use the
    `get_general_airport_info` tool for these, as TIA has specific rules.
-   **RAG Tool Rule:** When you use `get_general_airport_info`, the tool's
    output IS the final, correct answer. You MUST return this answer
    VERBATIM (exactly as it is written) without re-phrasing it.
"""
# --- AGENT SETUP ---
# We give the agent our THREE tools
tools = [get_flight_status_from_json, get_kathmandu_weather_openmeteo, get_general_airport_info]
memory = MemorySaver()

try:
    agent_executor = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_MESSAGE,
        checkpointer=memory,
    )
    print("ReAct Agent created successfully with memory.")
except Exception as e:
    st.error(f"Failed to create agent: {e}")
    st.stop()


# --- Streamlit Chat UI ---
st.title("🇳🇵 TIA Virtual Help Desk (Agent + Multilingual)")
st.caption("नेपालीमा वा अंग्रेजीमा सोध्नुहोस्")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = "tia_chat_session_v1"

# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input ---
if user_question := st.chat_input("Ask about TIA... | TIA बारे सोध्नुहोस्..."):

    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # --- "TRANSLATION SANDWICH" AROUND THE AGENT ---
    with st.chat_message("assistant"):
        with st.spinner("Thinking... | सोच्दै..."):
            try:
                # 1. Detect Language
                lang = detect_language(user_question)
                
                # 2. Translate to English (if needed)
                if lang == 'ne':
                    english_query = translate_to_english(user_question)
                    st.info(f"*(Translating: {english_query})*") # Show user the translation
                else:
                    english_query = user_question

                #
                # 3. Run the AGENT (in English)
                #    We do NOT have any if/elif routing here.
                #    We let the agent decide.
                #
                config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
                inputs = {"messages": [{"role": "user", "content": english_query}]}

                print("\n--- 🤖 Agent is Invoked... ---\n")
                response = agent_executor.invoke(inputs, config=config)

                # Safe extraction
                last_message = response.get("messages", [])[-1]
                english_answer = getattr(last_message, "content", str(last_message)).strip()

                # Fallback safeguard
                if not english_answer:
                    english_answer = (
                        "I'm sorry, I don't have that information in my knowledge base. "
                        "Please contact the airport directly."
                    )
                
                # 4. Translate back to Nepali (if needed)
                if lang == 'ne':
                    final_answer = translate_to_nepali(english_answer)
                else:
                    final_answer = english_answer
                
                # 5. Display the final answer
                st.markdown(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})
                
                print("\n--- ✅ Agent Finished. ---\n")

            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {e}" 
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )

# --- Sidebar ---
with st.sidebar:
    st.header("About")
    st.write("This bot can now understand both English and Nepali.") 
    st.write(
        """
        This chatbot uses a **LangGraph ReAct Agent** to answer your questions.

        It can:
        - 🛂 Answer general questions about TIA rules.
        - ✈️ Check **live flight status** (from a reliable mock DB)
        - ☀️ Check **live airport weather** (real-time API)
        - 🧠 Handle **mixed queries** and **retain conversation memory**

        **Try asking:**
        - "RA205 को स्थिति के छ र काठमाडौंको मौसम कस्तो छ?"
        - "के के सामान ल्याउन पाइदैन?"
        - (Follow-up) "What is that flight's gate?"
        """
    )

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    if st.button("🔄 Reload Translation Models"): 
        st.cache_resource.clear()
        st.rerun()