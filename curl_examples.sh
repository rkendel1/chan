#!/bin/bash
# Quick reference for testing Chandra OCR API with curl
# Usage: ./curl_examples.sh [API_URL]

API_URL="${1:-http://localhost:5000}"

cat << EOF

╔════════════════════════════════════════════════════════════════╗
║          Chandra OCR API - Quick Curl Reference                ║
║                                                                ║
║  API URL: $API_URL                                             
╚════════════════════════════════════════════════════════════════╝

1. HEALTH CHECK
   Check if the API is running:
   
   curl $API_URL/health

2. API INFORMATION
   Get API details and supported formats:
   
   curl $API_URL/

3. PROCESS A PDF FILE
   Upload and process a PDF document:
   
   curl -X POST $API_URL/process \\
     -F "file=@document.pdf"

4. PROCESS AN IMAGE
   Upload and process an image:
   
   curl -X POST $API_URL/process \\
     -F "file=@image.png"

5. PROCESS SPECIFIC PDF PAGES
   Process only certain pages (e.g., pages 1-5):
   
   curl -X POST $API_URL/process \\
     -F "file=@document.pdf" \\
     -F "page_range=1-5"

6. PROCESS WITH OPTIONS
   Include all available options:
   
   curl -X POST $API_URL/process \\
     -F "file=@document.pdf" \\
     -F "page_range=1-3,5,7-10" \\
     -F "include_images=true" \\
     -F "include_headers_footers=false" \\
     -F "max_output_tokens=12384"

7. SAVE RESPONSE TO FILE
   Save the JSON response to a file:
   
   curl -X POST $API_URL/process \\
     -F "file=@document.pdf" \\
     -o response.json

8. PRETTY PRINT RESPONSE
   Format the JSON response for easy reading:
   
   curl -X POST $API_URL/process \\
     -F "file=@document.pdf" \\
     | python3 -m json.tool

   Or with jq (if installed):
   
   curl -X POST $API_URL/process \\
     -F "file=@document.pdf" \\
     | jq '.'

9. VERBOSE OUTPUT
   See full request/response headers:
   
   curl -v -X POST $API_URL/process \\
     -F "file=@document.pdf"

10. WITH TIMEOUT
    Set a timeout (useful for large files):
    
    curl --max-time 300 -X POST $API_URL/process \\
      -F "file=@document.pdf"

SUPPORTED FILE FORMATS:
  • PDF (.pdf)
  • PNG (.png)
  • JPEG (.jpg, .jpeg)
  • GIF (.gif)
  • WebP (.webp)
  • TIFF (.tiff)
  • BMP (.bmp)

OPTIONAL PARAMETERS:
  • page_range          - Pages to process (e.g., "1-5,7,9-12")
  • include_images      - Extract images (true/false, default: true)
  • include_headers_footers - Include headers/footers (true/false, default: false)
  • max_output_tokens   - Max tokens per page (integer)

RESPONSE FORMAT:
  {
    "success": true,
    "filename": "document.pdf",
    "num_pages": 3,
    "pages": [
      {
        "page_num": 0,
        "markdown": "# Title\\n\\nContent...",
        "html": "<h1>Title</h1><p>Content...</p>",
        "token_count": 1234,
        "num_chunks": 15,
        "num_images": 2
      }
    ]
  }

RUN AUTOMATED TESTS:
  • Bash script:   ./test_curl.sh $API_URL
  • Python script: ./test_api.py $API_URL

For more examples, see TESTING.md

EOF
