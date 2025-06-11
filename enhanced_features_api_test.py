#!/usr/bin/env python3
"""
SkyAR Enhanced Features API Test Script
Tests the enhanced API endpoints of the SkyAR demo application
"""

import requests
import os
import time
import sys
import base64
import json
from pathlib import Path

class SkyARAPITester:
    def __init__(self, base_url="https://d604002f-0ae5-434f-a584-a4ecec2abf6d-8001.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        
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
    
    def test_save_enhanced_image_endpoint(self):
        """Test the save enhanced image endpoint"""
        # Create a simple base64 image (just a small red square)
        width, height = 100, 100
        red_square = bytearray([255, 0, 0, 255] * (width * height))  # RGBA red pixels
        
        # Convert to base64
        base64_image = base64.b64encode(red_square).decode('utf-8')
        
        # Create form data with a non-existent video_id (should return 404)
        form_data = {
            'video_id': 'non-existent-id',
            'image_data': f"data:image/png;base64,{base64_image}"
        }
        
        success, response = self.run_test(
            "Save Enhanced Image (Invalid ID)",
            "POST",
            "api/save-enhanced-image",
            404,  # Expect 404 for non-existent ID
            data=form_data
        )
        
        return success
    
    def test_apply_preset_to_all_endpoint(self):
        """Test the apply preset to all endpoint"""
        # Create form data with no video_ids (should return 400)
        form_data = {
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
            "Apply Preset to All (No IDs)",
            "POST",
            "api/apply-preset-to-all",
            400,  # Expect 400 for missing video_ids
            data=form_data
        )
        
        return success
    
    def test_download_all_zip_endpoint(self):
        """Test the download all as ZIP endpoint"""
        # Create form data with non-existent video_ids (should return 404)
        form_data = {
            'video_ids': ['non-existent-id-1', 'non-existent-id-2']
        }
        
        try:
            url = f"{self.base_url}/api/download-all-zip"
            response = requests.post(url, data=form_data)
            
            if response.status_code == 404:
                self.tests_passed += 1
                print(f"✅ ZIP download (invalid IDs) correctly returned 404")
                return True
            else:
                print(f"❌ ZIP download (invalid IDs) failed - Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ ZIP download (invalid IDs) failed - Error: {str(e)}")
            return False

def main():
    # Setup
    base_url = "https://d604002f-0ae5-434f-a584-a4ecec2abf6d-8001.preview.emergentagent.com"  # Default URL
    
    # Check if a custom URL was provided
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing SkyAR Enhanced API Endpoints at: {base_url}")
    tester = SkyARAPITester(base_url)
    
    # Run tests
    tester.test_save_enhanced_image_endpoint()
    tester.test_apply_preset_to_all_endpoint()
    tester.test_download_all_zip_endpoint()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
