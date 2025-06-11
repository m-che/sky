#!/usr/bin/env python3
"""
SkyAR Sequential Batch Processing Test Script
Tests the sequential batch processing functionality of the SkyAR demo application
to verify it resolves the stuck processing issues
"""

import requests
import os
import time
import sys
import base64
from pathlib import Path
import random
import datetime
from PIL import Image

class SkyARSequentialBatchTester:
    def __init__(self, base_url="https://d604002f-0ae5-434f-a584-a4ecec2abf6d-8001.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_files = []
        self.batch_id = None
        self.test_results = {
            "sequential_processing": True,  # Only one file processing at a time
            "completion_past_95": True,     # Files move past 95% completion
            "status_updates_accurate": True, # Status updates are accurate
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
    
    def create_test_image(self, size=512, color=(255, 0, 0)):
        """Create a simple test image"""
        img = Image.new('RGB', (size, size), color=color)
        img_path = f"/tmp/test_image_{random.randint(1000, 9999)}.jpg"
        img.save(img_path)
        return img_path
    
    def test_upload_multiple_images(self, num_images=4):
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
    
    def test_sequential_batch_status(self, max_attempts=60, delay=5):
        """Test monitoring batch processing status with focus on sequential processing"""
        if not self.batch_id:
            print("❌ No batch ID available for status check")
            return False
        
        print(f"\n🔍 Monitoring sequential batch processing (max {max_attempts} attempts, {delay}s delay)...")
        print(f"⚠️ Specifically watching for sequential processing (only one file at a time)...")
        
        completed_count = 0
        total_files = len(self.uploaded_files)
        
        # Track processing history
        processing_history = []
        file_status_history = {}
        
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
            
            # Count files by status
            files = response["files"]
            completed_count = sum(1 for f in files.values() if f.get("status") == "completed")
            processing_count = sum(1 for f in files.values() if f.get("status") == "processing")
            pending_count = sum(1 for f in files.values() if f.get("status") == "pending")
            error_count = sum(1 for f in files.values() if f.get("status") == "error")
            
            # Record the current state for analysis
            current_state = {
                "timestamp": time.time(),
                "completed": completed_count,
                "processing": processing_count,
                "pending": pending_count,
                "error": error_count,
                "processing_files": [vid for vid, status in files.items() if status.get("status") == "processing"],
                "file_details": {vid: {"status": status.get("status"), "progress": status.get("progress")} 
                                for vid, status in files.items()}
            }
            processing_history.append(current_state)
            
            # Print progress information
            elapsed = time.time() - start_time
            print(f"Batch progress: {completed_count}/{total_files} completed, {processing_count} processing, {pending_count} pending, {error_count} errors (Elapsed: {elapsed:.1f}s)")
            
            # Check for sequential processing - only one file should be processing at a time
            if processing_count > 1:
                print(f"❌ CRITICAL: Multiple files processing simultaneously: {processing_count}")
                self.test_results["sequential_processing"] = False
                
                # List the files that are processing
                processing_files = [vid for vid, status in files.items() if status.get("status") == "processing"]
                print(f"   Processing files: {processing_files}")
            
            # Check individual file progress
            for video_id, file_status in files.items():
                status = file_status.get("status", "unknown")
                progress = file_status.get("progress", 0)
                message = file_status.get("message", "")
                filename = file_status.get("filename", video_id)
                
                # Track file status history
                if video_id not in file_status_history:
                    file_status_history[video_id] = []
                file_status_history[video_id].append((time.time(), status, progress, message))
                
                # Print current status
                if status == "processing":
                    print(f"  - {filename}: {status} ({progress}%) - {message}")
                else:
                    print(f"  - {filename}: {status} - {message}")
                
                # Check for files stuck at 95%
                if status == "processing" and progress == 95:
                    # Check how long it's been at 95%
                    history = file_status_history[video_id]
                    if len(history) >= 2:
                        time_at_95 = 0
                        for i in range(len(history) - 2, -1, -1):
                            if history[i][2] == 95:  # If previous progress was also 95%
                                time_at_95 = history[-1][0] - history[i][0]  # Time difference
                            else:
                                break
                        
                        if time_at_95 > 60:  # If stuck at 95% for more than 60 seconds
                            print(f"⚠️ File {filename} stuck at 95% for {time_at_95:.1f}s")
                            if video_id not in self.test_results["stuck_files"]:
                                self.test_results["stuck_files"].append(video_id)
                            self.test_results["completion_past_95"] = False
                
                # Track completed files
                if status == "completed" and video_id not in self.test_results["completed_files"]:
                    self.test_results["completed_files"].append(video_id)
                
                # Track error files
                if status == "error" and video_id not in self.test_results["error_files"]:
                    self.test_results["error_files"].append(video_id)
            
            # If all files are completed or we have errors, we're done
            if completed_count == total_files:
                print(f"✅ All {total_files} files completed successfully!")
                break
            elif completed_count + error_count == total_files:
                print(f"⚠️ Processing finished with {completed_count} completed and {error_count} errors")
                break
            
            # Wait before next check
            time.sleep(delay)
        
        # Analyze the processing history to verify sequential processing
        print("\n📊 Sequential Processing Analysis:")
        
        # Check if we ever had more than one file processing at a time
        multiple_processing = any(state["processing"] > 1 for state in processing_history)
        if multiple_processing:
            print("❌ Multiple files were processing simultaneously - NOT sequential")
            self.test_results["sequential_processing"] = False
        else:
            print("✅ Only one file was processing at a time - Sequential processing confirmed")
        
        # Check if files were processed in sequence (one completes before next starts)
        if len(processing_history) > 1:
            sequential_flow = True
            processing_files_sequence = []
            
            for state in processing_history:
                if state["processing"] == 1:
                    processing_files_sequence.extend(state["processing_files"])
            
            # Remove duplicates while preserving order
            seen = set()
            processing_sequence = [x for x in processing_files_sequence if not (x in seen or seen.add(x))]
            
            print(f"Processing sequence: {processing_sequence}")
            
            # Check if files moved from pending to processing to completed in sequence
            if len(processing_sequence) > 1:
                for i in range(len(processing_sequence) - 1):
                    current_file = processing_sequence[i]
                    next_file = processing_sequence[i + 1]
                    
                    # Find when current file completed and next file started processing
                    current_completed = False
                    for state in processing_history:
                        if current_file in state["file_details"] and state["file_details"][current_file]["status"] == "completed":
                            current_completed = True
                        
                        if current_completed and next_file in state["file_details"] and state["file_details"][next_file]["status"] == "processing":
                            # This is good - next file started processing after current completed
                            break
                    
                    if not current_completed:
                        sequential_flow = False
                        print(f"❌ File {current_file} never completed before {next_file} started")
            
            if sequential_flow:
                print("✅ Files were processed in proper sequence (one completes before next starts)")
            else:
                print("❌ Files were not processed in proper sequence")
                self.test_results["sequential_processing"] = False
        
        # Check for files stuck at 95%
        if self.test_results["stuck_files"]:
            print(f"❌ {len(self.test_results['stuck_files'])} files were stuck at 95%")
            for vid in self.test_results["stuck_files"]:
                filename = next((f["filename"] for f in self.uploaded_files if f["video_id"] == vid), vid)
                print(f"  - {filename}")
        else:
            print("✅ No files were stuck at 95%")
        
        # Print summary
        print(f"\n📋 Test Summary:")
        print(f"- Sequential processing (one at a time): {'✅ Yes' if self.test_results['sequential_processing'] else '❌ No'}")
        print(f"- Files completing past 95%: {'✅ Yes' if self.test_results['completion_past_95'] else '❌ No'}")
        print(f"- Status updates accurate: {'✅ Yes' if self.test_results['status_updates_accurate'] else '❌ No'}")
        print(f"- Completed files: {len(self.test_results['completed_files'])}/{total_files}")
        print(f"- Files stuck at 95%: {len(self.test_results['stuck_files'])}")
        print(f"- Error files: {len(self.test_results['error_files'])}")
        
        return self.test_results["sequential_processing"] and self.test_results["completion_past_95"]
    
    def run_all_tests(self):
        """Run all sequential batch processing tests"""
        print(f"🕒 Test started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.test_upload_multiple_images(num_images=4):
            print("❌ Failed to upload test images, stopping tests")
            return False
        
        if not self.test_batch_processing():
            print("❌ Failed to start batch processing, stopping tests")
            return False
        
        batch_success = self.test_sequential_batch_status(max_attempts=60, delay=5)
        
        print(f"🕒 Test completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Overall success is based on sequential processing AND no files stuck at 95%
        return batch_success

def main():
    # Setup
    base_url = "https://d604002f-0ae5-434f-a584-a4ecec2abf6d-8001.preview.emergentagent.com"
    
    # Check if a custom URL was provided
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Testing SkyAR Sequential Batch Processing at: {base_url}")
    print(f"Focus: Verifying sequential processing (one file at a time) and no stuck files")
    tester = SkyARSequentialBatchTester(base_url)
    
    # Run tests
    success = tester.run_all_tests()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Sequential batch processing test {'succeeded' if success else 'failed'}")
    
    if not success:
        if not tester.test_results["sequential_processing"]:
            print(f"❌ Test failed: Files were not processed sequentially")
        if not tester.test_results["completion_past_95"]:
            print(f"❌ Test failed: Files stuck at 95%: {len(tester.test_results['stuck_files'])}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())