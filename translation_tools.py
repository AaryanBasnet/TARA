from transformers import AutoTokenizer, T5ForConditionalGeneration, MarianMTModel, MarianTokenizer
from langdetect import detect, LangDetectException
import streamlit as st
import os 
import nltk # <-- We need NLTK for sentence splitting

# --- Download the NLTK sentence tokenizer ---
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK 'punkt' tokenizer...")
    nltk.download('punkt')
    print("Download complete.")
# ---

# --- MODEL 1: NEPALI TO ENGLISH (Public Model) ---
@st.cache_resource(show_spinner=False)
def load_nepali_to_english_model():
    print("Loading Nepali to English translation model...")
    model_name = "iamTangsang/MarianMT-Nepali-to-English"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    print("Nepali to English model loaded.")
    return tokenizer, model

# --- MODEL 2: ENGLISH TO NEPALI (Public Model) ---
@st.cache_resource(show_spinner=False)
def load_english_to_nepali_model():
    print("Loading English to Nepali translation model...")
    # This is a public T5 model that works well
    model_name = "d2niraj555/mt5-eng2nep"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)
    print("English to Nepali model loaded.")
    return tokenizer, model

# Load the models once on startup
ne_en_tokenizer, ne_en_model = load_nepali_to_english_model()
en_ne_tokenizer, en_ne_model = load_english_to_nepali_model()

def detect_language(text: str) -> str:
    """Detects if the text is 'ne' (Nepali) or 'en' (English)"""
    try:
        lang = detect(text)
        if lang == 'ne':
            return 'ne'
        else:
            return 'en'
    except LangDetectException:
        return 'en'

def translate_to_english(text: str) -> str:
    """Translates a Nepali string to English"""
    print(f"Translating to English: {text}")
    inputs = ne_en_tokenizer(text, return_tensors="pt", padding=True)
    translated_tokens = ne_en_model.generate(**inputs)
    english_text = ne_en_tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
    print(f"Translation result: {english_text}")
    return english_text

def translate_to_nepali(text: str) -> str:
    """Translates an English string to Nepali, sentence by sentence."""
    print(f"Chunk-translating to Nepali: {text[:50]}...")

    # 1. Split the paragraph into a list of sentences
    sentences = nltk.sent_tokenize(text)
    
    translated_sentences = []
    
    # 2. Loop over each sentence and translate it
    for sentence in sentences:
        if not sentence.strip():
            continue
            
        input_text = sentence
        
        inputs = en_ne_tokenizer(
            input_text, 
            return_tensors="pt", 
            padding=True, 
            truncation=True, 
            max_length=512    
        )
        
        translated_tokens = en_ne_model.generate(
            **inputs, 
            num_beams=4,
            early_stopping=True,
            max_length=512    
        )
        
        translated_sentence = en_ne_tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
        translated_sentences.append(translated_sentence)

    # 3. Join the translated sentences back into a single paragraph
    nepali_text = " ".join(translated_sentences)
    
    print(f"Translation result: {nepali_text}")
    return nepali_text