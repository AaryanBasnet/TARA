import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
# 1. Get API Key from .env (Best Practice)
API_KEY = os.getenv("AVIATIONSTACK_API_KEY") 
BASE_URL = "http://api.aviationstack.com/v1/flights"
CACHE_FILE = "flight_cache.json"
AIRPORT_IATA = "KTM"

def fetch_flights_from_api(direction="arrival"):
    """
    Fetches flights based on direction ('arrival' or 'departure').
    """
    if not API_KEY:
        print("❌ Error: AVIATIONSTACK_API_KEY not found in environment variables.")
        return []

    print(f"... Fetching {direction.title()}s for {AIRPORT_IATA}...")
    
    params = {
        'access_key': API_KEY,
        'limit': 40  # Grab 40 flights (Free tier allows 100/month, use carefully!)
    }
    
    # Toggle parameter based on direction
    if direction == "arrival":
        params['arr_iata'] = AIRPORT_IATA
    else:
        params['dep_iata'] = AIRPORT_IATA

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        data = response.json()
        
        if "error" in data:
            print(f"❌ API Error ({direction}): {data['error']['info']}")
            return []
            
        raw_flights = data.get('data', [])
        print(f"    -> Retrieved {len(raw_flights)} raw {direction}s")
        return raw_flights

    except Exception as e:
        print(f"❌ Connection Error ({direction}): {e}")
        return []

def normalize_flight_data(raw_flight, direction):
    """
    Converts complex API JSON into our simple Chatbot format.
    """
    try:
        # 1. Basic Info
        f_num = raw_flight['flight']['iata']
        airline = raw_flight['airline']['name']
        status_raw = raw_flight['flight_status']
        
        # 2. Route Logic (If Arrival, route is Origin. If Departure, route is Dest)
        if direction == "arrival":
            route = raw_flight['departure']['airport']
            time_point = raw_flight['arrival']['scheduled']
        else:
            route = raw_flight['arrival']['airport']
            time_point = raw_flight['departure']['scheduled']

        # 3. Time Formatting (Handle ISO string)
        # Ex: "2024-11-27T14:30:00+00:00" -> "14:30"
        try:
            dt_obj = datetime.fromisoformat(time_point.replace('Z', '+00:00'))
            time_clean = dt_obj.strftime("%H:%M")
        except:
            time_clean = time_point

        # 4. Status Normalization
        status = "Scheduled"
        s_lower = status_raw.lower()
        if "landed" in s_lower: status = "Landed"
        elif "active" in s_lower: status = "En Route"
        elif "cancelled" in s_lower: status = "Cancelled"
        elif "incident" in s_lower: status = "Delayed"
        elif "diverted" in s_lower: status = "Diverted"

        return {
            "flight": f_num,
            "airline": airline,
            "route": route, # "Delhi", "Dubai"
            "time": time_clean,
            "status": status,
            "type": direction.title(), # "Arrival" or "Departure"
            "raw_status": status_raw
        }
    except Exception:
        return None # Skip broken records

def get_static_fallback_data():
    """Safety Net: Uses this if API fails completely."""
    return [
        {"flight": "RA206", "airline": "Nepal Airlines", "route": "Delhi", "time": "10:15", "status": "Landed", "type": "Arrival"},
        {"flight": "FZ575", "airline": "FlyDubai", "route": "Dubai", "time": "14:20", "status": "Landed", "type": "Arrival"},
        {"flight": "QR648", "airline": "Qatar Airways", "route": "Doha", "time": "16:45", "status": "Scheduled", "type": "Arrival"},
        {"flight": "RA417", "airline": "Nepal Airlines", "route": "Kuala Lumpur", "time": "23:30", "status": "Scheduled", "type": "Departure"}
    ]

def update_cache():
    print(f"--- 📡 Data Engine Started at {datetime.now().strftime('%H:%M:%S')} ---")
    
    # 1. Fetch Arrivals
    arrivals_raw = fetch_flights_from_api("arrival")
    arrivals_clean = [normalize_flight_data(f, "arrival") for f in arrivals_raw if normalize_flight_data(f, "arrival")]
    
    # 2. Fetch Departures
    departures_raw = fetch_flights_from_api("departure")
    departures_clean = [normalize_flight_data(f, "departure") for f in departures_raw if normalize_flight_data(f, "departure")]
    
    # 3. Combine
    all_flights = arrivals_clean + departures_clean
    
    # 4. Fallback Check
    source_label = "AviationStack API (Real-Time)"
    if not all_flights:
        print("⚠️ API yielded no data. Using Fallback Snapshot.")
        all_flights = get_static_fallback_data()
        source_label = "Cached Snapshot (Offline Mode)"

    # 5. Save to Disk
    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source_label,
        "total_flights": len(all_flights),
        "flights": all_flights
    }
    
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"💾 Cache updated in {CACHE_FILE} with {len(all_flights)} flights.")

if __name__ == "__main__":
    update_cache()