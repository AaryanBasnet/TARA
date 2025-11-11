import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# --- IMPORTANT ---
# This is a new library you must install:
# pip install amadeus
# -----------------
from amadeus import Client, ResponseError

load_dotenv()

def get_cheapest_flights(origin_iata: str, destination_iata: str, departure_date: str) -> str:
    """
    Fetches the cheapest flight offers from Amadeus.
    """
    
    # 1. Get Amadeus API keys from your .env file
    # You get these from the Amadeus developer portal
    CLIENT_ID = os.environ.get("AMADEUS_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("AMADEUS_CLIENT_SECRET")

    if not CLIENT_ID or not CLIENT_SECRET:
        return json.dumps({"error": "AMADEUS_CLIENT_ID or CLIENT_SECRET not set."})

    try:
        # 2. Initialize the Amadeus client
        amadeus = Client(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

        # 3. Make the API call to search for flight offers
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin_iata,
            destinationLocationCode=destination_iata,
            departureDate=departure_date,
            adults=1,
            currencyCode="NPR"  # Change to your preferred currency
        )

        # 4. Check if any data was returned
        if not response.data:
            return json.dumps({"error": "No flight offers found for this route and date."})

        # 5. Process the data to find the cheapest
        cheapest_flights = []
        for offer in response.data:
            simplified_offer = {
                "airline": offer["itineraries"][0]["segments"][0].get("carrierCode", "N/A"),
                "price": {
                    "total": offer["price"].get("total"),
                    "currency": offer["price"].get("currency")
                },
                "number_of_stops": len(offer["itineraries"][0]["segments"]) - 1
            }
            cheapest_flights.append(simplified_offer)
        
        # Sort by total price
        cheapest_flights.sort(key=lambda x: float(x["price"]["total"]))
        
        # Return the top 3 cheapest flights
        return json.dumps(cheapest_flights[:3], indent=2)

    except ResponseError as e:
        return json.dumps({"error": f"Amadeus API error: {e}"})
    except Exception as e:
        return json.dumps({"error": f"An error occurred: {e}"})

# --- To test the function directly ---
if __name__ == "__main__":
    
    # --- Parameters for your search ---
    origin = "DOH"        # Doha
    destination = "KTM"   # Kathmandu
    
    # Get tomorrow's date in YYYY-MM-DD format
    # (Searching for "today" often fails, so "tomorrow" is better for testing)
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"--- Searching for cheapest flights from {origin} to {destination} for {tomorrow} ---")
    
    flights_json = get_cheapest_flights(origin, destination, tomorrow)

    print("\n--- Cheapest Flight Offers ---")
    print(flights_json)