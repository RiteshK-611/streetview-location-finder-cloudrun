# streetview-location-finder-cloudrun
Cloud Run service for comprehensive Street View location finder with multi-angle imagery using Google Maps API

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
