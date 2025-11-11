import json
import os
import re
from langchain_community.document_loaders import PyPDFLoader # <-- NEW

# --- Configuration ---
SOURCE_DIR = "source_data"       # Folder where you put your source files
KNOWLEDGE_BASE_DIR = "knowledge_base"  # Folder where the .txt files will be created
# ---------------------

def clean_filename(title):
    clean_title = title.replace("Topic:", "").strip().lower()
    clean_title = clean_title.replace(' ', '_')
    clean_title = re.sub(r'[^a-z0-9_]', '', clean_title)
    return f"{clean_title}.txt"

def process_json_file(file_path):
    print(f"Processing JSON file: {file_path}...")
    file_count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for intent_data in data:
        intent_name = intent_data.get("intent")
        responses = intent_data.get("responses")
        if not intent_name or intent_name == "unknown" or not responses:
            continue
        content = "\n".join(responses)
        content = content.replace("**", "").replace("!!", "")
        filename = f"{intent_name}.txt"
        output_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as out_f:
            out_f.write(content)
        file_count += 1
    print(f"  -> Created {file_count} knowledge files from JSON.")
    return file_count

def process_text_file(file_path):
    print(f"Processing Text file: {file_path}...")
    file_count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        full_text = f.read()
    documents = full_text.split("---")
    for doc in documents:
        doc = doc.strip()
        if not doc:
            continue
        lines = doc.split('\n')
        title_line = lines[0].strip()
        content_body = "\n".join(lines[1:]).strip()
        if not title_line.startswith("Topic:") or not content_body:
            print(f"  -> Skipping badly formatted block: {title_line}")
            continue
        filename = clean_filename(title_line)
        output_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as out_f:
            out_f.write(content_body)
        file_count += 1
    print(f"  -> Created {file_count} knowledge files from Text.")
    return file_count

# --- THIS ENTIRE FUNCTION IS NEW ---
def process_pdf_file(file_path):
    """
    This is the NEW function for your PDFs.
    It reads a PDF and saves each page as a separate .txt file.
    """
    print(f"Processing PDF file: {file_path}...")
    try:
        # Get the original PDF filename to use in our new .txt files
        base_filename = os.path.basename(file_path).replace('.pdf', '')
        
        # Load the PDF
        loader = PyPDFLoader(file_path)
        pages = loader.load() # This returns a list of "Document" objects
        
        # Loop through each page and save it as its own .txt file
        for i, page in enumerate(pages):
            page_content = page.page_content
            page_number = i + 1
            
            # Create a clean filename like: "baggage_rules_pdf_page_1.txt"
            txt_filename = f"{base_filename}_pdf_page_{page_number}.txt"
            output_path = os.path.join(KNOWLEDGE_BASE_DIR, txt_filename)
            
            # Save the page's text to the new file
            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.write(page_content)
                
        print(f"  -> Created {len(pages)} knowledge files from PDF.")
        return len(pages)
        
    except Exception as e:
        print(f"  -> ERROR processing PDF {file_path}: {e}")
        return 0
# --- END OF NEW FUNCTION ---

# --- Main Automation Script ---
def main():
    print("Building Knowledge Base...")
    os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
    total_files = 0
    
    try:
        for filename in os.listdir(SOURCE_DIR):
            file_path = os.path.join(SOURCE_DIR, filename)
            
            if filename.endswith(".json"):
                total_files += process_json_file(file_path)
            
            elif filename.endswith(".txt"):
                total_files += process_text_file(file_path)
            
            elif filename.endswith(".pdf"): # <-- NEW
                total_files += process_pdf_file(file_path) # <-- NEW
                
            else:
                print(f"Skipping unknown file type: {filename}")
    
    except FileNotFoundError:
        print(f"\n❌ ERROR: Could not find the '{SOURCE_DIR}' folder.")
        print(f"    Please make sure '{SOURCE_DIR}' is in the same directory as this script.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
            
    print(f"\n✅ Total knowledge files created: {total_files}")
    print(f"All files are in the '{KNOWLEDGE_BASE_DIR}' folder.")

if __name__ == "__main__":
    main()