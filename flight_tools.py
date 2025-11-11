# import requests
# import os
# import json
# from dotenv import load_dotenv

# load_dotenv()

# def get_flight_status(flight_iata: str) -> str:
#     """
#     Fetches live flight status from Aviationstack for a given IATA flight number.
#     Returns a JSON string with simplified flight details or an error.
#     """
    
#     # 1. Get the API Key securely from environment variables
#     API_KEY = os.environ.get("AVIATIONSTACK_API_KEY")
#     if not API_KEY:
#         print("Error: AVIATIONSTACK_API_KEY environment variable not set.")
#         return json.dumps({"error": "API key for Aviationstack is not set."})

#     BASE_URL = "http://api.aviationstack.com/v1/flights"
    
#     # 2. Set up the parameters for the API request
#     params = {
#         "access_key": API_KEY,
#         "flight_iata": flight_iata,
#         "limit": 1  # We only want the most relevant flight
#     }

#     try:
#         # 3. Make the API call
#         response = requests.get(BASE_URL, params=params)
#         response.raise_for_status()  # Raise an exception for bad status codes (4xx, 5xx)
        
#         data = response.json()

#         # 4. Check if the API returned any data
#         if not data.get("data") or len(data["data"]) == 0:
#             return json.dumps({"error": f"No flight information found for {flight_iata}."})

#         # 5. Process the data and build the simple response
#         flight_info = data["data"][0]
#         departure = flight_info.get("departure", {})
#         arrival = flight_info.get("arrival", {})
        
#         simplified_data = {
#             "flight_number": flight_iata,
#             "airline": flight_info.get("airline", {}).get("name", "N/A"),
#             "flight_status": flight_info.get("flight_status", "N/A"),
#             "departure_delay": departure.get("delay", 0), # Delay in minutes
#             "departure": {
#                 "airport": departure.get("airport", "N/A"),
#                 "gate": departure.get("gate", "N/A"),
#                 "scheduled": departure.get("scheduled", "N/A"),
#                 "estimated": departure.get("estimated", "N/A")
#             },
#             "arrival": {
#                 "airport": arrival.get("airport", "N/A"),
#                 "gate": arrival.get("gate", "N/A"),
#                 "scheduled": arrival.get("scheduled", "N/A"),
#                 "estimated": arrival.get("estimated", "N/A")
#             }
#         }
        
#         # 6. Return the simplified data as a JSON STRING
#         return json.dumps(simplified_data)

#     except requests.exceptions.HTTPError as http_err:
#         return json.dumps({"error": f"HTTP error occurred: {http_err}"})
#     except requests.exceptions.RequestException as e:
#         return json.dumps({"error": f"An error occurred connecting to the API: {e}"})
    

# # --- To test the function directly ---
# if __name__ == "__main__":
#     # Use a real flight number for testing. 
#     # You may need to find a valid one on a flight tracker.
#     test_flight = "H9363"  # Air India (KTM-DEL)

#     print(f"--- Testing function for {test_flight} ---")
#     flight_data_json = get_flight_status(test_flight)

#     print("\n--- Raw JSON String Output ---")
#     print(flight_data_json)

#     # Pretty-print the JSON for easier reading
#     try:
#         parsed_data = json.loads(flight_data_json)
#         print("\n--- Parsed Data (Pretty) ---")
#         print(json.dumps(parsed_data, indent=2))
#     except json.JSONDecodeError:
#         print(f"\nCould not parse response: {flight_data_json}")    

import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone  # CHANGED: Added datetime import

load_dotenv()

def get_flight_status(flight_iata: str) -> str:
    """
    Fetches live flight status from AeroDataBox (RapidAPI) for a given IATA flight number.
    Returns a JSON string with simplified flight details or an error.
    """
    
    # 1. Get the API Key securely from environment variables
    API_KEY = os.environ.get("RAPIDAPI_KEY")
    if not API_KEY:
        print("Error: RAPIDAPI_KEY environment variable not set.")
        return json.dumps({"error": "API key for RapidAPI is not set."})

    # CHANGED: Get today's date in YYYY-MM-DD format (UTC is safest for flights)
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 2. Set up the URL and Headers for the RapidAPI request
    # CHANGED: Switched to the more specific endpoint that requires a date
    # This endpoint is /flights/number/{flight_number}/{date}
    BASE_URL = f"https://aerodatabox.p.rapidapi.com/flights/number/{flight_iata}/{today_date}"
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "aerodatabox.p.rapidapi.com"
    }

    try:
        # 3. Make the API call
        response = requests.get(BASE_URL, headers=headers)
        response.raise_for_status()
        
        data = response.json()

        # 4. Check for API errors
        # This endpoint returns a LIST of flights, even if it's just one.
        # We must check if the list is empty.
        if not data or len(data) == 0:
            return json.dumps({"error": f"No flight information found for {flight_iata} on {today_date}."})

        # 5. Process the data and build the simple response
        # CHANGED: Get the first flight from the returned list
        flight_info = data[0] 
        departure = flight_info.get("departure", {})
        arrival = flight_info.get("arrival", {})
        
        simplified_data = {
            "flight_number": flight_info.get("number", flight_iata), # Use the number from the response
            "airline": flight_info.get("airline", {}).get("name", "N/A"),
            "flight_status": flight_info.get("status", "N/A"),
            "departure_delay": departure.get("delayMinutes", 0),
            "departure": {
                "airport": departure.get("airport", {}).get("name", "N/A"),
                "gate": departure.get("gate", "N/A"),
                "scheduled": departure.get("scheduledTimeUtc", "N/A"),
                "estimated": departure.get("actualTimeUtc") or departure.get("estimatedTimeUtc") or "N/A"
            },
            "arrival": {
                "airport": arrival.get("airport", {}).get("name", "N/A"),
                "gate": arrival.get("gate", "N/S"),
                "scheduled": arrival.get("scheduledTimeUtc", "N/A"),
                "estimated": arrival.get("actualTimeUtc") or arrival.get("estimatedTimeUtc") or "N/A"
            }
        }
        
        # 6. Return the simplified data as a JSON STRING
        return json.dumps(simplified_data)

    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
            return json.dumps({"error": f"No flight information found for {flight_iata} on {today_date}."})
        # Handle 400s from this new endpoint
        if http_err.response.status_code == 400:
             return json.dumps({"error": f"API reported a bad request. Check flight number format or date: {http_err}"})
        return json.dumps({"error": f"HTTP error occurred: {http_err}"})
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"An error occurred connecting to the API: {e}"})
    

# --- To test the function directly ---
if __name__ == "__main__":
    # Make sure your .env file has 'RAPIDAPI_KEY=...'
    
    # H9363 is Himalaya Airlines (KTM-DOH)
    test_flight = "TG309"  

    print(f"--- Testing function for {test_flight} ---")
    flight_data_json = get_flight_status(test_flight)

    print("\n--- Raw JSON String Output ---")
    print(flight_data_json)

    # Pretty-print the JSON for easier reading
    try:
        parsed_data = json.loads(flight_data_json)
        print("\n--- Parsed Data (Pretty) ---")
        print(json.dumps(parsed_data, indent=2))
    except json.JSONDecodeError:
        print(f"\nCould not parse response: {flight_data_json}")