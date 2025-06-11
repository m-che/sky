#!/usr/bin/env python3
"""
SkyAR Batch Processing Test Script (Batch Version)
Tests the batch processing functionality of the SkyAR demo application
"""

import requests
import os
import time
import sys
from PIL import Image
import random

# Create test images
def create_test_images(num_images=4):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    image_paths = []
    
    for i in range(min(num_images, len(colors))):
        img = Image.new('RGB', (512, 512), color=colors[i])
        img_path = f"/tmp/test_image_{i+1}.jpg"
        img.save(img_path)
        image_paths.append(img_path)
    
    print(f"Created {len(image_paths)} test images")
    return image_paths

# Upload multiple images
def upload_images(image_paths, base_url="http://localhost:8001"):
    url = f"{base_url}/api/upload"
    files = []
    
    for path in image_paths:
        file_name = os.path.basename(path)
        files.append(('files', (file_name, open(path, 'rb'), 'image/jpeg')))
    
    print(f"Uploading {len(files)} images to {url}")
    response = requests.post(url, files=files)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success") and "files" in result:
            video_ids = [file["video_id"] for file in result["files"]]
            print(f"✅ Uploaded {len(video_ids)} images successfully")
            return video_ids
    
    print(f"❌ Failed to upload images: {response.text}")
    return []

# Start batch processing
def start_batch_processing(video_ids, base_url="http://localhost:8001"):
    url = f"{base_url}/api/process-batch"
    form_data = {
        'video_ids': video_ids,
        'randomize_skybox': 'true',
        'auto_light_matching': 'true',
        'relighting_factor': '0.0',
        'recoloring_factor': '0.1',
        'halo_effect': 'true'
    }
    
    print(f"Starting batch processing for {len(video_ids)} images")
    response = requests.post(url, data=form_data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            batch_id = result.get("batch_id")
            print(f"✅ Batch processing started with ID: {batch_id}")
            return batch_id
    
    print(f"❌ Failed to start batch processing: {response.text}")
    return None

# Check batch status
def check_batch_status(batch_id, base_url="http://localhost:8001", max_attempts=60, delay=2):
    url = f"{base_url}/api/batch-status/{batch_id}"
    
    print(f"Checking batch status for batch_id: {batch_id}")
    
    for attempt in range(max_attempts):
        response = requests.get(url)
        
        if response.status_code == 200:
            status = response.json()
            
            # Count completed files
            files = status.get("files", {})
            total_files = len(files)
            completed_count = sum(1 for f in files.values() if f.get("status") == "completed")
            processing_count = sum(1 for f in files.values() if f.get("status") == "processing")
            error_count = sum(1 for f in files.values() if f.get("status") == "error")
            
            print(f"Batch progress: {completed_count}/{total_files} completed, {processing_count} processing, {error_count} errors")
            
            # Check individual file progress
            for video_id, file_status in files.items():
                status_text = file_status.get("status", "unknown")
                progress = file_status.get("progress", 0)
                filename = file_status.get("filename", video_id)
                
                if status_text == "processing":
                    print(f"  - {filename}: {status_text} ({progress}%)")
                else:
                    print(f"  - {filename}: {status_text}")
            
            # If all files are completed or we have errors, we're done
            if completed_count == total_files:
                print(f"✅ All {total_files} files completed successfully!")
                return True
            elif error_count > 0:
                print(f"❌ {error_count} files failed processing")
                return False
        else:
            print(f"❌ Failed to get batch status: {response.text}")
        
        time.sleep(delay)
    
    print("⚠️ Timeout reached, batch processing did not complete")
    return False

def main():
    base_url = "http://localhost:8001"
    
    # Create and upload test images
    image_paths = create_test_images(4)
    video_ids = upload_images(image_paths, base_url)
    
    if not video_ids:
        print("❌ Failed to upload images, stopping test")
        return 1
    
    # Start batch processing
    batch_id = start_batch_processing(video_ids, base_url)
    
    if not batch_id:
        print("❌ Failed to start batch processing, stopping test")
        return 1
    
    # Check batch status
    success = check_batch_status(batch_id, base_url)
    
    # Clean up
    for path in image_paths:
        try:
            os.remove(path)
            print(f"Removed test image: {path}")
        except:
            pass
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())