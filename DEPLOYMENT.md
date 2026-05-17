# Chandra OCR - Docker Deployment Guide

> **💰 NO PAID SERVICES REQUIRED**: This deployment runs completely locally on your infrastructure. No external APIs, no metered services, no recurring costs beyond your own hosting. See [NO_PAID_SERVICES.md](NO_PAID_SERVICES.md) for details.

> **📦 MODEL PRE-CACHED**: The ~20GB Chandra model is now downloaded during Docker build and included in the image. First build takes 15-25 minutes, but startup is then instant (2-3 minutes). See [WHAT_DOWNLOADS.md](WHAT_DOWNLOADS.md) for details.

This guide explains how to deploy Chandra OCR as a containerized HTTP API service that accepts file uploads.

## Quick Start

### Prerequisites (CPU Mode - Default)

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- **25GB free disk space** (for building image with cached model)
- **Internet connection** (for initial build to download model)

### Prerequisites (GPU Mode - Optional)

In addition to the above:
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit (for GPU access in Docker)
- **50GB free disk space** (for building both images with cached models)

### Build and Deploy (CPU Mode - Default)

This is the recommended mode if you don't have a GPU or encounter GPU driver errors:

```bash
# Build image (downloads model during build, takes 15-25 minutes first time)
docker-compose build

# Start service (CPU mode, no GPU required)
docker-compose up -d

# Check logs
docker-compose logs -f chandra-api

# Stop service
docker-compose down
```

The API will be available at `http://localhost:5000`

**Note:** CPU mode uses the HuggingFace backend which is slower than GPU mode but doesn't require NVIDIA drivers.

### Build and Deploy (GPU Mode - Optional)

If you have an NVIDIA GPU and properly configured drivers:

```bash
# Build images (downloads model during build, takes 15-25 minutes first time)
docker-compose build

# Start services with GPU profile
docker-compose --profile gpu up -d

# Check logs
docker-compose --profile gpu logs -f chandra-api-gpu

# Stop services
docker-compose --profile gpu down
```

The API will be available at `http://localhost:5000`

**Note:** GPU mode uses vLLM for much faster inference but requires NVIDIA Container Toolkit.

### Build Process

**CPU Mode (Default)**

First time build (15-25 minutes):
1. Downloads base Docker image (Python)
2. Installs Python dependencies
3. **Downloads Chandra model from HuggingFace (~20GB)**
4. Caches model in the image
5. Image is ready for instant deployment

Subsequent starts (30 seconds):
1. Container starts
2. Load pre-cached model from image into memory
3. Ready to process requests

**GPU Mode (Optional)**

First time build (15-25 minutes):
1. Downloads base Docker images (Python, vLLM)
2. Installs Python dependencies
3. **Downloads Chandra model from HuggingFace (~20GB)**
4. Caches model in both images
5. Images are ready for instant deployment

Subsequent starts (2-3 minutes):
1. Containers start
2. vLLM server loads pre-cached model into GPU memory
3. Ready to process requests

No downloads happen after the initial build!

### Manual Docker Build and Run

If you prefer to build and run manually:

```bash
# Build the API image
docker build -t chandra-api .

# Run with HuggingFace (CPU mode, no GPU required)
docker run -p 5000:5000 \
  -e INFERENCE_METHOD=hf \
  chandra-api

# Or run with vLLM (requires separate vLLM server)
docker run -p 5000:5000 \
  -e INFERENCE_METHOD=vllm \
  -e VLLM_API_BASE=http://your-vllm-server:8000/v1 \
  -e VLLM_MODEL_NAME=chandra \
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

### GPU Driver Error: "could not select device driver nvidia with capabilities: [[gpu]]"

This error occurs when:
1. NVIDIA drivers are not installed on your system
2. NVIDIA Container Toolkit is not installed
3. GPU is not properly configured

**Solution:** Use CPU mode (default) instead:

```bash
# Use CPU mode (default, no GPU required)
docker-compose build
docker-compose up -d
```

If you want to use GPU mode, ensure you have:
- NVIDIA GPU with CUDA support
- NVIDIA drivers installed on your host system (version 535+ recommended)
- NVIDIA Container Toolkit installed ([installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html))

Test your GPU setup:
```bash
docker run --rm --gpus all nvidia/cuda:13.0-base-ubuntu22.04 nvidia-smi
```

Once GPU is working, use:
```bash
docker-compose --profile gpu up -d
```

### Image Pull Warnings

If you see warnings like "pull access denied for chandra-api":

```
! chandra-api Warning pull access denied for chandra-api, repository does not exist...
```

**This is normal!** These are local images that need to be built first. Docker tries to pull from a registry before building. The warnings can be safely ignored as long as the build completes successfully.

To avoid these warnings and ensure images are built:
```bash
# Build images first
docker-compose build

# Then start services
docker-compose up -d
```

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
