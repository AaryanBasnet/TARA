# flight_tools.py
import os
import json  # <-- Import the JSON library
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

# Load environment variables
load_dotenv()

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FLIGHT_CACHE_FILE = os.path.join(SCRIPT_DIR, "flight_cache.json")

# --- Mock Flight Database (Fallback) ---
MOCK_FLIGHT_DATABASE = [
    {
        "flight": "RA205",
        "airline": "Nepal Airlines",
        "route": "Delhi",
        "time": "10:30",
        "status": "On Time",
        "type": "Arrival",
        "gate": "A2"
    },
    {
        "flight": "FZ575",
        "airline": "FlyDubai",
        "route": "Dubai",
        "time": "14:00",
        "status": "On Time",
        "type": "Arrival",
        "gate": "B5"
    },
    {
        "flight": "QR648",
        "airline": "Qatar Airways",
        "route": "Doha",
        "time": "02:45",
        "status": "Delayed",
        "type": "Arrival",
        "gate": "C1"
    },
    {
        "flight": "SQ700",
        "airline": "Singapore Airlines",
        "route": "Singapore",
        "time": "08:00",
        "status": "On Time",
        "type": "Arrival",
        "gate": "A4"
    },
    {
        "flight": "TG319",
        "airline": "Thai Airways",
        "route": "Bangkok",
        "time": "11:45",
        "status": "On Time",
        "type": "Arrival",
        "gate": "B2"
    },
    {
        "flight": "EK2054",
        "airline": "Emirates",
        "route": "Dubai",
        "time": "22:30",
        "status": "Boarding",
        "type": "Arrival",
        "gate": "C3"
    },
    {
        "flight": "AI216",
        "airline": "Air India",
        "route": "Mumbai",
        "time": "16:00",
        "status": "On Time",
        "type": "Arrival",
        "gate": "A1"
    },
    {
        "flight": "U4954",
        "airline": "Buddha Air",
        "route": "Pokhara",
        "time": "07:00",
        "status": "Departed",
        "type": "Departure",
        "gate": "D1"
    }
]


# =============================================================================
# HELPER FUNCTION: Load Flight Data from Cache or Fallback
# =============================================================================

def load_flight_data() -> tuple[list, str]:
    """
    Loads flight data from flight_cache.json or falls back to mock data.
    
    Returns:
        tuple: (list of flights, data source label)
    """
    try:
        if os.path.exists(FLIGHT_CACHE_FILE):
            with open(FLIGHT_CACHE_FILE, 'r') as f:
                data = json.load(f)
            
            flights = data.get('flights', [])
            source = data.get('source', 'flight_cache.json')
            last_updated = data.get('last_updated', 'Unknown')
            
            if flights:
                print(f"--- ✅ Using Real Data Source: {source} ---")
                print(f"    Last Updated: {last_updated}")
                print(f"    Total Flights: {len(flights)}")
                return flights, f"Real-Time ({source})"
        
        # Cache file exists but is empty or malformed
        print("--- ⚠️ Cache file empty, using Mock Database ---")
        return MOCK_FLIGHT_DATABASE, "Mock Database (Fallback)"
        
    except json.JSONDecodeError as e:
        print(f"--- ⚠️ Cache JSON Error: {e}, using Mock Database ---")
        return MOCK_FLIGHT_DATABASE, "Mock Database (JSON Error)"
    except Exception as e:
        print(f"--- ⚠️ Cache Load Error: {e}, using Mock Database ---")
        return MOCK_FLIGHT_DATABASE, "Mock Database (Error)"


@tool
def get_flight_status_from_json(flight_iata: str) -> str:
    """
    Fetches flight status from flight_cache.json (real-time data) or fallback mock data.
    Use this tool when a user asks for the status, gate, or schedule
    of a specific flight IATA number (e.g., "RA205", "U4954", "SH124").
    """
    print(f"\n--- ✈️ Searching for Flight: {flight_iata} ---\n")
    
    # Load flight data (real or fallback)
    flights, data_source = load_flight_data()
    
    flight_iata_clean = flight_iata.strip().upper()
    
    # Search for the flight
    for flight in flights:
        # Handle both old format (flight_iata) and new format (flight)
        flight_num = flight.get('flight', flight.get('flight_iata', '')).upper()
        
        if flight_num == flight_iata_clean:
            # Found the flight!
            airline = flight.get('airline', 'Unknown Airline')
            route = flight.get('route', flight.get('from_to', 'Unknown'))
            status = flight.get('status', 'Unknown')
            flight_type = flight.get('type', 'Unknown')
            time_str = flight.get('time', 'Unknown')
            gate = flight.get('gate', 'TBA')
            
            # Format time display based on flight type
            if flight_type == "Arrival":
                time_label = "Arrival Time"
            else:
                time_label = "Departure Time"
            
            result = f"""
✈️ **Flight {flight_num}** ({data_source})
- **Airline:** {airline if airline else 'Unknown'}
- **Route:** {route}
- **{time_label}:** {time_str}
- **Status:** {status}
- **Type:** {flight_type}
- **Gate:** {gate}
"""
            return result.strip()
    
    # Flight not found
    return f"❌ No flight information found for **{flight_iata_clean}** in the database.\n\n*Searched {len(flights)} flights from {data_source}*"


@tool
def search_flights_by_route(origin: str, destination: str = "Kathmandu") -> str:
    """
    Searches for flights based on origin and destination cities.
    
    Use this tool when the user asks about flights from a specific city
    WITHOUT providing a flight number (e.g., "flights from Dubai", 
    "what planes are coming from Singapore", "flights to Kathmandu from Bangkok").
    
    DO NOT use this tool if the user provides a specific flight number like "RA205".
    For specific flight numbers, use get_flight_status_from_json instead.
    
    Args:
        origin: The departure city (e.g., "Dubai", "Singapore", "Delhi")
        destination: The arrival city (default: "Kathmandu")
    
    Returns:
        A formatted list of matching flights or a message if none found.
    """
    print(f"\n--- 🔍 Searching flights: {origin} → {destination} ---\n")
    
    # Load flight data (real or fallback)
    flights, data_source = load_flight_data()
    
    # Normalize inputs
    origin_clean = origin.strip().lower()
    destination_clean = destination.strip().lower()
    
    # Common city name variations
    city_aliases = {
        "delhi": ["delhi", "indira gandhi", "del"],
        "dubai": ["dubai", "dxb"],
        "doha": ["doha", "hamad", "doh"],
        "singapore": ["singapore", "changi", "sin"],
        "bangkok": ["bangkok", "suvarnabhumi", "don muang", "bkk", "dmk"],
        "mumbai": ["mumbai", "chhatrapati", "bom"],
        "kuala lumpur": ["kuala lumpur", "klia", "kul"],
        "hong kong": ["hong kong", "hkg"],
        "sharjah": ["sharjah", "shj"],
        "abu dhabi": ["abu dhabi", "auh"],
        "dammam": ["dammam", "king fahd", "dmm"],
        "kuwait": ["kuwait", "kwi"],
        "pokhara": ["pokhara", "pkr"],
        "biratnagar": ["biratnagar", "bir"],
        "nepalganj": ["nepalganj", "kep"],
        "guangzhou": ["guangzhou", "baiyun", "can"],
        "chengdu": ["chengdu", "tianfu", "ctu"],
        "istanbul": ["istanbul", "ist"],
    }
    
    # Get all aliases for the origin city
    origin_aliases = city_aliases.get(origin_clean, [origin_clean])
    
    # Search for matching flights
    matching_flights = []
    for flight in flights:
        route = flight.get('route', flight.get('from_to', '')).lower()
        flight_type = flight.get('type', '').lower()
        
        # For arrivals to Kathmandu, the route field contains the origin
        # For departures from Kathmandu, the route field contains the destination
        
        # Check if any alias matches the route
        route_matches = any(alias in route for alias in origin_aliases)
        
        if route_matches:
            # If searching for arrivals to Kathmandu
            if destination_clean == "kathmandu" and flight_type == "arrival":
                matching_flights.append(flight)
            # If searching for departures from Kathmandu
            elif destination_clean != "kathmandu" and flight_type == "departure":
                # Check if destination is in route
                dest_aliases = city_aliases.get(destination_clean, [destination_clean])
                if any(alias in route for alias in dest_aliases):
                    matching_flights.append(flight)
            # General match (include both arrivals and departures)
            elif destination_clean == "kathmandu":
                matching_flights.append(flight)
    
    if not matching_flights:
        return f"❌ No flights found from **{origin.title()}** to **{destination.title()}** in our database.\n\n*Searched {len(flights)} flights from {data_source}*"
    
    # Sort by time
    matching_flights.sort(key=lambda x: x.get('time', '99:99'))
    
    # Format the results
    result_lines = [f"✈️ **Flights from {origin.title()} to {destination.title()}:**\n"]
    result_lines.append(f"*Data Source: {data_source}*\n")
    
    # Limit to 10 flights to avoid overwhelming response
    display_flights = matching_flights[:10]
    
    for flight in display_flights:
        flight_num = flight.get('flight', flight.get('flight_iata', 'Unknown'))
        airline = flight.get('airline', 'Unknown')
        route = flight.get('route', flight.get('from_to', 'Unknown'))
        time_str = flight.get('time', 'Unknown')
        status = flight.get('status', 'Unknown')
        flight_type = flight.get('type', 'Unknown')
        gate = flight.get('gate', 'TBA')
        
        # Status emoji
        status_emoji = "✅" if status in ["On Time", "Scheduled", "Landed"] else "⏳" if status == "En Route" else "⚠️"
        
        result_lines.append(f"""
**{flight_num}** - {airline if airline else 'Unknown Airline'}
- 🛫 Time: {time_str}
- 📍 Route: {route}
- {status_emoji} Status: {status}
- 🚪 Type: {flight_type}
---""")
    
    # Summary
    if len(matching_flights) > 10:
        result_lines.append(f"\n*Showing 10 of {len(matching_flights)} flights. Ask about a specific flight number for more details.*")
    else:
        result_lines.append(f"\n*Found {len(matching_flights)} flight(s). Ask about a specific flight number for more details.*")
    
    return "\n".join(result_lines)


@tool
def get_kathmandu_weather_openmeteo() -> str:
    """
    Fetches the current weather for Kathmandu, Nepal from Open-Meteo.
    This tool requires NO API KEY. Use this tool *only* when the user
    asks for the current weather, temperature, or forecast at KTM or Kathmandu.
    """
    # --- DEBUGGING PRINT ---
    print(f"\n--- ☀️ Calling Open-Meteo Weather Tool for: KTM ---\n")
    # ---------------------
    
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 27.7172,
            "longitude": 85.3240,
            "current_weather": True,
            "timezone": "Asia/Kathmandu"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current_weather", {})
        temp = current.get("temperature", "N/A")
        windspeed = current.get("windspeed", "N/A")
        weathercode = current.get("weathercode", 0)
        
        # Simple weather code interpretation
        weather_descriptions = {
            0: "Clear sky ☀️",
            1: "Mainly clear 🌤️",
            2: "Partly cloudy ⛅",
            3: "Overcast ☁️",
            45: "Foggy 🌫️",
            48: "Depositing rime fog 🌫️",
            51: "Light drizzle 🌧️",
            53: "Moderate drizzle 🌧️",
            55: "Dense drizzle 🌧️",
            61: "Slight rain 🌧️",
            63: "Moderate rain 🌧️",
            65: "Heavy rain 🌧️",
            80: "Slight rain showers 🌦️",
            81: "Moderate rain showers 🌦️",
            82: "Violent rain showers ⛈️",
            95: "Thunderstorm ⛈️",
        }
        
        weather_desc = weather_descriptions.get(weathercode, "Unknown")
        
        result = f"""
☀️ **Current Weather in Kathmandu (TIA)**

- **Temperature:** {temp}°C
- **Conditions:** {weather_desc}
- **Wind Speed:** {windspeed} km/h

*Data from Open-Meteo API*
"""
        return result.strip()
        
    except requests.exceptions.RequestException as e:
        return f"❌ Error fetching weather data: {e}"
    except Exception as e:
        return f"❌ Unexpected error: {e}"