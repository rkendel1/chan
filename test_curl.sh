#!/bin/bash
# Quick test script for Chandra OCR HTTP API using curl

set -e  # Exit on error

API_URL="${1:-http://localhost:5000}"
echo "Testing Chandra OCR API at: $API_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health check
echo "=========================================="
echo "Test 1: Health Check"
echo "=========================================="
echo "Command: curl $API_URL/health"
echo ""
if curl -s "$API_URL/health" | python3 -m json.tool; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
fi
echo ""

# Test 2: API info
echo "=========================================="
echo "Test 2: API Information"
echo "=========================================="
echo "Command: curl $API_URL/"
echo ""
if curl -s "$API_URL/" | python3 -m json.tool; then
    echo -e "${GREEN}✓ API info retrieved${NC}"
else
    echo -e "${RED}✗ Failed to get API info${NC}"
fi
echo ""

# Test 3: Create a test image and send it
echo "=========================================="
echo "Test 3: Process Test Image"
echo "=========================================="

# Create a simple test image using Python
python3 - <<'PYEOF'
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (800, 400), color='white')
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
except (OSError, IOError):
    font = ImageFont.load_default()
draw.text((50, 50), "Test Document", fill='black', font=font)
draw.text((50, 150), "This is a test for Chandra OCR", fill='black', font=font)
draw.text((50, 250), "Testing file upload via curl", fill='black', font=font)
img.save('/tmp/chandra_test.png')
print("✓ Test image created at /tmp/chandra_test.png")
PYEOF

echo ""
echo "Command: curl -X POST $API_URL/process -F \"file=@/tmp/chandra_test.png\""
echo ""
echo -e "${YELLOW}Note: This test requires the model to be loaded and may take a while...${NC}"
echo ""

if curl -X POST "$API_URL/process" \
    -F "file=@/tmp/chandra_test.png" \
    -F "include_images=true" \
    -o /tmp/chandra_response.json 2>/dev/null; then
    
    # Check if response is valid JSON and contains success
    if python3 -m json.tool < /tmp/chandra_response.json > /dev/null 2>&1; then
        echo "Response saved to /tmp/chandra_response.json"
        echo ""
        echo "Response preview:"
        cat /tmp/chandra_response.json | python3 -m json.tool | head -30
        echo ""
        echo -e "${GREEN}✓ Image processing test passed${NC}"
    else
        echo "Response:"
        cat /tmp/chandra_response.json
        echo ""
        echo -e "${RED}✗ Invalid response received${NC}"
    fi
else
    echo -e "${RED}✗ Image processing test failed${NC}"
fi
echo ""

# Test 4: Test with missing file (should fail)
echo "=========================================="
echo "Test 4: Missing File (should fail gracefully)"
echo "=========================================="
echo "Command: curl -X POST $API_URL/process"
echo ""
if curl -s -X POST "$API_URL/process" | python3 -m json.tool | grep -q "error"; then
    echo -e "${GREEN}✓ Correctly rejected request without file${NC}"
else
    echo -e "${RED}✗ Should have returned an error${NC}"
fi
echo ""

# Test 5: Test with invalid file type (should fail)
echo "=========================================="
echo "Test 5: Invalid File Type (should fail gracefully)"
echo "=========================================="
echo "Creating a text file..."
echo "This is not an image" > /tmp/test.txt
echo ""
echo "Command: curl -X POST $API_URL/process -F \"file=@/tmp/test.txt\""
echo ""
if curl -s -X POST "$API_URL/process" -F "file=@/tmp/test.txt" | python3 -m json.tool | grep -q "not allowed"; then
    echo -e "${GREEN}✓ Correctly rejected invalid file type${NC}"
else
    echo -e "${RED}✗ Should have returned file type error${NC}"
fi
echo ""

echo "=========================================="
echo "Test Examples for Your Own Files"
echo "=========================================="
echo ""
echo "To test with your own PDF:"
echo "  curl -X POST $API_URL/process -F \"file=@/path/to/your/document.pdf\" | python3 -m json.tool"
echo ""
echo "To test with specific page range:"
echo "  curl -X POST $API_URL/process -F \"file=@/path/to/document.pdf\" -F \"page_range=1-3\" | python3 -m json.tool"
echo ""
echo "To test with your own image:"
echo "  curl -X POST $API_URL/process -F \"file=@/path/to/your/image.png\" | python3 -m json.tool"
echo ""
echo "To save the response to a file:"
echo "  curl -X POST $API_URL/process -F \"file=@document.pdf\" -o response.json"
echo ""

# Cleanup
rm -f /tmp/chandra_test.png /tmp/test.txt

echo "=========================================="
echo "Tests Complete!"
echo "=========================================="
