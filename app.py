import os
import streamlit as st
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# --- Configuration ---
DB_DIR = "db"                          # Folder with your "brain"
MODEL_NAME = "all-MiniLM-L6-v2"        # The embedding model
LLM_MODEL = "llama3:8b"                # The Ollama model
load_dotenv()

# --- Load the "Brain" (Vector Database) ---
@st.cache_resource  # Caches the DB connection
def load_retriever():
    print("Loading vector database...")
    model_kwargs = {'device': 'cpu'}
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME, model_kwargs=model_kwargs)
    
    # Load the persisted database from disk
    db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    
    # Create the "retriever," which is the component that finds relevant documents
    retriever = db.as_retriever(search_kwargs={"k": 4}) # "k": 4 means "find 4 relevant documents"
    print("Vector database loaded.")
    return retriever

# --- Load the "Professor" (LLM) ---
@st.cache_resource  # Caches the LLM
def load_llm():
    print("Loading LLM...")
    llm = Ollama(model=LLM_MODEL)
    print("LLM loaded.")
    return llm

# --- Format Documents for the LLM ---
def format_docs(docs):
    # This helper function combines the retrieved documents into a single string
    # The LLM will use this as its "context" or "open book."
    return "\n\n".join(doc.page_content for doc in docs)

# --- Set up the RAG Prompt Template ---
# This is the "prompt" for your thesis. It instructs the AI on how to behave.
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
# This "chain" ties all the pieces together.
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
st.caption("Chatbot for Tribhuvan International Airport")

# Initialize chat history in Streamlit's session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get new user input
if user_question := st.chat_input("Ask a question about TIA..."):
    
    # Add user's message to chat history
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # Get the bot's answer using the RAG chain
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # The "stream" function allows the answer to appear word by word
                response_stream = rag_chain.stream(user_question)
                full_response = st.write_stream(response_stream)
                
                # Add the bot's complete response to chat history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                error_msg = f"Sorry, I encountered an error. Please make sure Ollama is running. Error: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})