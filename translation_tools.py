from deep_translator import GoogleTranslator
from langdetect import LangDetectException
import streamlit as st
import os 
import nltk
import re

# We keep NLTK dependency structure for sentence splitting compatibility
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK 'punkt' tokenizer...")
    nltk.download('punkt')
    print("Download complete.")

# NOTE: All heavy model loading has been removed for instant startup.

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
    """Translates Nepali to English using the fast Google Translate API."""
    if not text or text.strip() == "": return ""
    print(f"Translating to English (Cloud): {text[:50]}...")
    try:
        # Use 'auto' source detection for flexibility
        english_text = GoogleTranslator(source='auto', target='en').translate(text)
        print(f"Translation result: {english_text}")
        return english_text
    except Exception as e:
        print(f"Cloud Translation Error (Ne->En): {e}")
        return text # Fallback to original text

def translate_to_nepali(text: str) -> str:
    """Translates English to Nepali using the fast Google Translate API."""
    if not text or text.strip() == "": return ""
    print(f"Translating to Nepali (Cloud): {text[:50]}...")

    # We use nltk.sent_tokenize to prevent the API from losing formatting or
    # confusing sentences when dealing with multi-paragraph text.
    try:
        sentences = nltk.sent_tokenize(text)
    except:
        sentences = re.split(r'[.!?]\s*', text) # Simpler fallback
    
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
    
    print(f"Translation result: {nepali_text}")
    return nepali_text