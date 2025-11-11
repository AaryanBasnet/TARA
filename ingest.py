import os
from langchain_community.document_loaders import DirectoryLoader # <-- FIX
from langchain_text_splitters import RecursiveCharacterTextSplitter # <-- FIX
from langchain_huggingface import HuggingFaceEmbeddings # <-- FIX (This is the new package)
from langchain_community.vectorstores import Chroma # <-- FIX

# --- Configuration ---
KNOWLEDGE_BASE_DIR = "knowledge_base"  # The folder with your .txt files
DB_DIR = "db"                          # The folder where the vector database will be stored

def main():
    print("Starting ingestion process...")
    
    # 1. Load all documents from the knowledge_base folder
    print(f"Loading documents from '{KNOWLEDGE_BASE_DIR}'...")
    loader = DirectoryLoader(KNOWLEDGE_BASE_DIR, glob="*.txt")
    documents = loader.load()
    
    if not documents:
        print(f"No .txt files found in '{KNOWLEDGE_BASE_DIR}'. Please run build_knowledge.py first.")
        return

    print(f"Loaded {len(documents)} documents.")

    # 2. Split the documents into smaller chunks
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)
    print(f"Split into {len(texts)} chunks.")

    # 3. Set up the embedding model
    print("Loading embedding model... (This may take a few minutes on first run)")
    model_name = "all-MiniLM-L6-v2"
    model_kwargs = {'device': 'cpu'} # Use CPU
    embeddings = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs)
    print("Embedding model loaded.")

    # 4. Create and persist the vector database
    print(f"Creating and persisting vector database in '{DB_DIR}'...")
    db = Chroma.from_documents(
        texts, 
        embeddings, 
        persist_directory=DB_DIR
    )
    
    print("\n✅ Ingestion Complete!")
    print(f"Vector database is saved in the '{DB_DIR}' folder.")

if __name__ == "__main__":
    main()