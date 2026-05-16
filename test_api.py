#!/usr/bin/env python3
"""
Test script for Chandra OCR HTTP API.
Creates a sample test image and sends it to the API for processing.
"""
import io
import json
import sys
import requests
from PIL import Image, ImageDraw, ImageFont

# API Configuration
API_BASE_URL = "http://localhost:5000"


def create_test_image():
    """Create a simple test image with text."""
    print("Creating test image...")
    
    # Create a white image
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add some text
    try:
        # Try to use a default font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except (OSError, IOError):
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Draw text
    draw.text((50, 50), "Chandra OCR Test", fill='black', font=font)
    draw.text((50, 150), "This is a test document", fill='black', font=font)
    draw.text((50, 250), "Line 1: Sample text", fill='black', font=font)
    draw.text((50, 350), "Line 2: More content", fill='black', font=font)
    draw.text((50, 450), "Line 3: Testing OCR", fill='black', font=font)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    print("✓ Test image created")
    return img_bytes


def test_health():
    """Test the health endpoint."""
    print("\n" + "="*60)
    print("Testing /health endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✓ Health check passed")
            return True
        else:
            print("✗ Health check failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_api_info():
    """Test the root endpoint."""
    print("\n" + "="*60)
    print("Testing / endpoint (API info)")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✓ API info retrieved")
            return True
        else:
            print("✗ Failed to get API info")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_process_image():
    """Test the process endpoint with an image."""
    print("\n" + "="*60)
    print("Testing /process endpoint with test image")
    print("="*60)
    
    try:
        # Create test image
        img_bytes = create_test_image()
        
        # Prepare the file for upload
        files = {'file': ('test_image.png', img_bytes, 'image/png')}
        data = {
            'include_images': 'true',
            'include_headers_footers': 'false'
        }
        
        print("Sending request to API...")
        response = requests.post(
            f"{API_BASE_URL}/process",
            files=files,
            data=data,
            timeout=300  # 5 minute timeout for processing
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Processing successful!")
            print(f"Filename: {result.get('filename')}")
            print(f"Number of pages: {result.get('num_pages')}")
            
            if result.get('pages'):
                for page in result['pages']:
                    print(f"\nPage {page['page_num']}:")
                    print(f"  Token count: {page.get('token_count')}")
                    print(f"  Chunks: {page.get('num_chunks')}")
                    print(f"  Images: {page.get('num_images')}")
                    print(f"  Markdown preview: {page.get('markdown', '')[:200]}...")
            
            # Save full response to file
            with open('test_response.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n✓ Full response saved to test_response.json")
            
            return True
        else:
            print(f"✗ Processing failed")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out (processing took too long)")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_missing_file():
    """Test the process endpoint without a file."""
    print("\n" + "="*60)
    print("Testing /process endpoint without file (should fail)")
    print("="*60)
    
    try:
        response = requests.post(f"{API_BASE_URL}/process")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✓ Correctly rejected request without file")
            return True
        else:
            print("✗ Should have returned 400 status")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_invalid_file_type():
    """Test the process endpoint with invalid file type."""
    print("\n" + "="*60)
    print("Testing /process endpoint with invalid file type (should fail)")
    print("="*60)
    
    try:
        # Create a text file
        files = {'file': ('test.txt', io.BytesIO(b'This is a text file'), 'text/plain')}
        
        response = requests.post(f"{API_BASE_URL}/process", files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✓ Correctly rejected invalid file type")
            return True
        else:
            print("✗ Should have returned 400 status")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("Chandra OCR HTTP API Test Suite")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print()
    
    # Check if custom URL is provided
    if len(sys.argv) > 1:
        global API_BASE_URL
        API_BASE_URL = sys.argv[1]
        print(f"Using custom API URL: {API_BASE_URL}\n")
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("API Info", test_api_info()))
    results.append(("Missing File", test_missing_file()))
    results.append(("Invalid File Type", test_invalid_file_type()))
    
    # This test requires the model to be loaded, so it might fail
    print("\nNote: The next test requires a model to be loaded and may take a while...")
    results.append(("Process Image", test_process_image()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print("\n" + "="*60)
    print(f"Total: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
