from deep_translator import GoogleTranslator
from langdetect import LangDetectException

import os 
import nltk
import re
from typing import Tuple, Dict

# We keep NLTK dependency structure for sentence splitting compatibility
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK 'punkt' tokenizer...")
    nltk.download('punkt')
    print("Download complete.")

# NOTE: All heavy model loading has been removed for instant startup.

# =============================================================================
# ENTITY PROTECTION (Translation Sandwich Architecture)
# =============================================================================
# Regular expressions for entities that must NOT be translated/mangled
PROTECTED_PATTERNS = {
    # Flight Codes (e.g., RA205, RA 205, 9N123)
    "FLIGHT": r"\b([A-Z]{2,3}\s?\d{3,4})\b",
    
    # Passport Numbers (e.g., A1234567, 1234567, N12345678)
    "PASSPORT": r"\b([A-Z]{1,2}\d{6,9})\b",
    
    # Emails
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    
    # URLs
    "URL": r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
}

def mask_entities(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Replaces protected entities with placeholders to prevent translation.
    Format: [[__ID_0__]], [[__ID_1__]], etc.
    """
    if not text:
        return text, {}

    placeholders = {}
    masked_text = text
    counter = 0

    # Helper to generate unique placeholder
    def replace_match(match):
        nonlocal counter
        original = match.group(0)
        # Check if this string is already in our placeholder map (deduplication)
        for ph, orig in placeholders.items():
            if orig == original:
                return ph
        
        # Create new placeholder
        placeholder = f"[[__ID_{counter}__]]"
        placeholders[placeholder] = original
        counter += 1
        return placeholder

    # Apply patterns
    # Priority: URLs and Emails first (to avoid breaking them with other regex), then Flights/Passports
    for label in ["URL", "EMAIL", "FLIGHT", "PASSPORT"]:
        pattern = PROTECTED_PATTERNS[label]
        masked_text = re.sub(pattern, replace_match, masked_text)

    return masked_text, placeholders

def unmask_entities(text: str, placeholders: Dict[str, str]) -> str:
    """
    Restores original entities from placeholders in the translated text.
    Handles potential translator mangling of placeholders (e.g., added spaces).
    """
    if not text or not placeholders:
        return text

    restored_text = text

    for placeholder, original in placeholders.items():
        # Clean placeholder for regex (escape brackets)
        # Placeholder format: [[__ID_0__]]
        # Translator might change it to: [[ __ ID_0 __ ]] or [ [ __ID_0__ ] ]
        
        # We try strict replacement first
        if placeholder in restored_text:
            restored_text = restored_text.replace(placeholder, original)
        else:
            # Fuzzy recovery logic
            # Extract the ID number
            try:
                id_num = placeholder.split('_')[-3] # ID_0 -> 0
                # Regex to find mangled version: braces with that ID inside
                # Looks for [[ ... ID_0 ... ]] allowing for spaces
                fuzzy_pattern = r"\[\[\s*__ID_" + id_num + r"__\s*\]\]"
                restored_text = re.sub(fuzzy_pattern, original, restored_text, flags=re.IGNORECASE)
            except:
                pass # Failed to recover this one

    return restored_text

# =============================================================================
# TRANSLATION FUNCTIONS
# =============================================================================

def detect_language(text: str) -> str:
    """
    Detects language using a fast Unicode check for Devanagari (Nepali).
    This runs instantly on the CPU, skipping the slow LangDetect model.
    """
    if not text or text.strip() == "":
        return 'en'
        
    # Check for Devanagari characters (Unicode range \u0900 to \u097F)
    if any("\u0900" <= char <= "\u097F" for char in text):
        return 'ne'
        
    # If no Devanagari, assume English (or the language of the prompt)
    return 'en'

def translate_to_english(text: str) -> str:
    """Translates Nepali to English using the 'Translation Sandwich' architecture."""
    if not text or text.strip() == "": return ""
    
    # 1. Mask Entities
    masked_text, placeholders = mask_entities(text)
    
    print(f"Translating to English (Cloud): {text[:50]}...")
    if placeholders:
        print(f"   (Protected {len(placeholders)} entities)")

    try:
        # Use 'auto' source detection for flexibility
        english_text = GoogleTranslator(source='auto', target='en').translate(masked_text)
        
        # 2. Unmask Entities
        final_text = unmask_entities(english_text, placeholders)
        
        print(f"Translation result: {final_text}")
        return final_text
    except Exception as e:
        print(f"Cloud Translation Error (Ne->En): {e}")
        return text # Fallback to original text

def translate_to_nepali(text: str) -> str:
    """Translates English to Nepali using the 'Translation Sandwich' architecture."""
    if not text or text.strip() == "": return ""
    
    # 1. Mask Entities (CRITICAL: Prevents RA205 -> "Room 205" errors)
    masked_text, placeholders = mask_entities(text)
    
    print(f"Translating to Nepali (Cloud): {text[:50]}...")
    if placeholders:
        print(f"   (Protected {len(placeholders)} entities)")

    # We use nltk.sent_tokenize to prevent the API from losing formatting or
    # confusing sentences when dealing with multi-paragraph text.
    try:
        sentences = nltk.sent_tokenize(masked_text)
    except:
        sentences = re.split(r'[.!?]\s*', masked_text) # Simpler fallback
    
    translated_sentences = []
    
    for sentence in sentences:
        if not sentence.strip():
            continue
        try:
            # Send each sentence chunk separately for higher accuracy
            translated_sentence = GoogleTranslator(source='en', target='ne').translate(sentence)
            translated_sentences.append(translated_sentence)
        except Exception as e:
            print(f"Cloud Sentence Translation Error: {e}")
            translated_sentences.append(sentence)

    # Join the translated sentences back into a single paragraph
    nepali_text = " ".join(translated_sentences)
    
    # 2. Unmask Entities
    final_text = unmask_entities(nepali_text, placeholders)
    
    print(f"Translation result: {final_text}")
    return final_text