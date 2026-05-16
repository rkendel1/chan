# Testing Chandra OCR HTTP API

This document provides examples and scripts for testing the Chandra OCR HTTP API locally.

## Quick Start - cURL Examples

### 1. Health Check

```bash
curl http://localhost:5000/health
```

### 2. API Information

```bash
curl http://localhost:5000/
```

### 3. Process a PDF File

```bash
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/your/document.pdf"
```

### 4. Process an Image File

```bash
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/your/image.png"
```

### 5. Process Specific Pages of a PDF

```bash
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/your/document.pdf" \
  -F "page_range=1-3"
```

### 6. Process with All Options

```bash
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/your/document.pdf" \
  -F "page_range=1-5,7,9-12" \
  -F "include_images=true" \
  -F "include_headers_footers=false" \
  -F "max_output_tokens=12384"
```

### 7. Save Response to File

```bash
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/your/document.pdf" \
  -o response.json
```

### 8. Pretty Print JSON Response

```bash
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/your/document.pdf" \
  | python -m json.tool
```

Or with `jq` (if installed):

```bash
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/your/document.pdf" \
  | jq '.'
```

## Python Test Script

See `test_api.py` for a comprehensive Python script that tests the API.

## Testing with Different File Types

### PDF
```bash
curl -X POST http://localhost:5000/process \
  -F "file=@sample.pdf"
```

### PNG
```bash
curl -X POST http://localhost:5000/process \
  -F "file=@sample.png"
```

### JPEG
```bash
curl -X POST http://localhost:5000/process \
  -F "file=@sample.jpg"
```

## Response Format

The API returns JSON in this format:

```json
{
  "success": true,
  "filename": "document.pdf",
  "num_pages": 2,
  "pages": [
    {
      "page_num": 0,
      "markdown": "# Document Title\n\nPage content...",
      "html": "<h1>Document Title</h1><p>Page content...</p>",
      "token_count": 1234,
      "page_box": [0, 0, 2480, 3508],
      "num_chunks": 15,
      "num_images": 2,
      "image_names": ["hash_1_img.webp", "hash_2_img.webp"]
    }
  ]
}
```

## Error Responses

### Missing File
```bash
curl -X POST http://localhost:5000/process
```
Response:
```json
{
  "error": "No file provided"
}
```

### Invalid File Type
```bash
curl -X POST http://localhost:5000/process \
  -F "file=@document.txt"
```
Response:
```json
{
  "error": "File type not allowed. Supported types: .pdf, .png, .jpg, ..."
}
```

## Performance Testing

### Using Apache Bench (ab)

First, save a test file upload as a request:

```bash
# Create multipart form data file
cat > test_request.txt << 'EOF'
POST /process HTTP/1.1
Host: localhost:5000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="test.pdf"
Content-Type: application/pdf

<BINARY_DATA_HERE>
------WebKitFormBoundary--
EOF
```

Then run load test:
```bash
ab -n 10 -c 2 -T 'multipart/form-data; boundary=----WebKitFormBoundary' \
  -p test_request.txt http://localhost:5000/process
```

### Using wrk (if installed)

```bash
wrk -t2 -c10 -d30s --timeout 60s http://localhost:5000/health
```

## Monitoring

### Watch logs in real-time

With Docker Compose:
```bash
docker-compose logs -f chandra-api
```

With standalone Docker:
```bash
docker logs -f <container-id>
```

### Check server status

```bash
watch -n 2 'curl -s http://localhost:5000/health | jq'
```
