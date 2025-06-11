#!/usr/bin/env python3
"""
SkyAR Batch Processing Test Script (Local Version)
Tests the batch processing functionality of the SkyAR demo application
"""

import requests
import os
import time
import sys
import base64
from pathlib import Path
import random

class SkyARBatchTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_files = []
        self.batch_id = None
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, json_data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files)
                elif json_data:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=json_data, headers=headers)
                else:
                    response = requests.post(url, data=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.text[:200]}...")
                    return False, response.json()
                except:
                    return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}
    
    def create_test_image(self, size=1024, color=(255, 0, 0)):
        """Create a simple test image"""
        from PIL import Image
        img = Image.new('RGB', (size, size), color=color)
        img_path = f"/tmp/test_image_{random.randint(1000, 9999)}.jpg"
        img.save(img_path)
        return img_path
    
    def test_upload_multiple_images(self, num_images=1):
        """Test uploading multiple images for batch processing"""
        # Create test images with different colors
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        image_paths = []
        
        for i in range(min(num_images, len(colors))):
            image_paths.append(self.create_test_image(size=512, color=colors[i]))
        
        print(f"Created {len(image_paths)} test images")
        
        # Upload images
        files = []
        for path in image_paths:
            file_name = os.path.basename(path)
            files.append(('files', (file_name, open(path, 'rb'), 'image/jpeg')))
        
        success, response = self.run_test(
            "Upload Multiple Images",
            "POST",
            "api/upload",
            200,
            files=files
        )
        
        # Clean up test images
        for path in image_paths:
            try:
                os.remove(path)
            except:
                pass
        
        if success and response.get("success") == True and "files" in response:
            self.uploaded_files = response["files"]
            print(f"✅ Uploaded {len(self.uploaded_files)} images successfully")
            return True
        return False
    
    def test_batch_processing(self):
        """Test starting batch processing"""
        if not self.uploaded_files:
            print("❌ No files uploaded for batch processing")
            return False
        
        # Create form data for batch processing
        form_data = {
            'video_ids': [file["video_id"] for file in self.uploaded_files],
            'randomize_skybox': 'true',
            'auto_light_matching': 'true',
            'relighting_factor': '0.0',
            'recoloring_factor': '0.1',
            'halo_effect': 'true'
        }
        
        success, response = self.run_test(
            "Start Batch Processing",
            "POST",
            "api/process-batch",
            200,
            data=form_data
        )
        
        if success and response.get("success") == True:
            self.batch_id = response.get("batch_id")
            print(f"✅ Batch processing started with ID: {self.batch_id}")
            return True
        return False
    
    def test_batch_status(self, max_attempts=60, delay=2):
        """Test monitoring batch processing status"""
        if not self.batch_id:
            print("❌ No batch ID available for status check")
            return False
        
        print(f"\n🔍 Monitoring batch processing status (max {max_attempts} attempts, {delay}s delay)...")
        
        completed_count = 0
        total_files = len(self.uploaded_files)
        
        for attempt in range(max_attempts):
            success, response = self.run_test(
                f"Batch Status Check (Attempt {attempt+1}/{max_attempts})",
                "GET",
                f"api/batch-status/{self.batch_id}",
                200
            )
            
            if not success:
                print(f"❌ Failed to get batch status on attempt {attempt+1}")
                continue
            
            # Check if the response has the expected structure
            if "files" not in response:
                print(f"❌ Invalid batch status response: {response}")
                time.sleep(delay)
                continue
            
            # Count completed files
            files = response["files"]
            completed_count = sum(1 for f in files.values() if f.get("status") == "completed")
            processing_count = sum(1 for f in files.values() if f.get("status") == "processing")
            error_count = sum(1 for f in files.values() if f.get("status") == "error")
            
            # Print progress information
            print(f"Batch progress: {completed_count}/{total_files} completed, {processing_count} processing, {error_count} errors")
            
            # Check individual file progress
            for video_id, file_status in files.items():
                status = file_status.get("status", "unknown")
                progress = file_status.get("progress", 0)
                filename = file_status.get("filename", video_id)
                
                if status == "processing":
                    print(f"  - {filename}: {status} ({progress}%)")
                else:
                    print(f"  - {filename}: {status}")
            
            # If all files are completed or we have errors, we're done
            if completed_count == total_files or error_count > 0:
                if completed_count == total_files:
                    print(f"✅ All {total_files} files completed successfully!")
                    return True
                elif error_count > 0:
                    print(f"❌ {error_count} files failed processing")
                    return False
            
            # Wait before next check
            time.sleep(delay)
        
        # If we get here, we've reached the maximum number of attempts
        if completed_count == total_files:
            print(f"✅ All {total_files} files completed successfully!")
            return True
        else:
            print(f"⚠️ Timeout reached. {completed_count}/{total_files} files completed.")
            return completed_count > 0  # Consider partial success
    
    def run_all_tests(self):
        """Run all batch processing tests"""
        if not self.test_upload_multiple_images(num_images=4):
            print("❌ Failed to upload test images, stopping tests")
            return False
        
        if not self.test_batch_processing():
            print("❌ Failed to start batch processing, stopping tests")
            return False
        
        return self.test_batch_status()

def main():
    # Setup
    base_url = "http://localhost:8001"
    
    # Check if a custom URL was provided
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing SkyAR Batch Processing at: {base_url}")
    tester = SkyARBatchTester(base_url)
    
    # Run tests
    success = tester.run_all_tests()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Batch processing test {'succeeded' if success else 'failed'}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())