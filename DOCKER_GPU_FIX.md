# Docker GPU Error Fix

## Problem

When running `docker-compose up`, users without NVIDIA GPU or with improper GPU setup encountered this error:

```
Error response from daemon: could not select device driver "nvidia" with capabilities: [[gpu]]
```

## Solution

The docker-compose configuration has been updated to support two deployment modes:

### 1. CPU Mode (Default) - No GPU Required

This is now the **default mode** that works on any system without requiring GPU or NVIDIA drivers.

**Prerequisites:**
- Docker and Docker Compose
- **40GB+ free disk space** (for building)

**How to use:**
```bash
# Check disk space first
df -h

# Build the image
docker-compose build

# Start the service (CPU mode)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f chandra-api
```

> **⚠️ Disk Space:** If you see "no space left on device" errors during build, run `docker system prune -a -f` to clean up. See [DOCKER_DISK_SPACE.md](DOCKER_DISK_SPACE.md) for details.

**Features:**
- Uses HuggingFace backend
- No GPU required
- Works on any system
- Slower inference than GPU mode
- Model is pre-cached in Docker image (~20GB)

### 2. GPU Mode (Optional) - Requires NVIDIA GPU

For users with NVIDIA GPU and proper drivers, GPU mode offers much faster inference.

**Prerequisites:**
- NVIDIA GPU with CUDA support
- NVIDIA drivers (version 535+ recommended)
- NVIDIA Container Toolkit installed
- **70GB+ free disk space** (for building both images)

**How to use:**
```bash
# Build the images
docker-compose build

# Start services with GPU profile
docker-compose --profile gpu up -d

# Check status
docker-compose --profile gpu ps

# View logs
docker-compose --profile gpu logs -f chandra-api-gpu
```

**Features:**
- Uses vLLM backend for optimized inference
- Much faster than CPU mode
- Requires NVIDIA Container Toolkit
- Models are pre-cached in Docker images (~50GB total)

## Testing GPU Setup

Before using GPU mode, test your GPU setup:

```bash
docker run --rm --gpus all nvidia/cuda:13.0-base-ubuntu22.04 nvidia-smi
```

If this fails, you need to:
1. Install NVIDIA drivers
2. Install NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

## Common Warnings

### Image Pull Warnings

You may see warnings like:
```
! chandra-api Warning pull access denied for chandra-api, repository does not exist...
```

**This is normal!** These are local images that need to be built. Docker tries to pull from a registry before building. The warnings can be safely ignored as long as the build completes successfully.

To avoid these warnings:
```bash
# Build first
docker-compose build

# Then start
docker-compose up -d
```

## Migration Guide

### If you were previously using the default GPU mode:

**Old command:**
```bash
docker-compose up -d
```

**New command (to keep GPU mode):**
```bash
docker-compose --profile gpu up -d
```

### If you want to switch to CPU mode:

Simply use the new default:
```bash
docker-compose up -d
```

## API Compatibility

The API remains the same for both modes. Your existing API clients don't need any changes.

Both modes expose the API at `http://localhost:5000`

```bash
# Test the API
curl http://localhost:5000/health

# Process a document
curl -X POST http://localhost:5000/process \
  -F "file=@document.pdf" \
  | python -m json.tool
```

## Performance Comparison

| Mode | Inference Speed | GPU Required | Memory Usage |
|------|-----------------|--------------|--------------|
| CPU (Default) | Slower | No | ~20GB disk |
| GPU (Optional) | 5-10x faster | Yes | ~50GB disk + 16GB+ GPU |

## Support

For more details, see:
- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- [README.md](README.md) - Project overview and quickstart
- [TESTING.md](TESTING.md) - API testing examples
