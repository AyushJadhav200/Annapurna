"""
Location utilities for Annapurna
- Delivery zone checking
- Distance calculation  
- Geofencing
"""
import math
from typing import Tuple, Optional

# Kitchen Location (Pune - Update this to your actual kitchen location)
KITCHEN_LAT = 18.5204
KITCHEN_LNG = 73.8567

# Delivery radius in kilometers
MAX_DELIVERY_RADIUS_KM = 10

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in kilometers
    r = 6371
    
    return c * r

def is_in_delivery_zone(lat: float, lng: float) -> Tuple[bool, float]:
    """
    Check if given coordinates are within delivery zone.
    Returns (is_deliverable, distance_km)
    """
    distance = haversine_distance(KITCHEN_LAT, KITCHEN_LNG, lat, lng)
    is_deliverable = distance <= MAX_DELIVERY_RADIUS_KM
    return is_deliverable, round(distance, 2)

def get_distance_from_kitchen(lat: float, lng: float) -> float:
    """Get distance from kitchen in kilometers"""
    return round(haversine_distance(KITCHEN_LAT, KITCHEN_LNG, lat, lng), 2)

def estimate_delivery_time(distance_km: float) -> int:
    """
    Estimate delivery time in minutes based on distance.
    Assumes average speed of 20 km/h in city traffic + 15 min prep time.
    """
    travel_time = (distance_km / 20) * 60  # Convert to minutes
    prep_time = 15  # Kitchen prep time
    buffer = 5  # Buffer for parking, finding address, etc.
    
    return int(travel_time + prep_time + buffer)

def get_kitchen_location() -> dict:
    """Return kitchen coordinates for map display"""
    return {
        "lat": KITCHEN_LAT,
        "lng": KITCHEN_LNG,
        "name": "Annapurna Kitchen",
        "address": "Shivaji Nagar, Pune"
    }
