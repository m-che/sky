#!/usr/bin/env python3
"""
SkyAR Enhanced Features Test Script
Tests the enhanced features of the SkyAR demo application
"""

import requests
import os
import time
import sys
import base64
import json
from pathlib import Path

class SkyAREnhancedTester:
    def __init__(self, base_url="https://d604002f-0ae5-434f-a584-a4ecec2abf6d-8001.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.video_id = None
        self.image_id = None
        
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
    
    def test_upload_image(self):
        """Test uploading an image file"""
        # Create a small test image (just some bytes that look like an image)
        # This is just for testing the API, not for actual processing
        test_image_data = b"\xFF\xD8\xFF\xE0\x10JFIF\x01\x01" + b"X" * 1024
        files = {'file': ('test.jpg', test_image_data, 'image/jpeg')}
        
        success, response = self.run_test(
            "Upload Image",
            "POST",
            "api/upload-single",
            200,
            files=files
        )
        
        if success and response.get("success") == True and "files" in response:
            self.image_id = response["files"][0]["video_id"]  # API uses video_id for both
            print(f"✅ Image uploaded successfully with ID: {self.image_id}")
            return True
        return False
    
    def test_save_enhanced_image(self):
        """Test saving an enhanced image"""
        if not self.image_id:
            print("❌ No image ID available for enhancement")
            return False
        
        # Create a simple base64 image (just a small red square)
        # In a real scenario, this would be the enhanced image from the canvas
        width, height = 100, 100
        red_square = bytearray([255, 0, 0, 255] * (width * height))  # RGBA red pixels
        
        # Convert to base64
        base64_image = base64.b64encode(red_square).decode('utf-8')
        
        # Create form data
        form_data = {
            'video_id': self.image_id,
            'image_data': f"data:image/png;base64,{base64_image}"
        }
        
        success, response = self.run_test(
            "Save Enhanced Image",
            "POST",
            "api/save-enhanced-image",
            200,
            data=form_data
        )
        
        if success and response.get("success") == True:
            print(f"✅ Enhanced image saved successfully")
            return True
        return False
    
    def test_apply_preset_to_all(self):
        """Test applying a preset to all images"""
        if not self.image_id:
            print("❌ No image ID available for preset application")
            return False
        
        # Create form data
        form_data = {
            'video_ids': [self.image_id],
            'preset_name': 'vivid',
            'preset_settings': json.dumps({
                'contrast': 120,
                'saturation': 130,
                'highlights': 15,
                'vibrance': 20,
                'shadow': 15,
                'warmth': 0
            })
        }
        
        success, response = self.run_test(
            "Apply Preset to All",
            "POST",
            "api/apply-preset-to-all",
            200,
            data=form_data
        )
        
        if success and response.get("success") == True:
            print(f"✅ Preset applied to all images successfully")
            return True
        return False
    
    def test_download_all_zip(self):
        """Test downloading all images as ZIP"""
        if not self.image_id:
            print("❌ No image ID available for ZIP download")
            return False
        
        # Create form data
        form_data = {
            'video_ids': [self.image_id]
        }
        
        # This endpoint returns a binary file, so we'll just check the status code
        try:
            url = f"{self.base_url}/api/download-all-zip"
            response = requests.post(url, data=form_data)
            
            if response.status_code == 200 and response.headers.get('Content-Type') == 'application/zip':
                self.tests_passed += 1
                print(f"✅ ZIP download successful - Content-Type: {response.headers.get('Content-Type')}")
                print(f"✅ ZIP file size: {len(response.content)} bytes")
                return True
            else:
                print(f"❌ ZIP download failed - Status: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
                return False
        except Exception as e:
            print(f"❌ ZIP download failed - Error: {str(e)}")
            return False

def main():
    # Setup
    base_url = "https://d604002f-0ae5-434f-a584-a4ecec2abf6d-8001.preview.emergentagent.com"  # Default URL
    
    # Check if a custom URL was provided
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing SkyAR Enhanced Features at: {base_url}")
    tester = SkyAREnhancedTester(base_url)
    
    # Run tests
    if not tester.test_upload_image():
        print("❌ Image upload failed, stopping tests")
        return 1
    
    if not tester.test_save_enhanced_image():
        print("❌ Save enhanced image failed")
        # Continue with other tests
    
    if not tester.test_apply_preset_to_all():
        print("❌ Apply preset to all failed")
        # Continue with other tests
    
    if not tester.test_download_all_zip():
        print("❌ Download all as ZIP failed")
        # Continue with other tests
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
