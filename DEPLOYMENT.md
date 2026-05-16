# Chandra OCR - Docker Deployment Guide

> **💰 NO PAID SERVICES REQUIRED**: This deployment runs completely locally on your infrastructure. No external APIs, no metered services, no recurring costs beyond your own hosting. See [NO_PAID_SERVICES.md](NO_PAID_SERVICES.md) for details.

> **📦 MODEL DOWNLOAD**: The ~20GB Chandra model is downloaded from HuggingFace on first startup (5-15 minutes). It's cached locally for subsequent runs. See [MODEL_DOWNLOAD.md](MODEL_DOWNLOAD.md) for details.

This guide explains how to deploy Chandra OCR as a containerized HTTP API service that accepts file uploads.

## Quick Start

### Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- NVIDIA GPU with CUDA support (for vLLM mode)
- NVIDIA Container Toolkit (for GPU access in Docker)

### Option 1: Using Docker Compose with vLLM (Recommended for Production)

This setup runs a vLLM server for optimized inference and the Chandra HTTP API.

```bash
# Start both vLLM server and Chandra API
docker-compose up -d

# Check logs
docker-compose logs -f chandra-api

# Stop services
docker-compose down
```

The API will be available at `http://localhost:5000`

### Option 2: Using Docker with HuggingFace Backend

For development or when GPU resources are limited:

```bash
# Start only the HuggingFace-based API
docker-compose --profile hf up -d chandra-api-hf

# Or build and run directly
docker build -t chandra-api .
docker run -p 5000:5000 -e INFERENCE_METHOD=hf chandra-api
```

### Option 3: Build and Run Docker Manually

```bash
# Build the image
docker build -t chandra-api .

# Run with vLLM (requires separate vLLM server)
docker run -p 5000:5000 \
  -e INFERENCE_METHOD=vllm \
  -e VLLM_API_BASE=http://your-vllm-server:8000/v1 \
  -e VLLM_MODEL_NAME=chandra \
  chandra-api

# Run with HuggingFace
docker run -p 5000:5000 \
  -e INFERENCE_METHOD=hf \
  chandra-api
```

## API Usage

### Health Check

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### API Information

```bash
curl http://localhost:5000/
```

### Process a Document

Upload a file for OCR processing:

```bash
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/document.pdf" \
  -F "page_range=1-5" \
  -F "include_images=true" \
  -F "include_headers_footers=false"
```

Response:
```json
{
  "success": true,
  "filename": "document.pdf",
  "num_pages": 5,
  "pages": [
    {
      "page_num": 0,
      "markdown": "# Document Content\n\nPage text...",
      "html": "<h1>Document Content</h1><p>Page text...</p>",
      "token_count": 1234,
      "page_box": [0, 0, 2480, 3508],
      "num_chunks": 15,
      "num_images": 2,
      "image_names": ["abc123_1_img.webp", "abc123_2_img.webp"]
    }
  ]
}
```

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | file | required | Document file (PDF, PNG, JPG, etc.) |
| `page_range` | string | all pages | Page range for PDFs (e.g., "1-5,7,9-12") |
| `include_images` | boolean | true | Extract and include image metadata |
| `include_headers_footers` | boolean | false | Include page headers and footers |
| `max_output_tokens` | integer | 12384 | Maximum output tokens per page |

### Supported File Formats

- PDF (.pdf)
- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- WebP (.webp)
- TIFF (.tiff)
- BMP (.bmp)

## Environment Variables

### HTTP Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HTTP_HOST` | 0.0.0.0 | Server bind address |
| `HTTP_PORT` | 5000 | Server port |
| `HTTP_DEBUG` | false | Enable debug mode |

### Inference Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `INFERENCE_METHOD` | vllm | Inference method (vllm or hf) |
| `MODEL_CHECKPOINT` | datalab-to/chandra-ocr-2 | Model checkpoint |
| `MAX_OUTPUT_TOKENS` | 12384 | Maximum output tokens per page |

### vLLM Configuration (when using vLLM method)

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_API_BASE` | http://vllm-server:8000/v1 | vLLM server URL |
| `VLLM_MODEL_NAME` | chandra | Model name on vLLM server |
| `VLLM_GPUS` | 0 | GPU device IDs |

## Production Deployment

### Scaling with Multiple Workers

For high-throughput production deployments:

```yaml
# docker-compose.yml
services:
  chandra-api:
    # ... existing config
    deploy:
      replicas: 3
    environment:
      - VLLM_API_BASE=http://vllm-server:8000/v1
```

### Using an External vLLM Server

If you already have a vLLM server running:

```bash
docker run -p 5000:5000 \
  -e INFERENCE_METHOD=vllm \
  -e VLLM_API_BASE=http://your-vllm-server.example.com:8000/v1 \
  -e VLLM_MODEL_NAME=chandra \
  chandra-api
```

### Behind a Reverse Proxy (nginx)

Example nginx configuration:

```nginx
upstream chandra_api {
    server localhost:5000;
}

server {
    listen 80;
    server_name ocr.example.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://chandra_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for large files
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
```

## Troubleshooting

### vLLM Server Not Starting

Ensure you have:
- NVIDIA GPU with sufficient memory (16GB+ recommended)
- NVIDIA Container Toolkit installed
- Proper GPU access in Docker

Test GPU access:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Out of Memory Errors

- Reduce `--max-model-len` in vLLM configuration
- Process fewer pages at once
- Use HuggingFace backend with smaller batch sizes

### Slow Inference

- Use vLLM instead of HuggingFace backend
- Increase GPU memory allocation
- Use multiple workers for vLLM
- Enable Flash Attention (installed by default in vLLM)

### Connection Refused Errors

- Check that the vLLM server is running: `docker-compose ps`
- Verify network connectivity: `docker-compose logs vllm-server`
- Ensure `VLLM_API_BASE` points to the correct URL

## Development

### Running Locally Without Docker

```bash
# Install dependencies
pip install -e .
pip install flask

# Start vLLM server separately (or use remote server)
chandra_vllm

# Run HTTP server
python -m chandra.scripts.http_server
```

### Testing the API

```bash
# Using curl
curl -X POST http://localhost:5000/process \
  -F "file=@test.pdf"

# Using Python requests
import requests

with open('test.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/process',
        files={'file': f},
        data={'include_images': 'true'}
    )
    print(response.json())
```

## Security Considerations

- The default configuration accepts files up to 50MB
- Only specified file types are allowed
- Use HTTPS in production (configure reverse proxy)
- Consider implementing authentication/authorization
- Rate limiting recommended for public deployments
- Validate and sanitize file uploads

## License

See [LICENSE](LICENSE) and [MODEL_LICENSE](MODEL_LICENSE) for details on code and model licensing.
