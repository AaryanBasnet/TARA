"""
Boarding Pass Scanner - OCR-based Flight Information Extraction

This module implements boarding pass scanning using:
1. EasyOCR for text extraction
2. Regex pattern matching for structured field extraction
3. Integration with flight status tools

Technical Flow:
    Image → OCR → Pattern Matching → Field Extraction → Flight Lookup
"""

import re
import json
from datetime import datetime, timedelta
from typing import Optional
from langchain_core.tools import tool

# --- Initialize OCR Reader (Lazy Loading - Shared with KYC) ---
_ocr_reader = None


def get_ocr_reader():
    """
    Lazy initialization of EasyOCR reader. FORCES CPU MODE (gpu=False)
    for stability, bypassing complex CUDA/NVIDIA setup issues.
    """
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        print("--- Initializing EasyOCR Reader (CPU MODE)... ---")
        _ocr_reader = easyocr.Reader(['en'], gpu=False)
        print("--- EasyOCR Reader Initialized (CPU) ---")
    return _ocr_reader


# =============================================================================
# BOARDING PASS FIELD PATTERNS
# =============================================================================

# Common airline codes (expanded)
AIRLINE_CODES = {
    # Nepal Airlines
    "RA": "Nepal Airlines",
    "9N": "Shree Airlines",
    "YT": "Yeti Airlines",
    "U4": "Buddha Air",
    "H9": "Himalaya Airlines",
    "KB": "Druk Air",
    # International
    "SQ": "Singapore Airlines",
    "TG": "Thai Airways",
    "AI": "Air India",
    "6E": "IndiGo",
    "UK": "Vistara",
    "G8": "Go First",
    "CZ": "China Southern",
    "MU": "China Eastern",
    "CA": "Air China",
    "QR": "Qatar Airways",
    "EK": "Emirates",
    "FZ": "Flydubai",
    "WY": "Oman Air",
    "GF": "Gulf Air",
    "UL": "SriLankan Airlines",
    "BG": "Biman Bangladesh",
    "BA": "British Airways",
    "LH": "Lufthansa",
    "AF": "Air France",
    "KL": "KLM",
    "AA": "American Airlines",
    "UA": "United Airlines",
    "DL": "Delta Airlines",
    "JL": "Japan Airlines",
    "NH": "All Nippon Airways",
    "CX": "Cathay Pacific",
    "MH": "Malaysia Airlines",
    "GA": "Garuda Indonesia",
    "VN": "Vietnam Airlines",
    "OZ": "Asiana Airlines",
    "KE": "Korean Air",
    "ET": "Ethiopian Airlines",
    "MS": "EgyptAir",
    "TK": "Turkish Airlines",
    "SV": "Saudia",
    "PK": "Pakistan International",
}

# Extended airport codes with city names
AIRPORT_CODES = {
    # South Asia
    "KTM": "Kathmandu", "DEL": "Delhi", "BOM": "Mumbai", "MAA": "Chennai",
    "BLR": "Bangalore", "HYD": "Hyderabad", "CCU": "Kolkata", "COK": "Kochi",
    "DAC": "Dhaka", "CMB": "Colombo", "ISB": "Islamabad", "KHI": "Karachi",
    "LHE": "Lahore", "MLE": "Male",
    # Southeast Asia
    "SIN": "Singapore", "BKK": "Bangkok", "KUL": "Kuala Lumpur", "CGK": "Jakarta",
    "MNL": "Manila", "SGN": "Ho Chi Minh", "HAN": "Hanoi", "RGN": "Yangon",
    # East Asia
    "HKG": "Hong Kong", "PEK": "Beijing", "PVG": "Shanghai", "CAN": "Guangzhou",
    "TPE": "Taipei", "NRT": "Tokyo Narita", "HND": "Tokyo Haneda", "ICN": "Seoul",
    # Middle East
    "DXB": "Dubai", "DOH": "Doha", "AUH": "Abu Dhabi", "MCT": "Muscat",
    "BAH": "Bahrain", "KWI": "Kuwait", "RUH": "Riyadh", "JED": "Jeddah",
    "AMM": "Amman", "TLV": "Tel Aviv",
    # Europe
    "LHR": "London Heathrow", "CDG": "Paris", "FRA": "Frankfurt", "AMS": "Amsterdam",
    "ZRH": "Zurich", "MUC": "Munich", "FCO": "Rome", "MAD": "Madrid",
    "IST": "Istanbul", "ATH": "Athens",
    # Americas
    "JFK": "New York JFK", "LAX": "Los Angeles", "SFO": "San Francisco",
    "ORD": "Chicago", "DFW": "Dallas", "MIA": "Miami", "YYZ": "Toronto",
    # Africa
    "CAI": "Cairo", "ADD": "Addis Ababa", "NBO": "Nairobi", "JNB": "Johannesburg",
    # Oceania
    "SYD": "Sydney", "MEL": "Melbourne", "AKL": "Auckland",
}

# City name to code mapping (reverse lookup)
CITY_TO_CODE = {v.upper(): k for k, v in AIRPORT_CODES.items()}


def extract_boarding_pass_fields(ocr_text_list: list) -> dict:
    """
    Extracts structured fields from OCR text of a boarding pass.
    Enhanced with multiple pattern formats for better extraction.
    """

    # Combine all OCR text and also keep individual segments for analysis
    raw_text = " ".join(ocr_text_list).upper()
    # Also create version with each OCR segment on new line for pattern matching
    segmented_text = "\n".join(ocr_text_list).upper()

    print(f"\n--- Boarding Pass OCR Analysis ---")
    print(f"    Raw text ({len(raw_text)} chars): {raw_text[:300]}...")
    print(f"    Segments: {ocr_text_list[:10]}")

    result = {
        "flight_number": None,
        "airline": None,
        "passenger_name": None,
        "origin": None,
        "destination": None,
        "date": None,
        "seat": None,
        "gate": None,
        "boarding_time": None,
        "departure_time": None,
        "class": None,
        "booking_ref": None,
        "confidence": 0,
        "raw_text": raw_text[:500]
    }

    fields_found = 0

    # ==========================================================================
    # FLIGHT NUMBER EXTRACTION (Most Critical) - Enhanced for non-standard formats
    # ==========================================================================
    flight_patterns = [
        r'(?:FLIGHT|FLT|FL|FLIGHT\s*NO)[:\s#;]*([A-Z]{1,3})[\s-]?(\d{2,4})',  # FLIGHT: RA 205, FLIGHT NO ABC1234
        r'(?:FLIGHT|FLT|FL)[:\s#]*([A-Z]\d)[\s-]?(\d{2,4})',   # FLIGHT: 9N 512
        r'\b([A-Z]{1,3})[\s]?(\d{3,4})\b',                      # F2784, ABC1234, RA205
        r'\b([A-Z]{2})[\s-]?(\d{3,4})\b',                       # RA205, RA 205
        r'\b([A-Z]\d)[\s-]?(\d{3,4})\b',                        # 9N512
    ]

    for pattern in flight_patterns:
        matches = re.findall(pattern, raw_text)
        for match in matches:
            airline_code = match[0]
            flight_num = match[1]
            # Validate it looks like a real flight
            if airline_code in AIRLINE_CODES or (len(airline_code) >= 1 and len(flight_num) >= 3):
                result["flight_number"] = f"{airline_code}{flight_num}"
                result["airline"] = AIRLINE_CODES.get(airline_code, airline_code)
                fields_found += 2
                print(f"    Flight: {result['flight_number']} ({result['airline']})")
                break
        if result["flight_number"]:
            break

    # ==========================================================================
    # PASSENGER NAME EXTRACTION (Enhanced for various formats)
    # ==========================================================================
    name_patterns = [
        r'(?:PASSENGER|NAME|PAX|TRAVELER|NAME\s*OF\s*PASSENGER)[:\s]*([A-Z][A-Z\s]+)[/]([A-Z][A-Z\s]+)',
        r'(?:PASSENGER|NAME|PAX)[:\s]*([A-Z]{2,})\s+([A-Z]{2,})',
        r'\b([A-Z]{2,15})/([A-Z]{2,15})\s*(?:MR|MRS|MS|MISS)?',
        r'(?:MR|MRS|MS|MISS)\s+([A-Z]{2,15})\s+([A-Z]{2,15})',
        r'\b([A-Z]{3,15})/([A-Z]{3,15})\b',
    ]

    # Also try single full name pattern (JOHN DOE, MORGAN MAXWELL)
    single_name_pattern = r'(?:PASSENGER|NAME|PAX|NAME\s*OF\s*PASSENGER)[:\s]*([A-Z]{2,15})\s+([A-Z]{2,15})(?:\s|$)'

    for pattern in name_patterns:
        match = re.search(pattern, raw_text)
        if match:
            part1 = match.group(1).strip()
            part2 = match.group(2).strip()
            if part1 not in ['BOARDING', 'FLIGHT', 'GATE', 'SEAT', 'DATE', 'FROM', 'CLASS', 'NAME', 'TIME']:
                result["passenger_name"] = f"{part1}/{part2}"
                fields_found += 1
                print(f"    Passenger: {result['passenger_name']}")
                break

    # Try single name pattern if no match yet
    if not result["passenger_name"]:
        match = re.search(single_name_pattern, raw_text)
        if match:
            result["passenger_name"] = f"{match.group(1)}/{match.group(2)}"
            fields_found += 1
            print(f"    Passenger: {result['passenger_name']}")

    # ==========================================================================
    # ORIGIN/DESTINATION EXTRACTION (Enhanced for country/city names)
    # ==========================================================================

    # Pattern 1: Direct route format - support both codes and full names
    route_patterns = [
        r'\b([A-Z]{3})\s*[-→>]\s*([A-Z]{3})\b',                    # DEL-KTM, DEL→KTM
        r'\b([A-Z]{3})\s+TO\s+([A-Z]{3})\b',                        # DEL TO KTM
        r'(?:FROM|ORIGIN|DEPART)[:\s;]*([A-Z]{3})',                 # FROM: DEL
        r'(?:TO|DEST|DESTINATION|ARRIVE|ARR)[:\s;]*([A-Z]{3})',    # TO: KTM
    ]

    # Extended: Full city/country names
    full_name_route = r'(?:FROM)[:\s;]*([A-Z][A-Z\s]{2,20})(?:\s+TO\s+|[→>-]\s*)([A-Z][A-Z\s]{2,20})'
    match = re.search(full_name_route, raw_text)
    if match:
        result["origin"] = match.group(1).strip()
        result["destination"] = match.group(2).strip()
        fields_found += 2
        print(f"    Route: {result['origin']} -> {result['destination']}")

    # Try direct route first
    for pattern in route_patterns[:2]:
        match = re.search(pattern, raw_text)
        if match:
            origin_code = match.group(1)
            dest_code = match.group(2)
            if origin_code in AIRPORT_CODES or dest_code in AIRPORT_CODES:
                result["origin"] = AIRPORT_CODES.get(origin_code, origin_code)
                result["destination"] = AIRPORT_CODES.get(dest_code, dest_code)
                fields_found += 2
                print(f"    Route: {result['origin']} → {result['destination']}")
                break

    # Try individual FROM/TO if direct route not found
    if not result["origin"]:
        match = re.search(r'(?:FROM|ORIGIN|DEPART)[:\s]*([A-Z]{3})', raw_text)
        if match and match.group(1) in AIRPORT_CODES:
            result["origin"] = AIRPORT_CODES.get(match.group(1), match.group(1))
            fields_found += 1

    if not result["destination"]:
        match = re.search(r'(?:TO|DEST|DESTINATION|ARRIVE)[:\s]*([A-Z]{3})', raw_text)
        if match and match.group(1) in AIRPORT_CODES:
            result["destination"] = AIRPORT_CODES.get(match.group(1), match.group(1))
            fields_found += 1

    # Pattern 2: Look for city names
    if not result["origin"] or not result["destination"]:
        for city_name, code in CITY_TO_CODE.items():
            if city_name in raw_text:
                if not result["origin"]:
                    result["origin"] = AIRPORT_CODES.get(code, city_name)
                    fields_found += 1
                elif not result["destination"] and result["origin"] != AIRPORT_CODES.get(code):
                    result["destination"] = AIRPORT_CODES.get(code, city_name)
                    fields_found += 1

    # Pattern 3: Find any 3-letter airport codes in text
    if not result["origin"] or not result["destination"]:
        found_codes = []
        for code in AIRPORT_CODES.keys():
            if re.search(rf'\b{code}\b', raw_text):
                found_codes.append(code)
        if len(found_codes) >= 2:
            if not result["origin"]:
                result["origin"] = AIRPORT_CODES.get(found_codes[0], found_codes[0])
                fields_found += 1
            if not result["destination"]:
                result["destination"] = AIRPORT_CODES.get(found_codes[1], found_codes[1])
                fields_found += 1

    if result["origin"]:
        print(f"    Origin: {result['origin']}")
    if result["destination"]:
        print(f"    Destination: {result['destination']}")

    # ==========================================================================
    # DATE EXTRACTION (Enhanced)
    # ==========================================================================
    date_patterns = [
        r'\b(\d{1,2})\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s*[,]?\s*(\d{2,4})?\b',
        r'\b(\d{1,2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{2,4})?\b',
        r'(?:DATE|DT)[:\s]*(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})',
        r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',  # 2024-12-17
        r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b',  # 17/12/2024
    ]

    for pattern in date_patterns:
        match = re.search(pattern, raw_text)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                if groups[1] in ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']:
                    day = groups[0]
                    month = groups[1][:3]
                    year = groups[2] if len(groups) > 2 and groups[2] else "2024"
                    if len(str(year)) == 2:
                        year = f"20{year}"
                    result["date"] = f"{day} {month} {year}"
                else:
                    # Numeric date format
                    result["date"] = f"{groups[0]}/{groups[1]}/{groups[2] if len(groups) > 2 else '2024'}"
                fields_found += 1
                print(f"    Date: {result['date']}")
                break

    # ==========================================================================
    # SEAT EXTRACTION (Enhanced)
    # ==========================================================================
    seat_patterns = [
        r'(?:SEAT|ST|ASIENTO)[:\s#]*(\d{1,2}[A-HJ-K])',
        r'\bSEAT\s*(\d{1,2}[A-HJ-K])\b',
        r'\b(\d{1,2}[A-HJ-K])\s*(?:SEAT|WINDOW|AISLE|MIDDLE)',
        r'(?:^|\s)(\d{1,2}[A-F])(?:\s|$)',  # Standalone seat like "12A"
    ]

    for pattern in seat_patterns:
        match = re.search(pattern, raw_text)
        if match:
            seat = match.group(1)
            # Validate seat number (1-99 + letter A-K excluding I)
            seat_num = int(re.match(r'\d+', seat).group())
            if 1 <= seat_num <= 99:
                result["seat"] = seat
                fields_found += 1
                print(f"    Seat: {result['seat']}")
                break

    # ==========================================================================
    # GATE EXTRACTION (Enhanced)
    # ==========================================================================
    gate_patterns = [
        r'(?:GATE|GT|PUERTA)[:\s#]*([A-Z]?\d{1,2}[A-Z]?)',
        r'\bGATE\s+([A-Z]?\d{1,2}[A-Z]?)\b',
        r'\bG[:\s]*(\d{1,2})\b',
    ]

    for pattern in gate_patterns:
        match = re.search(pattern, raw_text)
        if match:
            result["gate"] = match.group(1)
            fields_found += 1
            print(f"    Gate: {result['gate']}")
            break

    # ==========================================================================
    # TIME EXTRACTION (Enhanced - Boarding & Departure)
    # ==========================================================================
    boarding_patterns = [
        r'(?:BOARDING|BRD|BOARD|EMBARQUE)[:\s]*(\d{1,2})[:\.]?(\d{2})',
        r'(?:BOARDING|BRD)[:\s]*(\d{4})',  # 0830 format
    ]

    for pattern in boarding_patterns:
        match = re.search(pattern, raw_text)
        if match:
            if len(match.groups()) == 2:
                result["boarding_time"] = f"{match.group(1)}:{match.group(2)}"
            else:
                time_str = match.group(1)
                result["boarding_time"] = f"{time_str[:2]}:{time_str[2:]}"
            fields_found += 1
            print(f"    Boarding: {result['boarding_time']}")
            break

    departure_patterns = [
        r'(?:DEPARTURE|DEP|DEPART|STD|SALIDA)[:\s]*(\d{1,2})[:\.]?(\d{2})',
        r'(?:DEPARTURE|DEP|STD)[:\s]*(\d{4})',
    ]

    for pattern in departure_patterns:
        match = re.search(pattern, raw_text)
        if match:
            if len(match.groups()) == 2:
                result["departure_time"] = f"{match.group(1)}:{match.group(2)}"
            else:
                time_str = match.group(1)
                result["departure_time"] = f"{time_str[:2]}:{time_str[2:]}"
            fields_found += 1
            print(f"    Departure: {result['departure_time']}")
            break

    # ==========================================================================
    # CLASS EXTRACTION (Enhanced)
    # ==========================================================================
    class_patterns = [
        r'(?:CLASS|CLASE|CL)[:\s]*(ECONOMY|BUSINESS|FIRST|PREMIUM|ECO|BUS)',
        r'\b(ECONOMY|BUSINESS|FIRST|PREMIUM\s*ECONOMY)\b',
        r'(?:CLASS|CL)[:\s]*([YCJFWSB])\b',  # Single letter codes
        r'\b(ECONOMY\s*CLASS|BUSINESS\s*CLASS|FIRST\s*CLASS)\b',
    ]

    class_map = {
        "Y": "Economy", "S": "Economy", "W": "Premium Economy",
        "C": "Business", "J": "Business", "B": "Business",
        "F": "First", "ECO": "Economy", "BUS": "Business",
        "PREMIUM": "Premium Economy"
    }

    for pattern in class_patterns:
        match = re.search(pattern, raw_text)
        if match:
            cls = match.group(1).strip()
            result["class"] = class_map.get(cls, cls.title())
            fields_found += 1
            print(f"    Class: {result['class']}")
            break

    # ==========================================================================
    # BOOKING REFERENCE (PNR)
    # ==========================================================================
    pnr_patterns = [
        r'(?:PNR|BOOKING|CONFIRM|REF|LOCATOR)[:\s#]*([A-Z0-9]{5,8})',
        r'\b([A-Z]{6})\b',  # 6-letter PNR
    ]

    for pattern in pnr_patterns:
        match = re.search(pattern, raw_text)
        if match:
            pnr = match.group(1)
            # Validate PNR (should be alphanumeric, 5-8 chars)
            if 5 <= len(pnr) <= 8 and pnr not in ['BOARDING', 'ECONOMY', 'BUSINESS']:
                result["booking_ref"] = pnr
                fields_found += 1
                print(f"    Booking Ref: {result['booking_ref']}")
                break

    # ==========================================================================
    # CALCULATE CONFIDENCE SCORE
    # ==========================================================================
    # Weight different fields by importance
    weights = {
        "flight_number": 20,
        "passenger_name": 15,
        "origin": 12,
        "destination": 12,
        "date": 10,
        "seat": 8,
        "gate": 8,
        "boarding_time": 8,
        "class": 7,
    }

    total_weight = sum(weights.values())
    achieved_weight = sum(weights[k] for k, v in result.items() if v and k in weights)
    result["confidence"] = min(100, int((achieved_weight / total_weight) * 100))

    print(f"    Confidence: {result['confidence']}% ({fields_found} fields extracted)")

    return result


# =============================================================================
# TIME CALCULATION & CONTEXTUAL ADVICE
# =============================================================================

def calculate_time_to_departure(departure_time: str, flight_date: str = None) -> dict:
    """
    Calculates time remaining until departure and provides contextual advice.

    Args:
        departure_time: Departure time in HH:MM format (e.g., "14:30")
        flight_date: Flight date string (optional, defaults to today)

    Returns:
        dict with time_remaining, hours, minutes, and contextual advice
    """
    result = {
        "hours": 0,
        "minutes": 0,
        "time_remaining": "Unknown",
        "advice": "",
        "urgency": "normal"  # normal, soon, urgent, passed
    }

    try:
        now = datetime.now()

        # Parse departure time
        dep_parts = departure_time.replace(".", ":").split(":")
        dep_hour = int(dep_parts[0])
        dep_minute = int(dep_parts[1]) if len(dep_parts) > 1 else 0

        # Create departure datetime (assume today if date not provided)
        dep_datetime = now.replace(hour=dep_hour, minute=dep_minute, second=0, microsecond=0)

        # If departure time has passed today, assume it's tomorrow
        if dep_datetime < now:
            dep_datetime += timedelta(days=1)

        # Calculate difference
        diff = dep_datetime - now
        total_minutes = int(diff.total_seconds() / 60)

        if total_minutes < 0:
            result["time_remaining"] = "Flight has departed"
            result["urgency"] = "passed"
            result["advice"] = "This flight has already departed. Please check your booking for alternatives."
            return result

        hours = total_minutes // 60
        minutes = total_minutes % 60

        result["hours"] = hours
        result["minutes"] = minutes
        result["time_remaining"] = f"{hours}h {minutes}m"

        # Generate contextual advice based on time remaining
        if total_minutes <= 30:
            result["urgency"] = "urgent"
            result["advice"] = "URGENT: Boarding may have closed. Please proceed to your gate immediately!"
        elif total_minutes <= 60:
            result["urgency"] = "urgent"
            result["advice"] = "Please proceed to the boarding gate now. Boarding is likely in progress."
        elif total_minutes <= 90:
            result["urgency"] = "soon"
            result["advice"] = "Head to security screening now. Aim to be at the gate 45 minutes before departure."
        elif total_minutes <= 120:
            result["urgency"] = "soon"
            result["advice"] = "You should be at the airport now. Complete check-in and proceed to security."
        elif total_minutes <= 180:
            result["urgency"] = "normal"
            result["advice"] = "You have time. Complete check-in, then proceed to security. Browse duty-free if time permits."
        else:
            result["urgency"] = "normal"
            result["advice"] = f"You have {hours} hours until departure. Relax at the lounge or explore airport facilities."

        return result

    except Exception as e:
        result["time_remaining"] = "Could not calculate"
        result["advice"] = f"Unable to calculate time: {e}"
        return result


def get_personalized_flight_context(boarding_pass: dict, flight_status: dict = None) -> dict:
    """
    Creates a personalized context summary for the user based on their boarding pass.
    This can be stored in agent memory for personalized responses.

    Args:
        boarding_pass: Extracted boarding pass fields
        flight_status: Live flight status (optional)

    Returns:
        dict with personalized context for agent memory
    """
    context = {
        "has_boarding_pass": True,
        "flight_number": boarding_pass.get("flight_number"),
        "passenger_name": boarding_pass.get("passenger_name"),
        "airline": boarding_pass.get("airline"),
        "origin": boarding_pass.get("origin"),
        "destination": boarding_pass.get("destination"),
        "gate": boarding_pass.get("gate"),
        "seat": boarding_pass.get("seat"),
        "departure_time": boarding_pass.get("departure_time"),
        "boarding_time": boarding_pass.get("boarding_time"),
        "flight_class": boarding_pass.get("class"),
        "time_context": None,
        "live_status": None,
        "summary": ""
    }

    # Add time context if departure time is available
    if boarding_pass.get("departure_time"):
        context["time_context"] = calculate_time_to_departure(
            boarding_pass["departure_time"],
            boarding_pass.get("date")
        )

    # Add live flight status if available
    if flight_status and flight_status.get("status") != "not_found":
        context["live_status"] = {
            "status": flight_status.get("status"),
            "delay": flight_status.get("delay_minutes", 0),
            "actual_gate": flight_status.get("gate"),
            "terminal": flight_status.get("terminal")
        }

        # Override gate if live status has different gate
        if flight_status.get("gate") and flight_status.get("gate") != boarding_pass.get("gate"):
            context["gate_changed"] = True
            context["new_gate"] = flight_status.get("gate")

    # Create summary for agent
    parts = []
    if context["flight_number"]:
        parts.append(f"Flight {context['flight_number']}")
    if context["airline"]:
        parts.append(f"({context['airline']})")
    if context["destination"]:
        parts.append(f"to {context['destination']}")
    if context["gate"]:
        parts.append(f"from Gate {context['gate']}")
    if context["time_context"] and context["time_context"].get("time_remaining"):
        parts.append(f"- {context['time_context']['time_remaining']} until departure")

    context["summary"] = " ".join(parts)

    return context


@tool
def scan_boarding_pass(image_path: str) -> str:
    """
    Scans a boarding pass image and extracts flight information.

    Use this tool when the user uploads a boarding pass image and wants to:
    - Get their flight details automatically
    - Check their flight status based on boarding pass
    - Verify boarding pass information

    Args:
        image_path: Path to the boarding pass image file

    Returns:
        JSON string with extracted boarding pass fields and flight status
    """
    import os

    print(f"\n{'='*60}")
    print("BOARDING PASS SCANNER INITIATED")
    print(f"{'='*60}")
    print(f"    Image: {image_path}")

    result = {
        "status": "error",
        "boarding_pass": None,
        "flight_status": None,
        "message": None
    }

    try:
        # Validate file exists
        if not os.path.exists(image_path):
            result["message"] = f"Image not found at '{image_path}'"
            return json.dumps(result, indent=2)

        # =================================================================
        # STEP 1: OCR TEXT EXTRACTION
        # =================================================================
        print("\n--- STEP 1: OCR Text Extraction ---")
        reader = get_ocr_reader()
        ocr_results = reader.readtext(image_path)

        if not ocr_results:
            result["message"] = "No text detected in image. Please upload a clearer boarding pass photo."
            return json.dumps(result, indent=2)

        # Extract text portions
        ocr_text_list = [text[1] for text in ocr_results]
        print(f"    Extracted {len(ocr_text_list)} text segments")

        # =================================================================
        # STEP 2: FIELD EXTRACTION
        # =================================================================
        print("\n--- STEP 2: Field Extraction ---")
        boarding_pass = extract_boarding_pass_fields(ocr_text_list)
        result["boarding_pass"] = boarding_pass

        # Check if we got the critical field (flight number)
        if not boarding_pass["flight_number"]:
            result["status"] = "partial"
            result["message"] = "Could not extract flight number. Please ensure the boarding pass is clearly visible."
            return json.dumps(result, indent=2)

        # =================================================================
        # STEP 3: FLIGHT STATUS LOOKUP (Optional Integration)
        # =================================================================
        print("\n--- STEP 3: Flight Status Lookup ---")

        try:
            from flight_tools import get_flight_status_from_json

            flight_status_json = get_flight_status_from_json.invoke(boarding_pass["flight_number"])
            flight_status = json.loads(flight_status_json)

            if flight_status.get("status") != "not_found":
                result["flight_status"] = flight_status
                print(f"    Flight Status: {flight_status.get('status', 'Unknown')}")
        except Exception as e:
            print(f"    Flight status lookup skipped: {e}")
            result["flight_status"] = None

        # =================================================================
        # STEP 4: TIME CALCULATION & PERSONALIZED CONTEXT
        # =================================================================
        print("\n--- STEP 4: Time & Context Calculation ---")

        # Calculate time to departure if we have departure time
        if boarding_pass.get("departure_time"):
            time_info = calculate_time_to_departure(
                boarding_pass["departure_time"],
                boarding_pass.get("date")
            )
            result["time_to_departure"] = time_info
            print(f"    Time remaining: {time_info['time_remaining']}")
            print(f"    Urgency: {time_info['urgency']}")
            print(f"    Advice: {time_info['advice']}")
        else:
            result["time_to_departure"] = None

        # Create personalized context for agent memory
        result["personalized_context"] = get_personalized_flight_context(
            boarding_pass,
            result.get("flight_status")
        )

        # =================================================================
        # SUCCESS
        # =================================================================
        result["status"] = "success"

        # Create informative message
        msg_parts = [f"Successfully scanned boarding pass for flight {boarding_pass['flight_number']}"]
        if result.get("time_to_departure"):
            msg_parts.append(f"({result['time_to_departure']['time_remaining']} until departure)")
        if result.get("flight_status") and result["flight_status"].get("status"):
            msg_parts.append(f"- Status: {result['flight_status']['status']}")

        result["message"] = " ".join(msg_parts)

        print(f"\n{'='*60}")
        print("BOARDING PASS SCAN COMPLETE")
        print(f"{'='*60}")

        return json.dumps(result, indent=2)

    except ImportError as e:
        result["message"] = f"Required library not installed: {e}. Please install easyocr."
        return json.dumps(result, indent=2)

    except Exception as e:
        result["message"] = f"Scanning error: {str(e)}"
        print(f"\n Boarding Pass Scan Error: {e}")
        return json.dumps(result, indent=2)


def format_boarding_pass_result(scan_result: dict) -> str:
    """
    Formats the boarding pass scan result for display.

    Args:
        scan_result: The result dict from scan_boarding_pass

    Returns:
        Formatted string for display
    """
    if scan_result["status"] == "error":
        return f"**Scan Failed:** {scan_result['message']}"

    bp = scan_result.get("boarding_pass", {})
    fs = scan_result.get("flight_status")
    time_ctx = scan_result.get("time_to_departure")

    output = []
    output.append("## Boarding Pass Details\n")

    if bp.get("flight_number"):
        output.append(f"**Flight:** {bp['flight_number']}")
        if bp.get("airline"):
            output.append(f" ({bp['airline']})")
        output.append("\n")

    if bp.get("passenger_name"):
        output.append(f"**Passenger:** {bp['passenger_name']}\n")

    if bp.get("origin") and bp.get("destination"):
        output.append(f"**Route:** {bp['origin']} -> {bp['destination']}\n")

    if bp.get("date"):
        output.append(f"**Date:** {bp['date']}\n")

    if bp.get("seat"):
        output.append(f"**Seat:** {bp['seat']}\n")

    if bp.get("gate"):
        output.append(f"**Gate:** {bp['gate']}\n")

    if bp.get("boarding_time"):
        output.append(f"**Boarding Time:** {bp['boarding_time']}\n")

    if bp.get("departure_time"):
        output.append(f"**Departure Time:** {bp['departure_time']}\n")

    if bp.get("class"):
        output.append(f"**Class:** {bp['class']}\n")

    output.append(f"\n*Scan Confidence: {bp.get('confidence', 0)}%*\n")

    # Add time context if available
    if time_ctx and time_ctx.get("time_remaining"):
        output.append("\n---\n## Time to Departure\n")
        output.append(f"**Time Remaining:** {time_ctx['time_remaining']}\n")

        # Add urgency indicator
        urgency = time_ctx.get("urgency", "normal")
        if urgency == "urgent":
            output.append("**Status:** URGENT - Act now!\n")
        elif urgency == "soon":
            output.append("**Status:** Boarding Soon\n")
        else:
            output.append("**Status:** On Schedule\n")

        if time_ctx.get("advice"):
            output.append(f"\n**Advice:** {time_ctx['advice']}\n")

    # Add live flight status if available
    if fs and fs.get("status") != "not_found":
        output.append("\n---\n## Live Flight Status\n")
        output.append(f"**Status:** {fs.get('status', 'Unknown')}\n")
        if fs.get("scheduled_arrival"):
            output.append(f"**Scheduled Arrival:** {fs['scheduled_arrival']}\n")
        if fs.get("terminal"):
            output.append(f"**Terminal:** {fs['terminal']}\n")
        if fs.get("gate"):
            output.append(f"**Gate (Live):** {fs['gate']}\n")

            # Check if gate changed from boarding pass
            if bp.get("gate") and fs.get("gate") != bp.get("gate"):
                output.append(f"\n**NOTICE:** Gate has changed from {bp['gate']} to {fs['gate']}!\n")

    return "".join(output)


# =============================================================================
# TEST FUNCTION
# =============================================================================

if __name__ == "__main__":
    # Test with a sample image
    import sys

    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        result = scan_boarding_pass.invoke(test_image)
        print("\n" + "="*60)
        print("RESULT:")
        print("="*60)
        print(result)
    else:
        print("Usage: python boarding_pass_tools.py <image_path>")
