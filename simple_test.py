#!/usr/bin/env python3
"""
SkyAR Batch Processing Test Script (Simple Version)
Tests the batch processing functionality of the SkyAR demo application
"""

import requests
import os
import time
import sys
from PIL import Image
import random

# Create a test image
def create_test_image():
    img = Image.new('RGB', (512, 512), color=(255, 0, 0))
    img_path = f"/tmp/test_image_{random.randint(1000, 9999)}.jpg"
    img.save(img_path)
    print(f"Created test image at {img_path}")
    return img_path

# Upload a single image
def upload_image(image_path, base_url="http://localhost:8001"):
    url = f"{base_url}/api/upload-single"
    files = {'file': (os.path.basename(image_path), open(image_path, 'rb'), 'image/jpeg')}
    
    print(f"Uploading image to {url}")
    response = requests.post(url, files=files)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success") and "files" in result:
            video_id = result["files"][0]["video_id"]
            print(f"✅ Image uploaded successfully with ID: {video_id}")
            return video_id
    
    print(f"❌ Failed to upload image: {response.text}")
    return None

# Start processing
def start_processing(video_id, base_url="http://localhost:8001"):
    url = f"{base_url}/api/process"
    data = {
        "video_id": video_id,
        "sky_template": "bluesky1",
        "auto_light_matching": True,
        "relighting_factor": 0.0,
        "recoloring_factor": 0.1,
        "halo_effect": True
    }
    
    print(f"Starting processing for video_id: {video_id}")
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Processing started successfully")
            return True
    
    print(f"❌ Failed to start processing: {response.text}")
    return False

# Check processing status
def check_status(video_id, base_url="http://localhost:8001", max_attempts=60, delay=2):
    url = f"{base_url}/api/status/{video_id}"
    
    print(f"Checking status for video_id: {video_id}")
    
    for attempt in range(max_attempts):
        response = requests.get(url)
        
        if response.status_code == 200:
            status = response.json()
            current_status = status.get("status", "unknown")
            progress = status.get("progress", 0)
            message = status.get("message", "")
            
            print(f"Status: {current_status}, Progress: {progress}%, Message: {message}")
            
            if current_status == "completed":
                print("✅ Processing completed successfully!")
                return True
            elif current_status == "error":
                print(f"❌ Processing failed: {message}")
                return False
        else:
            print(f"❌ Failed to get status: {response.text}")
        
        time.sleep(delay)
    
    print("⚠️ Timeout reached, processing did not complete")
    return False

def main():
    base_url = "http://localhost:8001"
    
    # Create and upload test image
    image_path = create_test_image()
    video_id = upload_image(image_path, base_url)
    
    if not video_id:
        print("❌ Failed to upload image, stopping test")
        return 1
    
    # Start processing
    if not start_processing(video_id, base_url):
        print("❌ Failed to start processing, stopping test")
        return 1
    
    # Check status
    success = check_status(video_id, base_url)
    
    # Clean up
    try:
        os.remove(image_path)
        print(f"Removed test image: {image_path}")
    except:
        pass
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())