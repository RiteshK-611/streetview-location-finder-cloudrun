import requests
import json
import os

def test_find_location():
    url = "http://localhost:8000/find_location"
    payload = {"query": "Empire State Building"}
    headers = {"Content-Type": "application/json"}
    
    print(f"Testing {url} with query: {payload['query']}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Success!")
            print(f"Name: {data.get('name')}")
            print(f"Address: {data.get('address')}")
            print(f"Total Images: {data.get('total_images')}")
            print(json.dumps(data, indent=2))
        else:
            print("Failed")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the service. Is it running?")

if __name__ == "__main__":
    test_find_location()
