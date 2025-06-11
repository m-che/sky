#!/usr/bin/env python3
"""
SkyAR Batch Processing Test Script - 95% Completion Issue Test
Tests the batch processing functionality of the SkyAR demo application
with specific focus on the 95% completion issue
"""

import requests
import os
import time
import sys
import base64
from pathlib import Path
import random
import datetime

class SkyARBatchTester:
    def __init__(self, base_url="https://d604002f-0ae5-434f-a584-a4ecec2abf6d-8001.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_files = []
        self.batch_id = None
        self.test_results = {
            "completion_past_95": True,
            "file_operations_success": True,
            "timeout_handling": True,
            "status_updates_accurate": True,
            "concurrent_processing": True,
            "stuck_files": [],
            "completed_files": [],
            "error_files": []
        }
        
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
    
    def test_upload_multiple_images(self, num_images=3):
        """Test uploading multiple images for batch processing"""
        # Create test images with different colors
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
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
            'randomize_skybox': 'false',  # Use consistent skybox for testing
            'sky_template': 'bluesky1',
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
    
    def test_batch_status(self, max_attempts=60, delay=5):
        """Test monitoring batch processing status with focus on 95% issue"""
        if not self.batch_id:
            print("❌ No batch ID available for status check")
            return False
        
        print(f"\n🔍 Monitoring batch processing status (max {max_attempts} attempts, {delay}s delay)...")
        print(f"⚠️ Specifically watching for files stuck at 95% completion...")
        
        completed_count = 0
        total_files = len(self.uploaded_files)
        
        # Track files at 95% and how long they stay there
        files_at_95 = {}
        progress_history = {}
        
        start_time = time.time()
        
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
            elapsed = time.time() - start_time
            print(f"Batch progress: {completed_count}/{total_files} completed, {processing_count} processing, {error_count} errors (Elapsed: {elapsed:.1f}s)")
            
            # Check individual file progress
            for video_id, file_status in files.items():
                status = file_status.get("status", "unknown")
                progress = file_status.get("progress", 0)
                message = file_status.get("message", "")
                filename = file_status.get("filename", video_id)
                
                # Track progress history
                if video_id not in progress_history:
                    progress_history[video_id] = []
                progress_history[video_id].append((time.time(), progress, status, message))
                
                # Check for files at 95%
                if status == "processing" and progress == 95:
                    if video_id not in files_at_95:
                        files_at_95[video_id] = time.time()
                        print(f"⚠️ File {filename} reached 95% at {elapsed:.1f}s")
                    else:
                        time_at_95 = time.time() - files_at_95[video_id]
                        print(f"⚠️ File {filename} still at 95% after {time_at_95:.1f}s - Message: {message}")
                        
                        # If a file is stuck at 95% for more than 2 minutes, mark it
                        if time_at_95 > 120:
                            self.test_results["completion_past_95"] = False
                            if video_id not in self.test_results["stuck_files"]:
                                self.test_results["stuck_files"].append(video_id)
                elif status == "processing" and progress > 95:
                    # File moved past 95%
                    if video_id in files_at_95:
                        time_at_95 = time.time() - files_at_95[video_id]
                        print(f"✅ File {filename} moved past 95% after {time_at_95:.1f}s")
                        files_at_95.pop(video_id)
                elif status == "completed" and video_id in files_at_95:
                    # File completed from 95%
                    time_at_95 = time.time() - files_at_95[video_id]
                    print(f"✅ File {filename} completed from 95% after {time_at_95:.1f}s")
                    files_at_95.pop(video_id)
                    if video_id not in self.test_results["completed_files"]:
                        self.test_results["completed_files"].append(video_id)
                elif status == "error":
                    if video_id not in self.test_results["error_files"]:
                        self.test_results["error_files"].append(video_id)
                
                # Print current status
                if status == "processing":
                    print(f"  - {filename}: {status} ({progress}%) - {message}")
                else:
                    print(f"  - {filename}: {status} - {message}")
            
            # If all files are completed or we have errors, we're done
            if completed_count == total_files:
                print(f"✅ All {total_files} files completed successfully!")
                break
            elif completed_count + error_count == total_files:
                print(f"⚠️ Processing finished with {completed_count} completed and {error_count} errors")
                break
            
            # Wait before next check
            time.sleep(delay)
        
        # Final analysis
        print("\n📊 Final Analysis:")
        
        # Check if any files are still at 95%
        if files_at_95:
            print(f"❌ {len(files_at_95)} files stuck at 95%:")
            for video_id, start_time in files_at_95.items():
                filename = next((f["filename"] for f in self.uploaded_files if f["video_id"] == video_id), video_id)
                stuck_time = time.time() - start_time
                print(f"  - {filename}: stuck for {stuck_time:.1f}s")
            self.test_results["completion_past_95"] = False
        else:
            print("✅ No files stuck at 95%")
        
        # Check progress patterns
        for video_id, history in progress_history.items():
            filename = next((f["filename"] for f in self.uploaded_files if f["video_id"] == video_id), video_id)
            
            # Check for smooth progress
            progress_values = [p[1] for p in history]
            if len(progress_values) > 2:
                is_monotonic = all(x <= y for x, y in zip(progress_values, progress_values[1:]))
                if not is_monotonic:
                    print(f"⚠️ {filename}: Progress not monotonically increasing: {progress_values}")
                    self.test_results["status_updates_accurate"] = False
            
            # Check final status
            final_status = history[-1][2]
            if final_status == "completed":
                print(f"✅ {filename}: Completed successfully")
            elif final_status == "error":
                print(f"❌ {filename}: Failed with error: {history[-1][3]}")
            else:
                print(f"⚠️ {filename}: Final status: {final_status} at {history[-1][1]}%")
                if history[-1][1] == 95:
                    self.test_results["completion_past_95"] = False
        
        # Overall success determination
        success = completed_count == total_files
        
        # Print summary
        print(f"\n📋 Test Summary:")
        print(f"- Files completing past 95%: {'✅ Yes' if self.test_results['completion_past_95'] else '❌ No'}")
        print(f"- Status updates accurate: {'✅ Yes' if self.test_results['status_updates_accurate'] else '❌ No'}")
        print(f"- Completed files: {len(self.test_results['completed_files'])}/{total_files}")
        print(f"- Files stuck at 95%: {len(self.test_results['stuck_files'])}")
        print(f"- Error files: {len(self.test_results['error_files'])}")
        
        return success
    
    def run_all_tests(self):
        """Run all batch processing tests"""
        print(f"🕒 Test started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.test_upload_multiple_images(num_images=3):
            print("❌ Failed to upload test images, stopping tests")
            return False
        
        if not self.test_batch_processing():
            print("❌ Failed to start batch processing, stopping tests")
            return False
        
        batch_success = self.test_batch_status(max_attempts=60, delay=5)
        
        print(f"🕒 Test completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Overall success is based on batch success AND no files stuck at 95%
        return batch_success and self.test_results["completion_past_95"]

def main():
    # Setup
    base_url = "https://d604002f-0ae5-434f-a584-a4ecec2abf6d-8001.preview.emergentagent.com"
    
    # Check if a custom URL was provided
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing SkyAR Batch Processing at: {base_url}")
    print(f"Focus: Testing the 95% completion issue")
    tester = SkyARBatchTester(base_url)
    
    # Run tests
    success = tester.run_all_tests()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Batch processing test {'succeeded' if success else 'failed'}")
    
    if not success and tester.test_results["stuck_files"]:
        print(f"❌ Test failed: Files stuck at 95%: {len(tester.test_results['stuck_files'])}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())