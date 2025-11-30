import os
import math
import requests
import googlemaps
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Location Service", version="1.0")

# Configuration
MAPS_API_KEY = os.environ.get("MAPS_API_KEY")
if not MAPS_API_KEY:
    print("Warning: MAPS_API_KEY environment variable not set.")

# Initialize Google Maps Client
try:
    gmaps = googlemaps.Client(key=MAPS_API_KEY) if MAPS_API_KEY else None
except Exception as e:
    print(f"Error initializing Google Maps client: {e}")
    gmaps = None

# Street View Collection Parameters
STREETVIEW_CONFIG = {
    "vantage_offset_meters": 30,      # Distance for offset vantage points
    "headings": [0, 90, 180, 270],    # Cardinal directions
    "pitches": [0, -10],              # Level and slight downward angle
    "fovs": [90, 50],                 # Wide and medium zoom
    "image_size": "640x480",          # Image dimensions
    "max_images_per_location": 40,    # Cap to control API costs
    "use_smart_heading": True,        # Point camera towards building center
}

class LocationRequest(BaseModel):
    query: str

class StreetViewImage(BaseModel):
    vantage_point: str
    view_direction: str
    heading: int
    heading_offset: int
    pitch: int
    pitch_desc: str
    fov: int
    fov_desc: str
    pano_id: str
    pano_date: str
    lat: float
    lng: float
    url: str
    description: str

class LocationResponse(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    total_images: int
    unique_panoramas: int
    street_view_images: List[StreetViewImage]
    image_urls: List[str]
    error: Optional[str] = None

def calculate_heading_to_target(from_lat, from_lng, to_lat, to_lng):
    """
    Calculate the heading (compass direction) from one point to another.
    Returns heading in degrees (0-360, where 0=North, 90=East, etc.)
    """
    lat1 = math.radians(from_lat)
    lat2 = math.radians(to_lat)
    diff_lng = math.radians(to_lng - from_lng)
    
    x = math.sin(diff_lng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(diff_lng)
    
    heading = math.degrees(math.atan2(x, y))
    return (heading + 360) % 360  # Normalize to 0-360

@app.post("/find_location", response_model=LocationResponse)
def find_location(request: LocationRequest):
    """
    Finds a location and gathers comprehensive outdoor Street View imagery.
    """
    query = request.query
    print(f"Searching for: {query}")
    
    if not gmaps:
        raise HTTPException(status_code=500, detail="Google Maps client not initialized (missing API key)")

    try:
        lat, lng, formatted_address = None, None, None
        place_name = None
        
        # --- Step 1: Try Places API first ---
        try:
            places_result = gmaps.places(query=query)
            
            if places_result.get('results') and len(places_result['results']) > 0:
                place = places_result['results'][0]
                location = place['geometry']['location']
                lat, lng = location['lat'], location['lng']
                formatted_address = place.get('formatted_address', '')
                place_name = place.get('name', query)
                
                # Verify it's a specific place
                place_types = place.get('types', [])
                is_specific = not any(t in place_types for t in ['locality', 'political', 'administrative_area_level_1', 'country'])
                
                if not is_specific:
                    lat, lng, formatted_address = None, None, None
        except Exception as e:
            print(f"Places API error: {e}")
        
        # Fallback to Geocoding API
        if lat is None:
            geocode_result = gmaps.geocode(query)
            
            if not geocode_result:
                raise HTTPException(status_code=404, detail=f"Location not found: {query}")
            
            location = geocode_result[0]['geometry']['location']
            lat, lng = location['lat'], location['lng']
            formatted_address = geocode_result[0]['formatted_address']
            place_name = query # Use query as name if geocoding used
            
        # --- Step 2: Generate vantage points ---
        offset = STREETVIEW_CONFIG['vantage_offset_meters'] / 111000  # meters to degrees
        
        vantage_points = [
            {"name": "Front-N", "lat": lat + offset, "lng": lng},
            {"name": "Front-S", "lat": lat - offset, "lng": lng},
            {"name": "Side-E", "lat": lat, "lng": lng + offset * 1.2},
            {"name": "Side-W", "lat": lat, "lng": lng - offset * 1.2},
            {"name": "Corner-NE", "lat": lat + offset*0.7, "lng": lng + offset*0.7},
            {"name": "Corner-SW", "lat": lat - offset*0.7, "lng": lng - offset*0.7},
        ]
        
        target_lat, target_lng = lat, lng
        
        # --- Step 3: Gather images ---
        street_view_images = []
        seen_pano_ids = set()
        
        for vp in vantage_points:
            metadata_url = (
                f"https://maps.googleapis.com/maps/api/streetview/metadata?"
                f"location={vp['lat']},{vp['lng']}&source=outdoor&key={MAPS_API_KEY}"
            )
            
            try:
                meta_response = requests.get(metadata_url, timeout=5)
                meta_data = meta_response.json()
                
                if meta_data.get('status') != 'OK':
                    continue
                
                pano_id = meta_data.get('pano_id', '')
                pano_date = meta_data.get('date', 'Unknown')
                pano_lat = meta_data.get('location', {}).get('lat', vp['lat'])
                pano_lng = meta_data.get('location', {}).get('lng', vp['lng'])
                
                if pano_id in seen_pano_ids:
                    continue
                seen_pano_ids.add(pano_id)
                
                smart_heading = calculate_heading_to_target(pano_lat, pano_lng, target_lat, target_lng)
                
                heading_offsets = [0, -30, 30]
                
                for h_offset in heading_offsets:
                    for pitch in STREETVIEW_CONFIG['pitches']:
                        for fov in STREETVIEW_CONFIG['fovs']:
                            if len(street_view_images) >= STREETVIEW_CONFIG['max_images_per_location']:
                                break
                            
                            actual_heading = (smart_heading + h_offset) % 360
                            
                            if h_offset == 0: view_desc = "direct"
                            elif h_offset < 0: view_desc = "left"
                            else: view_desc = "right"
                            
                            pitch_desc = "level" if pitch == 0 else "down"
                            fov_desc = "wide" if fov >= 70 else "zoom"
                            
                            image_url = (
                                f"https://maps.googleapis.com/maps/api/streetview?"
                                f"size={STREETVIEW_CONFIG['image_size']}"
                                f"&location={pano_lat},{pano_lng}"
                                f"&heading={actual_heading:.0f}&pitch={pitch}&fov={fov}"
                                f"&source=outdoor&key={MAPS_API_KEY}"
                            )
                            
                            street_view_images.append({
                                "vantage_point": vp['name'],
                                "view_direction": view_desc,
                                "heading": round(actual_heading),
                                "heading_offset": h_offset,
                                "pitch": pitch,
                                "pitch_desc": pitch_desc,
                                "fov": fov,
                                "fov_desc": fov_desc,
                                "pano_id": pano_id,
                                "pano_date": pano_date,
                                "lat": pano_lat,
                                "lng": pano_lng,
                                "url": image_url,
                                "description": f"{vp['name']} | {view_desc} view | {pitch_desc} | {fov_desc}"
                            })
                        if len(street_view_images) >= STREETVIEW_CONFIG['max_images_per_location']: break
                    if len(street_view_images) >= STREETVIEW_CONFIG['max_images_per_location']: break
                    
            except Exception as e:
                print(f"Error processing vantage point {vp['name']}: {e}")
                
        # Fallback if no images found
        if not street_view_images:
             street_view_images.append({
                "vantage_point": "Fallback",
                "view_direction": "default",
                "heading": 0,
                "heading_offset": 0,
                "pitch": 0,
                "pitch_desc": "level",
                "fov": 90,
                "fov_desc": "wide",
                "pano_id": "fallback",
                "pano_date": "Unknown",
                "lat": lat,
                "lng": lng,
                "url": f"https://maps.googleapis.com/maps/api/streetview?size=640x480&location={lat},{lng}&fov=90&key={MAPS_API_KEY}",
                "description": "Fallback (default view)"
            })

        return LocationResponse(
            name=place_name or query,
            address=formatted_address,
            lat=lat,
            lng=lng,
            total_images=len(street_view_images),
            unique_panoramas=len(seen_pano_ids),
            street_view_images=street_view_images,
            image_urls=[img["url"] for img in street_view_images[:10]]
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
