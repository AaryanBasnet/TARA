"""
Build Knowledge Base - Improved Version
Converts source_data files into structured knowledge base documents.

Key Improvements:
1. Adds topic headers to each document for better context
2. Cleans PDF content (removes empty pages, excessive whitespace)
3. Merges related content instead of splitting by page
4. Creates Q&A formatted documents for better RAG retrieval
"""

import json
import os
import re
from langchain_community.document_loaders import PyPDFLoader

# --- Configuration ---
SOURCE_DIR = "source_data"
KNOWLEDGE_BASE_DIR = "knowledge_base"


def clean_text(text: str) -> str:
    """Clean text by removing excessive whitespace and empty lines."""
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    # Remove multiple newlines (keep max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip each line
    lines = [line.strip() for line in text.split('\n')]
    # Remove empty lines at start/end
    text = '\n'.join(lines).strip()
    return text


def clean_filename(title: str) -> str:
    """Create a clean filename from a title."""
    clean_title = title.replace("Topic:", "").strip().lower()
    clean_title = clean_title.replace(' ', '_')
    clean_title = re.sub(r'[^a-z0-9_]', '', clean_title)
    return f"{clean_title}.txt"


def process_json_file(file_path: str) -> int:
    """
    Process intent.json - Creates Q&A formatted documents.

    Format:
    TOPIC: [intent_name]
    QUESTION: [example questions]
    ANSWER: [response]
    """
    print(f"Processing JSON file: {file_path}...")
    file_count = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for intent_data in data:
        intent_name = intent_data.get("intent", "")
        responses = intent_data.get("responses", [])
        examples = intent_data.get("examples", [])

        if not intent_name or intent_name == "unknown" or not responses:
            continue

        # Create human-readable topic name
        topic_name = intent_name.replace("_", " ").title()

        # Build structured content
        content_parts = [f"TOPIC: {topic_name}"]

        # Add example questions (helps with retrieval)
        if examples:
            content_parts.append(f"RELATED QUESTIONS: {'; '.join(examples[:3])}")

        # Add the answer
        answer = "\n".join(responses)
        answer = answer.replace("**", "").replace("!!", "")  # Remove markdown
        content_parts.append(f"ANSWER: {answer}")

        content = "\n\n".join(content_parts)

        # Save to file
        filename = f"{intent_name}.txt"
        output_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as out_f:
            out_f.write(content)
        file_count += 1

    print(f"  -> Created {file_count} knowledge files from JSON.")
    return file_count


def process_text_file(file_path: str) -> int:
    """
    Process structured text files with Topic: headers.
    Adds topic context to each document.
    """
    print(f"Processing Text file: {file_path}...")
    file_count = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Get source filename for context
    source_name = os.path.basename(file_path).replace('.txt', '').replace('_', ' ').title()

    documents = full_text.split("---")
    for doc in documents:
        doc = doc.strip()
        if not doc:
            continue

        lines = doc.split('\n')
        title_line = lines[0].strip()
        content_body = "\n".join(lines[1:]).strip()

        if not title_line.startswith("Topic:") or not content_body:
            # Try to process as plain text if no Topic: header
            if len(doc) > 50:  # Only if substantial content
                topic = source_name
                content_body = doc
            else:
                print(f"  -> Skipping badly formatted block: {title_line[:50]}")
                continue
        else:
            topic = title_line.replace("Topic:", "").strip()

        # Build structured content with context
        content = f"TOPIC: {topic}\nSOURCE: {source_name}\n\n{clean_text(content_body)}"

        filename = clean_filename(f"Topic: {topic}")
        output_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as out_f:
            out_f.write(content)
        file_count += 1

    print(f"  -> Created {file_count} knowledge files from Text.")
    return file_count


def process_pdf_file(file_path: str) -> int:
    """
    Process PDF files - Improved version.

    Key improvements:
    1. Skips nearly empty pages
    2. Merges content by sections instead of pages
    3. Adds source context
    """
    print(f"Processing PDF file: {file_path}...")

    try:
        base_filename = os.path.basename(file_path).replace('.pdf', '')
        # Create readable source name
        source_name = base_filename.replace('_', ' ').replace('-', ' ')
        source_name = re.sub(r'\s+', ' ', source_name).strip()

        loader = PyPDFLoader(file_path)
        pages = loader.load()

        # Collect all content first
        all_content = []
        for page in pages:
            content = clean_text(page.page_content)
            # Skip nearly empty pages (less than 100 chars of actual content)
            if len(content.replace('\n', '').replace(' ', '')) > 100:
                all_content.append(content)

        if not all_content:
            print(f"  -> No substantial content found in PDF.")
            return 0

        # Merge all content
        full_content = "\n\n".join(all_content)

        # Try to split by sections (look for numbered sections or headers)
        sections = re.split(r'\n(?=\d+\.\s+[A-Z]|\n[A-Z][A-Z\s]{10,}:?\n)', full_content)

        file_count = 0

        if len(sections) > 1 and len(sections) < 50:
            # Process as sections
            for i, section in enumerate(sections):
                section = clean_text(section)
                if len(section) < 100:
                    continue

                # Try to extract section title
                first_line = section.split('\n')[0][:100]
                section_title = re.sub(r'[^a-zA-Z0-9\s]', '', first_line).strip()[:50]
                if not section_title:
                    section_title = f"Section {i+1}"

                content = f"TOPIC: {section_title}\nSOURCE: {source_name}\n\n{section}"

                # Create filename
                clean_section = re.sub(r'[^a-z0-9]', '_', section_title.lower())
                clean_section = re.sub(r'_+', '_', clean_section).strip('_')[:40]
                txt_filename = f"{base_filename}_{clean_section}.txt"
                output_path = os.path.join(KNOWLEDGE_BASE_DIR, txt_filename)

                with open(output_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(content)
                file_count += 1
        else:
            # Process as chunks (for large documents or those without clear sections)
            # Split into ~2000 char chunks for better context
            chunk_size = 2000
            chunks = []
            current_chunk = ""

            for paragraph in full_content.split('\n\n'):
                if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    current_chunk += "\n\n" + paragraph if current_chunk else paragraph

            if current_chunk:
                chunks.append(current_chunk)

            for i, chunk in enumerate(chunks):
                chunk = clean_text(chunk)
                if len(chunk) < 100:
                    continue

                content = f"TOPIC: {source_name} (Part {i+1})\nSOURCE: {source_name}\n\n{chunk}"

                txt_filename = f"{base_filename}_part_{i+1}.txt"
                output_path = os.path.join(KNOWLEDGE_BASE_DIR, txt_filename)

                with open(output_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(content)
                file_count += 1

        print(f"  -> Created {file_count} knowledge files from PDF.")
        return file_count

    except Exception as e:
        print(f"  -> ERROR processing PDF {file_path}: {e}")
        return 0


def main():
    """Main function to build the knowledge base."""
    print("=" * 60)
    print("Building Knowledge Base (Improved Version)")
    print("=" * 60)

    # Clear existing knowledge base
    if os.path.exists(KNOWLEDGE_BASE_DIR):
        existing_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.txt')]
        if existing_files:
            print(f"Clearing {len(existing_files)} existing files...")
            for f in existing_files:
                os.remove(os.path.join(KNOWLEDGE_BASE_DIR, f))

    os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

    total_files = 0

    try:
        for filename in sorted(os.listdir(SOURCE_DIR)):
            file_path = os.path.join(SOURCE_DIR, filename)

            if filename.endswith(".json"):
                total_files += process_json_file(file_path)
            elif filename.endswith(".txt"):
                total_files += process_text_file(file_path)
            elif filename.endswith(".pdf"):
                total_files += process_pdf_file(file_path)
            else:
                print(f"Skipping unknown file type: {filename}")

    except FileNotFoundError:
        print(f"\n ERROR: Could not find the '{SOURCE_DIR}' folder.")
        return
    except Exception as e:
        print(f"\n ERROR: {e}")
        return

    print("\n" + "=" * 60)
    print(f"Total knowledge files created: {total_files}")
    print(f"Output folder: '{KNOWLEDGE_BASE_DIR}'")
    print("=" * 60)
    print("\nNext step: Run 'python ingest.py' to create the vector database.")


if __name__ == "__main__":
    main()
