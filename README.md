# 🗺️ Street View Location Finder (Cloud Run Microservice)

A comprehensive Street View location finder with multi-angle imagery using Google Maps API. <br>
This service powers the **Scout Agent** in the _Access-All-Areas_ project by turning a free-text location query into:

- A precise building location (name, address, lat/lng)
- A **multi‑vantage Street View image set** with cameras pointing _towards_ the building
- Metadata needed by downstream agents (Vision, Judge, Reporter)

It is deployed as a stateless **Cloud Run** microservice and consumed via the `find_location_comprehensive(...)` tool in the Kaggle notebook.

---

## 🎯 What This Service Does

Given an input like:

```json
{ "query": "Philadelphia Museum of Art, Philadelphia" }
```
the service:

- Resolves the location using **Google Maps APIs**:
  - Uses **Places API** first (best for POIs, landmarks, businesses).
  - Falls back to **Geocoding API** (for street addresses).

- Computes multiple **outdoor vantage points** around the building using geographic offsets.

- For each vantage point, calculates a **“look‑at” heading** so the camera points at the building’s entrance/facade.

- Calls **Street View Static API** to fetch image URLs with:
  - Multiple **headings** (center / left / right),
  - Multiple **pitches** (level / downward),
  - Multiple **fields of view** (wide / zoomed).

- **Deduplicates panoramas** and returns a **compact JSON structure** optimized for AI analysis.

---

## Setup

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set Environment Variables:**
    You must set the `MAPS_API_KEY` environment variable.
    ```bash
    export MAPS_API_KEY="your_google_maps_api_key"
    # Or on Windows PowerShell:
    # $env:MAPS_API_KEY="your_google_maps_api_key"
    ```

## Running Locally

Start the server:
```bash
uvicorn main:app --reload
```

The service will be available at `http://localhost:8000`.

## API Usage

**Endpoint:** `POST /find_location`

**Request Body:**
```json
{
  "query": "Empire State Building"
}
```

**Response:**
Returns a JSON object containing location details and a list of Street View images.

## Docker

Build the image:
```bash
docker build -t streetview-location-finder .
```

Run the container:
```bash
docker run -p 8080:8080 -e MAPS_API_KEY="your_key" streetview-location-finder
