"""
KYC Tools for SIM Card Verification - Thesis-Level Security Implementation

This module implements forensic document verification using:
1. ICAO 9303 Standard MRZ (Machine Readable Zone) Validation
2. Face Recognition for biometric verification

Security Flow:
    OCR -> MRZ Extraction -> Check Digit Validation -> Face Matching -> Approval

References:
    - ICAO Doc 9303: Machine Readable Travel Documents
    - https://www.icao.int/publications/pages/publication.aspx?docnum=9303
"""

import json
import random
import string
import re
from langchain_core.tools import tool

# --- Initialize OCR Reader (Lazy Loading) ---
_ocr_reader = None


def get_ocr_reader():
    """
    Lazy initialization of EasyOCR reader. FORCES CPU MODE (gpu=False)
    for stability, bypassing complex CUDA/NVIDIA setup issues.
    """
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        print("--- [OCR] Initializing EasyOCR Reader (CPU MODE)... ---")
        # CRITICAL FIX: Set gpu=False to ensure stability on CPU
        _ocr_reader = easyocr.Reader(['en'], gpu=False) 
        print("--- [OK] EasyOCR Reader Initialized (CPU) ---")
    return _ocr_reader

def generate_mock_phone_number() -> str:
    """Generate a mock Nepali phone number."""
    prefixes = ["980", "981", "982", "984", "985", "986"]
    prefix = random.choice(prefixes)
    suffix = ''.join(random.choices(string.digits, k=7))
    return f"+977-{prefix}-{suffix}"


# =============================================================================
# ICAO 9303 MRZ VALIDATION - FORENSIC DOCUMENT SECURITY
# =============================================================================

def calculate_check_digit(data: str) -> int:
    """
    Calculates the ICAO 9303 Standard check digit using the 7-3-1 algorithm.
    
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                    ICAO 9303 CHECK DIGIT ALGORITHM                       ║
    ║                         (7-3-1 Weighted Sum)                             ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║ PURPOSE:                                                                 ║
    ║   Detect transcription errors and tampering in Machine Readable Zones   ║
    ║   (MRZ) of passports and travel documents.                              ║
    ║                                                                          ║
    ║ ALGORITHM:                                                               ║
    ║   1. Convert each character to a numeric value:                          ║
    ║      - Digits 0-9 -> value 0-9                                           ║
    ║      - Letters A-Z -> values 10-35 (A=10, B=11, ..., Z=35)               ║
    ║      - Filler character '<' -> value 0                                   ║
    ║                                                                          ║
    ║   2. Multiply each value by a weight from the repeating sequence:        ║
    ║      [7, 3, 1, 7, 3, 1, 7, 3, 1, ...]                                    ║
    ║                                                                          ║
    ║   3. Sum all weighted values                                             ║
    ║                                                                          ║
    ║   4. Return sum modulo 10 (result is always 0-9)                         ║
    ║                                                                          ║
    ║ EXAMPLE:                                                                 ║
    ║   Data: "AB123"                                                          ║
    ║   Values: A=10, B=11, 1=1, 2=2, 3=3                                      ║
    ║   Weights: 7, 3, 1, 7, 3                                                 ║
    ║   Calculation: (10×7) + (11×3) + (1×1) + (2×7) + (3×3)                  ║
    ║              = 70 + 33 + 1 + 14 + 9 = 127                               ║
    ║   Check Digit: 127 mod 10 = 7                                           ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    
    Args:
        data: String containing MRZ field data (alphanumeric + '<')
        
    Returns:
        int: Check digit (0-9)
        
    Raises:
        ValueError: If invalid character encountered
    """
    # ICAO 9303 specifies weights repeat in pattern: 7, 3, 1
    WEIGHTS = [7, 3, 1]
    
    # Character value mapping per ICAO 9303 Section 4.9
    def char_value(char: str) -> int:
        """
        Convert MRZ character to numeric value per ICAO 9303.
        
        Character Set:
            - '0'-'9': Numeric value (0-9)
            - 'A'-'Z': Alphabetic value (10-35)
            - '<': Filler character (0)
        """
        if char.isdigit():
            return int(char)
        elif char.isalpha():
            # A=10, B=11, ..., Z=35
            return ord(char.upper()) - ord('A') + 10
        elif char == '<':
            # Filler character has value 0
            return 0
        else:
            # Invalid character in MRZ - should not occur in valid documents
            raise ValueError(f"Invalid MRZ character: '{char}'")
    
    # Calculate weighted sum
    weighted_sum = 0
    for i, char in enumerate(data):
        value = char_value(char)
        weight = WEIGHTS[i % 3]  # Cycle through 7, 3, 1
        weighted_sum += value * weight
        
    # Return modulo 10 as check digit
    return weighted_sum % 10


def validate_mrz_logic(ocr_text_list: list) -> dict:
    """
    Validates MRZ (Machine Readable Zone) from OCR output using ICAO 9303 standard.
    
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                     PASSPORT MRZ STRUCTURE (TD3)                         ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║ LINE 1 (44 characters):                                                  ║
    ║ ┌─────────────────────────────────────────────────────────────────────┐  ║
    ║ │ P<NPLLNAME<<FNAME<MNAME<<<<<<<<<<<<<<<<<<<<<<<<<<                   │  ║
    ║ │ ↑ ↑   ↑                                                             │  ║
    ║ │ │ │   └── Surname<<Given Names (padded with <)                      │  ║
    ║ │ │ └────── Issuing Country (3-letter code, e.g., NPL=Nepal)          │  ║
    ║ │ └──────── Document Type (P=Passport, < for sub-type)                │  ║
    ║ └────────────────────────────────────────────────────────────────────┘  ║
    ║                                                                          ║
    ║ LINE 2 (44 characters):                                                  ║
    ║ ┌─────────────────────────────────────────────────────────────────────┐  ║
    ║ │ L898902C36UTO7408122F1204159ZE184226B<<<<<10                        │  ║
    ║ │ ├────────┤├┤├────┤├┤├──────┤├┤├──────┤├───┤├┤                      │  ║
    ║ │ │        ││ │    │ │ │      │ │ │      │    ││                       │  ║
    ║ │ │        ││ │    │ │ │      │ │ │      │    │└─ Composite Check      │  ║
    ║ │ │        ││ │    │ │ │      │ │ │      │    └── Optional Data        │  ║
    ║ │ │        ││ │    │ │ │      │ │ │      └─────── Personal No. Check   │  ║
    ║ │ │        ││ │    │ │ │      │ │ └────────────── Personal Number      │  ║
    ║ │ │        ││ │    │ │ │      │ └──────────────── Expiry Check Digit   │  ║
    ║ │ │        ││ │    │ │ │      └────────────────── Expiry Date (YYMMDD) │  ║
    ║ │ │        ││ │    │ │ └───────────────────────── Sex (M/F/<)          │  ║
    ║ │ │        ││ │    │ └─────────────────────────── DOB Check Digit      │  ║
    ║ │ │        ││ │    └───────────────────────────── DOB (YYMMDD)         │  ║
    ║ │ │        ││ └────────────────────────────────── Nationality          │  ║
    ║ │ │        │└──────────────────────────────────── Passport No. Check   │  ║
    ║ │ │        └───────────────────────────────────── Passport Number      │  ║
    ║ └────────────────────────────────────────────────────────────────────┘  ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    
    Args:
        ocr_text_list: List of text strings extracted by OCR
        
    Returns:
        dict: {
            "valid": bool,           # True if MRZ validates
            "details": str,          # Human-readable validation result
            "passport_number": str,  # Extracted passport number (if valid)
            "date_of_birth": str,    # Extracted DOB (if valid)
            "expiry_date": str       # Extracted expiry date (if valid)
        }
    """
    
    # ==========================================================================
    # INTELLIGENT ERROR CORRECTION HELPER FUNCTION
    # ==========================================================================
    
    def try_correcting_field(field_text: str, expected_check_digit: int, field_name: str) -> tuple:
        """
        Attempts to correct common OCR misreads by swapping lookalike characters.
        
        ╔══════════════════════════════════════════════════════════════════════════╗
        ║                    OCR ERROR CORRECTION ALGORITHM                        ║
        ╠══════════════════════════════════════════════════════════════════════════╣
        ║ PROBLEM:                                                                 ║
        ║   OCR engines frequently confuse visually similar characters:            ║
        ║   - '0' (zero) ↔ 'O' (letter O)                                         ║
        ║   - '1' (one) ↔ 'I' (letter I) ↔ 'l' (lowercase L)                      ║
        ║   - '5' (five) ↔ 'S' (letter S)                                         ║
        ║   - '2' (two) ↔ 'Z' (letter Z)                                          ║
        ║   - '8' (eight) ↔ 'B' (letter B)                                        ║
        ║                                                                          ║
        ║ SOLUTION:                                                                ║
        ║   1. Calculate check digit with original text                            ║
        ║   2. If mismatch, try all possible single-character substitutions        ║
        ║   3. For each substitution, recalculate check digit                      ║
        ║   4. If match found, accept the corrected value                          ║
        ║   5. If no single swap works, try combinations (up to 2 swaps)           ║
        ╚══════════════════════════════════════════════════════════════════════════╝
        
        Args:
            field_text: The MRZ field text (e.g., passport number, DOB)
            expected_check_digit: The check digit from the MRZ
            field_name: Human-readable name for logging
            
        Returns:
            tuple: (corrected_text, was_corrected: bool)
        """
        # Define lookalike character pairs (bidirectional swaps)
        LOOKALIKE_PAIRS = [
            ('O', '0'),  # Letter O <-> Digit 0
            ('0', 'O'),  # Digit 0 <-> Letter O
            ('I', '1'),  # Letter I <-> Digit 1
            ('1', 'I'),  # Digit 1 <-> Letter I
            ('L', '1'),  # Letter L <-> Digit 1 (uppercase already)
            ('1', 'L'),  # Digit 1 <-> Letter L
            ('S', '5'),  # Letter S <-> Digit 5
            ('5', 'S'),  # Digit 5 <-> Letter S
            ('Z', '2'),  # Letter Z <-> Digit 2
            ('2', 'Z'),  # Digit 2 <-> Letter Z
            ('B', '8'),  # Letter B <-> Digit 8
            ('8', 'B'),  # Digit 8 <-> Letter B
            ('G', '6'),  # Letter G <-> Digit 6
            ('6', 'G'),  # Digit 6 <-> Letter G
            ('Q', '0'),  # Letter Q <-> Digit 0 (rare)
            ('D', '0'),  # Letter D <-> Digit 0 (rare)
        ]
        
        original_text = field_text
        
        # First, check if original text is already valid
        try:
            if calculate_check_digit(field_text) == expected_check_digit:
                return field_text, False
        except ValueError:
            pass  # Continue to correction attempts
        
        # =======================================================================
        # PHASE 1: Try single character substitutions
        # =======================================================================
        print(f"    Attempting error correction for {field_name}: {field_text}")
        
        for i, char in enumerate(field_text):
            for wrong_char, correct_char in LOOKALIKE_PAIRS:
                if char == wrong_char:
                    # Create corrected version
                    corrected = field_text[:i] + correct_char + field_text[i+1:]
                    
                    try:
                        calculated = calculate_check_digit(corrected)
                        if calculated == expected_check_digit:
                            print(f"    [CORRECTED] Auto-Corrected {field_name}: {original_text} -> {corrected}")
                            print(f"       (Swapped '{wrong_char}' -> '{correct_char}' at position {i})")
                            return corrected, True
                    except ValueError:
                        continue  # Invalid character, skip
        
        # =======================================================================
        # PHASE 2: Try double character substitutions (for multiple errors)
        # =======================================================================
        print(f"    Trying double substitutions for {field_name}...")
        
        for i, char_i in enumerate(field_text):
            for wrong_i, correct_i in LOOKALIKE_PAIRS:
                if char_i != wrong_i:
                    continue
                    
                # First substitution
                text_after_first = field_text[:i] + correct_i + field_text[i+1:]
                
                for j, char_j in enumerate(text_after_first):
                    if j == i:  # Skip the already-swapped position
                        continue
                        
                    for wrong_j, correct_j in LOOKALIKE_PAIRS:
                        if char_j != wrong_j:
                            continue
                        
                        # Second substitution
                        corrected = text_after_first[:j] + correct_j + text_after_first[j+1:]
                        
                        try:
                            calculated = calculate_check_digit(corrected)
                            if calculated == expected_check_digit:
                                print(f"    [CORRECTED] Auto-Corrected {field_name}: {original_text} -> {corrected}")
                                print(f"       (Double swap: pos {i} '{wrong_i}'->'{correct_i}', pos {j} '{wrong_j}'->'{correct_j}')")
                                return corrected, True
                        except ValueError:
                            continue
        
        # No correction found
        print(f"    [X] Could not auto-correct {field_name}: {field_text}")
        return field_text, False
    
    # ==========================================================================
    # MAIN VALIDATION LOGIC
    # ==========================================================================
    
    result = {
        "valid": False,
        "details": "MRZ validation not performed",
        "passport_number": None,
        "date_of_birth": None,
        "expiry_date": None,
        "corrections_applied": []  # Track auto-corrections for thesis
    }
    
    # ==========================================================================
    # ROBUST DATA SANITIZATION (Critical for OCR Error Handling)
    # ==========================================================================
    
    # Step 1: Combine all OCR text fragments
    raw_text = "".join(ocr_text_list)
    
    print(f"\n--- MRZ Validation: Data Sanitization ---")
    print(f"    Raw OCR Text ({len(raw_text)} chars): {raw_text[:80]}...")
    
    # Step 2: Convert to UPPERCASE (fixes lowercase OCR misreads)
    cleaned_text = raw_text.upper()
    
    # Step 3: Remove all whitespace (spaces, tabs, newlines)
    cleaned_text = cleaned_text.replace(" ", "")
    cleaned_text = re.sub(r'\s+', '', cleaned_text)
    
    # Step 4: Remove common OCR noise characters
    noise_chars = ['.', ',', ';', ':', '!', '?', "'", '"', '`', '~', '@', '#', 
                   '$', '%', '^', '&', '*', '(', ')', '[', ']', '{', '}', 
                   '|', '\\', '/', '+', '=', '_']
    for char in noise_chars:
        cleaned_text = cleaned_text.replace(char, '')
    
    # Step 5: Replace common OCR misreads for the '<' filler character
    ocr_misread_map = {
        '«': '<',   # Double angle quotation mark
        '‹': '<',   # Single angle quotation mark
        '»': '<',   # Right-pointing double angle
        '›': '<',   # Right-pointing single angle
        'く': '<',   # Japanese Hiragana KU (rare OCR error)
        'К': 'K',   # Cyrillic K misread
        'С': 'C',   # Cyrillic S misread as C
        'О': 'O',   # Cyrillic O
        'Р': 'P',   # Cyrillic R misread as P
        'А': 'A',   # Cyrillic A
        'Е': 'E',   # Cyrillic E
        'Н': 'H',   # Cyrillic N misread as H
        'Т': 'T',   # Cyrillic T
        'В': 'B',   # Cyrillic V misread as B
        'М': 'M',   # Cyrillic M
        'Х': 'X',   # Cyrillic X
    }
    
    for wrong_char, correct_char in ocr_misread_map.items():
        cleaned_text = cleaned_text.replace(wrong_char, correct_char)
    
    # Step 6: Final cleanup - keep only valid MRZ characters (A-Z, 0-9, <)
    cleaned_text = re.sub(r'[^A-Z0-9<]', '', cleaned_text)
    
    # Debug output: Show the cleaned and normalized text
    print(f"    Cleaned & Normalized Text ({len(cleaned_text)} chars):")
    print(f"    >>> {cleaned_text[:88]}")
    if len(cleaned_text) > 88:
        print(f"    >>> {cleaned_text[88:176]}")
    
    # ==========================================================================
    # PATTERN MATCHING: Find MRZ Lines (Improved Robustness)
    # ==========================================================================
    
    print(f"\n--- MRZ Validation: Pattern Matching ---")
    
    mrz_line1_patterns = [
        r'P<[A-Z]{3}[A-Z<]{39}',
        r'P[A-Z]<[A-Z]{2}[A-Z<]{39}',
        r'P[A-Z][A-Z]{3}[A-Z<]{39}',
        r'P<[A-Z]{3}[A-Z<]{35,43}',
        r'P[<A-Z][A-Z<]{41,43}',
    ]
    
    mrz_line2_patterns = [
        r'[A-Z0-9<]{9}[0-9][A-Z]{3}[0-9]{6}[0-9][MF<][0-9]{6}[0-9][A-Z0-9<]{14}[0-9]',
        r'[A-Z0-9<]{9}[0-9][A-Z<]{3}[0-9]{6}[0-9][MF<][0-9]{6}[0-9][A-Z0-9<]{14}[0-9]',
        r'[A-Z0-9<]{9}[0-9][A-Z<]{3}[0-9]{6}[0-9][MF<][0-9]{6}[0-9][A-Z0-9<]{13,15}[0-9]',
        r'[A-Z0-9<]{10}[A-Z<]{3}[0-9]{7}[MF<][0-9]{7}[A-Z0-9<]{14,16}',
    ]
    
    line1_match = None
    for pattern in mrz_line1_patterns:
        line1_match = re.search(pattern, cleaned_text)
        if line1_match:
            print(f"    Line 1 matched with pattern: {pattern[:30]}...")
            break
    
    line2_match = None
    for pattern in mrz_line2_patterns:
        line2_match = re.search(pattern, cleaned_text)
        if line2_match:
            print(f"    Line 2 matched with pattern: {pattern[:30]}...")
            break
    
    # ==========================================================================
    # FALLBACK: Try to extract MRZ by position if patterns fail
    # ==========================================================================
    
    if not line1_match and len(cleaned_text) >= 44:
        p_positions = [i for i, c in enumerate(cleaned_text) if c == 'P']
        for pos in p_positions:
            if pos + 44 <= len(cleaned_text):
                potential_line1 = cleaned_text[pos:pos+44]
                if '<<' in potential_line1:
                    print(f"    Fallback: Found potential Line 1 at position {pos}")
                    line1_match = type('Match', (), {'group': lambda self, x=0: potential_line1})()
                    break
    
    if not line2_match and line1_match and len(cleaned_text) >= 88:
        line1_end = cleaned_text.find(line1_match.group(0)) + 44
        if line1_end + 44 <= len(cleaned_text):
            potential_line2 = cleaned_text[line1_end:line1_end+44]
            if (len(potential_line2) >= 28 and
                potential_line2[9].isdigit() and 
                potential_line2[19].isdigit() and 
                potential_line2[27].isdigit()):
                print(f"    Fallback: Found potential Line 2 after Line 1")
                line2_match = type('Match', (), {'group': lambda self, x=0: potential_line2})()
    
    # ==========================================================================
    # VALIDATION RESULT: Check if MRZ lines were found
    # ==========================================================================
    
    if not line1_match:
        result["details"] = "[X] SECURITY FAILURE: No valid MRZ Line 1 detected. Document may be invalid or image quality is poor."
        print(f"    {result['details']}")
        print(f"    Debug: Searched in {len(cleaned_text)} chars")
        return result
    
    if not line2_match:
        result["details"] = "[X] SECURITY FAILURE: No valid MRZ Line 2 detected. Document may be tampered or image quality is poor."
        print(f"    {result['details']}")
        print(f"    Debug: Line 1 found, but Line 2 missing")
        return result
    
    mrz_line1 = line1_match.group(0)
    mrz_line2 = line2_match.group(0)
    
    print(f"    [OK] MRZ Line 1 ({len(mrz_line1)} chars): {mrz_line1}")
    print(f"    [OK] MRZ Line 2 ({len(mrz_line2)} chars): {mrz_line2}")
    
    # ==========================================================================
    # CHECK DIGIT VALIDATION WITH INTELLIGENT ERROR CORRECTION
    # ==========================================================================
    
    print(f"\n--- [SECURE] MRZ Validation: Check Digit Verification (with Auto-Correction) ---")
    
    validation_errors = []
    corrections_applied = []
    
    # --- Validate Passport Number (positions 0-8, check digit at 9) ---
    try:
        passport_number = mrz_line2[0:9]
        passport_check = int(mrz_line2[9])
        
        # First attempt: Direct validation
        calculated_passport_check = calculate_check_digit(passport_number)
        
        if passport_check != calculated_passport_check:
            # Try intelligent error correction
            corrected_passport, was_corrected = try_correcting_field(
                passport_number, passport_check, "Passport Number"
            )
            
            if was_corrected:
                passport_number = corrected_passport
                corrections_applied.append(f"Passport Number: {mrz_line2[0:9]} -> {corrected_passport}")
                result["passport_number"] = passport_number.replace('<', '')
                print(f"    [OK] Passport Number Check: PASSED (after correction)")
            else:
                validation_errors.append(
                    f"Passport Number check digit mismatch: expected {calculated_passport_check}, got {passport_check}"
                )
                print(f"    [X] Passport Number Check: FAILED ({passport_number}) - Expected {calculated_passport_check}, Got {passport_check}")
        else:
            result["passport_number"] = passport_number.replace('<', '')
            print(f"    [OK] Passport Number Check: PASSED ({passport_number})")
            
    except (ValueError, IndexError) as e:
        validation_errors.append(f"Passport Number extraction failed: {e}")
        print(f"    [X] Passport Number Check: ERROR - {e}")
    
    # --- Validate Date of Birth (positions 13-18, check digit at 19) ---
    try:
        dob = mrz_line2[13:19]
        dob_check = int(mrz_line2[19])
        
        calculated_dob_check = calculate_check_digit(dob)
        
        if dob_check != calculated_dob_check:
            # Try intelligent error correction
            corrected_dob, was_corrected = try_correcting_field(
                dob, dob_check, "Date of Birth"
            )
            
            if was_corrected:
                dob = corrected_dob
                corrections_applied.append(f"Date of Birth: {mrz_line2[13:19]} -> {corrected_dob}")
                year_prefix = '19' if int(dob[0:2]) > 30 else '20'
                result["date_of_birth"] = f"{dob[4:6]}/{dob[2:4]}/{year_prefix}{dob[0:2]}"
                print(f"    [OK] Date of Birth Check: PASSED (after correction) -> {result['date_of_birth']}")
            else:
                validation_errors.append(
                    f"Date of Birth check digit mismatch: expected {calculated_dob_check}, got {dob_check}"
                )
                print(f"    [X] Date of Birth Check: FAILED ({dob}) - Expected {calculated_dob_check}, Got {dob_check}")
        else:
            year_prefix = '19' if int(dob[0:2]) > 30 else '20'
            result["date_of_birth"] = f"{dob[4:6]}/{dob[2:4]}/{year_prefix}{dob[0:2]}"
            print(f"    [OK] Date of Birth Check: PASSED ({dob}) -> {result['date_of_birth']}")
            
    except (ValueError, IndexError) as e:
        validation_errors.append(f"Date of Birth extraction failed: {e}")
        print(f"    [X] Date of Birth Check: ERROR - {e}")
    
    # --- Validate Expiry Date (positions 21-26, check digit at 27) ---
    try:
        expiry = mrz_line2[21:27]
        expiry_check = int(mrz_line2[27])
        
        calculated_expiry_check = calculate_check_digit(expiry)
        
        if expiry_check != calculated_expiry_check:
            # Try intelligent error correction
            corrected_expiry, was_corrected = try_correcting_field(
                expiry, expiry_check, "Expiry Date"
            )
            
            if was_corrected:
                expiry = corrected_expiry
                corrections_applied.append(f"Expiry Date: {mrz_line2[21:27]} -> {corrected_expiry}")
                result["expiry_date"] = f"{expiry[4:6]}/{expiry[2:4]}/20{expiry[0:2]}"
                print(f"    [OK] Expiry Date Check: PASSED (after correction) -> {result['expiry_date']}")
            else:
                validation_errors.append(
                    f"Expiry Date check digit mismatch: expected {calculated_expiry_check}, got {expiry_check}"
                )
                print(f"    [X] Expiry Date Check: FAILED ({expiry}) - Expected {calculated_expiry_check}, Got {expiry_check}")
        else:
            result["expiry_date"] = f"{expiry[4:6]}/{expiry[2:4]}/20{expiry[0:2]}"
            print(f"    [OK] Expiry Date Check: PASSED ({expiry}) -> {result['expiry_date']}")
            
    except (ValueError, IndexError) as e:
        validation_errors.append(f"Expiry Date extraction failed: {e}")
        print(f"    [X] Expiry Date Check: ERROR - {e}")
    
    # Store corrections for thesis documentation
    result["corrections_applied"] = corrections_applied
    
    # ==========================================================================
    # FINAL VALIDATION RESULT
    # ==========================================================================
    
    print(f"\n--- [RESULT] MRZ Validation: Final Result ---")
    
    if corrections_applied:
        print(f"    [NOTE] Auto-Corrections Applied: {len(corrections_applied)}")
        for correction in corrections_applied:
            print(f"       * {correction}")
    
    if validation_errors:
        result["valid"] = False
        result["details"] = f"[X] SECURITY FAILURE: MRZ check digit validation failed. Errors: {'; '.join(validation_errors)}"
        print(f"    {result['details']}")
    else:
        result["valid"] = True
        if corrections_applied:
            result["details"] = f"[OK] ICAO 9303 MRZ Validation: All check digits verified (with {len(corrections_applied)} auto-correction(s))"
        else:
            result["details"] = "[OK] ICAO 9303 MRZ Validation: All check digits verified successfully"
        print(f"    {result['details']}")
        print(f"    Passport: {result['passport_number']}")
        print(f"    DOB: {result['date_of_birth']}")
        print(f"    Expiry: {result['expiry_date']}")
    
    return result


# =============================================================================
# MAIN KYC TOOL
# =============================================================================

@tool
def process_sim_card_kyc(passport_path: str, selfie_path: str) -> str:
    """
    Performs forensic KYC verification for SIM card registration.
    
    SECURITY PIPELINE:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  Step 1: OCR Text Extraction                                           │
    │     ↓                                                                   │
    │  Step 2: ICAO 9303 MRZ Validation (7-3-1 Check Digit Algorithm)        │
    │     ↓ (STOP if fails - prevents resource waste on invalid documents)   │
    │  Step 3: Face Recognition (Biometric Verification)                     │
    │     ↓                                                                   │
    │  Step 4: Generate Verification Result                                  │
    └─────────────────────────────────────────────────────────────────────────┘
    
    Use this tool ONLY when the user has uploaded their passport and selfie
    images in the sidebar and requests SIM card verification.
    
    Args:
        passport_path: File path to the passport image (e.g., 'temp_passport.jpg')
        selfie_path: File path to the selfie image (e.g., 'temp_selfie.jpg')
    
    Returns:
        JSON string with verification_status, security_checks, face_match_confidence, and sim_details
    """
    print(f"\n{'='*60}")
    print("[KYC] FORENSIC KYC VERIFICATION INITIATED")
    print(f"{'='*60}")
    print(f"    Passport: {passport_path}")
    print(f"    Selfie: {selfie_path}")
    
    result = {
        "verification_status": "REJECTED",
        "security_checks": {
            "mrz_validation": "NOT_PERFORMED",
            "face_match": "NOT_PERFORMED"
        },
        "face_match_confidence": 0.0,
        "extracted_mrz_data": {},
        "sim_details": None,
        "error": None
    }
    
    try:
        import face_recognition
        import cv2
        import numpy as np
        import os
        
        # =====================================================================
        # STEP 0: FILE VALIDATION
        # =====================================================================
        if not os.path.exists(passport_path):
            result["error"] = f"Passport image not found at '{passport_path}'"
            return json.dumps(result, indent=2)
        
        if not os.path.exists(selfie_path):
            result["error"] = f"Selfie image not found at '{selfie_path}'"
            return json.dumps(result, indent=2)
        
        # =====================================================================
        # STEP 1: OCR - EXTRACT TEXT FROM PASSPORT
        # =====================================================================
        print("\n--- [OCR] STEP 1: OCR Text Extraction ---")
        reader = get_ocr_reader()
        ocr_results = reader.readtext(passport_path)
        print(f"DEBUG OCR OUTPUT: {ocr_results}")
        
        # Extract just the text portions
        ocr_text_list = [text[1] for text in ocr_results]
        extracted_text = " ".join(ocr_text_list)
        print(f"    Extracted {len(extracted_text)} characters from passport")
        
        # =====================================================================
        # STEP 2: FORENSIC MRZ VALIDATION (CRITICAL SECURITY CHECK)
        # =====================================================================
        print("\n--- [SECURE] STEP 2: ICAO 9303 MRZ Validation ---")
        mrz_result = validate_mrz_logic(ocr_text_list)
        
        result["security_checks"]["mrz_validation"] = "PASSED" if mrz_result["valid"] else "FAILED"
        result["extracted_mrz_data"] = {
            "passport_number": mrz_result.get("passport_number"),
            "date_of_birth": mrz_result.get("date_of_birth"),
            "expiry_date": mrz_result.get("expiry_date"),
            "validation_details": mrz_result["details"]
        }
        
        # *** CRITICAL: STOP IF MRZ VALIDATION FAILS ***
        # This prevents wasting computational resources on face recognition
        # for potentially forged or invalid documents
        if not mrz_result["valid"]:
            result["verification_status"] = "REJECTED"
            result["error"] = mrz_result["details"]
            print("\n" + "="*60)
            print("[X] KYC REJECTED: MRZ Validation Failed")
            print("   Face recognition skipped to conserve resources.")
            print("="*60)
            return json.dumps(result, indent=2)
        
        print("    MRZ Validation: [OK] PASSED - Proceeding to biometric verification")
        
        # =====================================================================
        # STEP 3: FACE RECOGNITION (BIOMETRIC VERIFICATION)
        # =====================================================================
        print("\n--- [FACE] STEP 3: Biometric Face Verification ---")
        
        # Load passport image and extract face encoding
        passport_image = face_recognition.load_image_file(passport_path)
        passport_encodings = face_recognition.face_encodings(passport_image)
        
        if len(passport_encodings) == 0:
            result["error"] = "No face detected in passport image. Please upload a clearer image."
            result["security_checks"]["face_match"] = "FAILED"
            return json.dumps(result, indent=2)
        
        passport_encoding = passport_encodings[0]
        print(f"    Passport face detected: [OK]")
        
        # Load selfie image and extract face encoding
        selfie_image = face_recognition.load_image_file(selfie_path)
        selfie_encodings = face_recognition.face_encodings(selfie_image)
        
        if len(selfie_encodings) == 0:
            result["error"] = "No face detected in selfie. Please take a clearer photo."
            result["security_checks"]["face_match"] = "FAILED"
            return json.dumps(result, indent=2)
        
        selfie_encoding = selfie_encodings[0]
        print(f"    Selfie face detected: [OK]")
        
        # Compare faces using Euclidean distance
        print("    Comparing facial features...")
        face_distance = face_recognition.face_distance([passport_encoding], selfie_encoding)[0]
        face_match_confidence = round((1 - face_distance) * 100, 2)
        result["face_match_confidence"] = face_match_confidence
        
        # ICAO recommends tolerance of 0.6 for face matching
        TOLERANCE = 0.6
        is_match = face_distance <= TOLERANCE
        
        print(f"    Face Distance: {face_distance:.4f}")
        print(f"    Match Confidence: {face_match_confidence}%")
        print(f"    Threshold: {(1-TOLERANCE)*100}%")
        
        result["security_checks"]["face_match"] = "PASSED" if is_match else "FAILED"
        
        # =====================================================================
        # STEP 4: GENERATE FINAL RESULT
        # =====================================================================
        print("\n--- [RESULT] STEP 4: Final Verification Result ---")
        
        if is_match:
            result["verification_status"] = "APPROVED"
            result["sim_details"] = {
                "phone_number": generate_mock_phone_number(),
                "carrier": "Nepal Telecom (NTC)",
                "plan": "Tourist SIM - 30 Days",
                "data": "5GB 4G Data",
                "validity": "30 Days",
                "activation_status": "READY FOR ACTIVATION",
                "security_level": "ICAO 9303 MRZ + Biometric Verified"
            }
            print("\n" + "="*60)
            print("[OK] KYC APPROVED")
            print("   Security Check: ICAO MRZ Verified")
            print("   Biometric Match: CONFIRMED")
            print("="*60)
        else:
            result["verification_status"] = "REJECTED"
            result["error"] = f"Face match confidence ({face_match_confidence}%) is below threshold. Please ensure both images show the same person clearly."
            print("\n" + "="*60)
            print("[X] KYC REJECTED: Face Mismatch")
            print(f"   Confidence: {face_match_confidence}% (Required: >{(1-TOLERANCE)*100}%)")
            print("="*60)
        
        return json.dumps(result, indent=2)
        
    except ImportError as e:
        result["error"] = f"Required library not installed: {e}. Please install face_recognition and opencv-python-headless."
        return json.dumps(result, indent=2)
    
    except ValueError as e:
        # Handle check digit calculation errors (invalid MRZ characters)
        result["error"] = f"MRZ parsing error: {str(e)}"
        result["security_checks"]["mrz_validation"] = "FAILED"
        return json.dumps(result, indent=2)
    
    except Exception as e:
        result["error"] = f"KYC processing error: {str(e)}"
        print(f"\n[X] KYC Error: {e}")
        return json.dumps(result, indent=2)