# flight_tools.py

import os
import json  # <-- Import the JSON library
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

# Load environment variables
load_dotenv()

@tool
def get_flight_status_from_json(flight_iata: str) -> str:
    """
    (Reliable Mock API) Fetches flight status from a local 'tia_flights.json' file.
    Use this tool when a user asks for the status, gate, or schedule
    of a specific flight IATA number (e.g., "RA205", "U4954").
    """
    
    # --- DEBUGGING PRINT ---
    print(f"\n--- ✈️ Calling Mock Flight Tool for: {flight_iata} ---\n")
    # ---------------------
    
    try:
        with open('tia_flights.json', 'r') as f:
            data = json.load(f)
        
        flight_iata_clean = flight_iata.strip().upper()
        
        for flight in data['flights']:
            if flight['flight_iata'].upper() == flight_iata_clean:
                # Found the flight!
                result = f"""
✈️ **Flight {flight['flight_iata']}** (Mock Data)
- **Airline:** {flight['airline']}
- **From/To:** {flight['from_to']}
- **Status:** {flight['status']}
- **Gate:** {flight['gate']}
                """
                return result.strip()
        
        # If the loop finishes
        return f"❌ No flight information found for {flight_iata_clean} in the local database."

    except FileNotFoundError:
        return "❌ Critical Error: 'tia_flights.json' file is missing."
    except Exception as e:
        return f"❌ An unexpected error occurred reading the flight file: {e}"


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
    
    url = "https://api.open-meteo.com/v1/forecast?latitude=27.71&longitude=85.32&current_weather=true"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        current = data.get('current_weather', {})
        temp = current.get('temperature', 'N/A')
        wind_speed = current.get('windspeed', 'N/A')

        result = f"""
☀️ **Current Weather at Kathmandu (KTM)**
**Temperature:** {temp}°C
**Wind Speed:** {wind_speed} km/h
        """
        return result.strip()

    except requests.exceptions.RequestException as e:
        return f"❌ Error connecting to the weather service: {e}"
    except Exception as e:
        return f"❌ An unexpected error occurred fetching weather: {e}"