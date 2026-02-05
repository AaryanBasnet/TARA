"""
Ingest Knowledge Base into Vector Database - Improved Version

Key Improvements:
1. Extracts metadata (topic, source) from document headers
2. Smart chunking - keeps small docs whole, splits large ones
3. Adds metadata to vector store for better retrieval
4. Removes old database before creating new one
"""

import os
import re
import shutil
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# --- Configuration ---
KNOWLEDGE_BASE_DIR = "knowledge_base"
DB_DIR = "db_new"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Chunking settings
MAX_CHUNK_SIZE = 800      # Maximum chunk size in characters
CHUNK_OVERLAP = 100       # Overlap between chunks
MIN_CHUNK_SIZE = 100      # Minimum chunk size (don't split smaller)


def extract_metadata(content: str, filename: str) -> dict:
    """
    Extract metadata from document content.
    Looks for TOPIC: and SOURCE: headers.
    """
    metadata = {
        "filename": filename,
        "topic": "",
        "source": ""
    }

    # Extract TOPIC
    topic_match = re.search(r'^TOPIC:\s*(.+?)$', content, re.MULTILINE)
    if topic_match:
        metadata["topic"] = topic_match.group(1).strip()

    # Extract SOURCE
    source_match = re.search(r'^SOURCE:\s*(.+?)$', content, re.MULTILINE)
    if source_match:
        metadata["source"] = source_match.group(1).strip()

    # Fallback: use filename as topic
    if not metadata["topic"]:
        metadata["topic"] = filename.replace('.txt', '').replace('_', ' ').title()

    return metadata


def load_and_process_documents() -> list:
    """
    Load documents and add metadata.
    Returns list of Document objects with metadata.
    """
    print(f"Loading documents from '{KNOWLEDGE_BASE_DIR}'...")

    documents = []

    for filename in os.listdir(KNOWLEDGE_BASE_DIR):
        if not filename.endswith('.txt'):
            continue

        filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                print(f"  Skipping empty file: {filename}")
                continue

            # Extract metadata
            metadata = extract_metadata(content, filename)

            # Create Document with metadata
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(doc)

        except Exception as e:
            print(f"  Error loading {filename}: {e}")

    print(f"Loaded {len(documents)} documents.")
    return documents


def smart_split_documents(documents: list) -> list:
    """
    Smart chunking strategy:
    - Small documents (< MAX_CHUNK_SIZE): Keep whole
    - Large documents: Split with overlap, preserve metadata
    """
    print("Splitting documents...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    all_chunks = []
    kept_whole = 0
    split_count = 0

    for doc in documents:
        content_length = len(doc.page_content)

        if content_length <= MAX_CHUNK_SIZE:
            # Keep small documents whole
            all_chunks.append(doc)
            kept_whole += 1
        else:
            # Split large documents
            chunks = text_splitter.split_documents([doc])

            # Add chunk index to metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = i + 1
                chunk.metadata["total_chunks"] = len(chunks)

                # Add topic prefix to chunk content for better retrieval
                topic = chunk.metadata.get("topic", "")
                if topic and not chunk.page_content.startswith("TOPIC:"):
                    chunk.page_content = f"TOPIC: {topic}\n\n{chunk.page_content}"

            all_chunks.extend(chunks)
            split_count += len(chunks)

    print(f"  Kept {kept_whole} documents whole")
    print(f"  Split into {split_count} chunks")
    print(f"  Total chunks: {len(all_chunks)}")

    return all_chunks


def create_vector_database(chunks: list) -> None:
    """
    Create the Chroma vector database with embeddings.
    """
    # Remove old database
    if os.path.exists(DB_DIR):
        print(f"Removing old database in '{DB_DIR}'...")
        try:
            shutil.rmtree(DB_DIR)
        except PermissionError:
            print("  WARNING: Could not delete old database (file in use).")
            print("  Please close any running Streamlit apps and try again.")
            print("  Or manually delete the 'db' folder.")
            return

    # Load embedding model
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'}
    )
    print("Embedding model loaded.")

    # Create vector database
    print(f"Creating vector database in '{DB_DIR}'...")
    print(f"  Embedding {len(chunks)} chunks...")

    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_DIR
    )

    print(f"Vector database created with {db._collection.count()} vectors.")


def test_retrieval(query: str = "smoking area") -> None:
    """
    Quick test to verify the database works.
    """
    print(f"\n--- Testing retrieval with query: '{query}' ---")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'}
    )

    db = Chroma(
        persist_directory=DB_DIR,
        embedding_function=embeddings
    )

    results = db.similarity_search(query, k=2)

    for i, doc in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Topic: {doc.metadata.get('topic', 'N/A')}")
        print(f"  Source: {doc.metadata.get('source', 'N/A')}")
        print(f"  Content preview: {doc.page_content[:200]}...")


def main():
    """Main ingestion pipeline."""
    print("=" * 60)
    print("Knowledge Base Ingestion (Improved Version)")
    print("=" * 60)

    # Step 1: Load documents with metadata
    documents = load_and_process_documents()

    if not documents:
        print(f"\nNo documents found in '{KNOWLEDGE_BASE_DIR}'.")
        print("Please run 'python build_knowledge.py' first.")
        return

    # Step 2: Smart chunking
    chunks = smart_split_documents(documents)

    # Step 3: Create vector database
    create_vector_database(chunks)

    # Step 4: Test
    test_retrieval()

    print("\n" + "=" * 60)
    print("Ingestion Complete!")
    print(f"Vector database saved in '{DB_DIR}'")
    print("=" * 60)


if __name__ == "__main__":
    main()
