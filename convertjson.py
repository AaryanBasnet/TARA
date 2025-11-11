import json
import os

# The name of the new folder we want to create
KNOWLEDGE_BASE_DIR = "knowledge_base"

# The name of your intents file
INTENT_FILE = "intent.json"

# Create the knowledge_base directory if it doesn't exist
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

print(f"Loading data from {INTENT_FILE}...")

# Load the JSON data
with open(INTENT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

file_count = 0

# Loop through each intent in the JSON file
for intent_data in data:
    intent_name = intent_data.get("intent")
    responses = intent_data.get("responses")

    # Skip the 'unknown' intent or any with no answers
    if not intent_name or intent_name == "unknown" or not responses:
        continue

    # Clean up markdown and special characters
    # We join all responses, in case an intent has more than one
    content = "\n".join(responses)
    content = content.replace("**", "")  # Remove bold markdown
    content = content.replace("!!", "")  # Remove special '!!' chars
    
    # Create the new filename, e.g., "knowledge_base/facilities_wifi.txt"
    file_path = os.path.join(KNOWLEDGE_BASE_DIR, f"{intent_name}.txt")

    # Write the clean answer to the new .txt file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    file_count += 1

print(f"Done! Successfully created {file_count} .txt files in the '{KNOWLEDGE_BASE_DIR}' folder.")