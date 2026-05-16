# Quick Answer: What Downloads Into the Container?

## Short Answer

**YES** - The Docker images NOW include the model! The ~20GB model is pre-downloaded during the Docker build process.

## What's Included in Docker Images

✅ **Included during build** (~25GB total per image):
- Python runtime
- All Python packages (Flask, transformers, pypdfium2, etc.)
- Application code
- System dependencies (gcc, git, etc.)
- **Chandra OCR model (~20GB) - PRE-CACHED** ⭐

## What Downloads at Runtime

✅ **Nothing!** The model is already in the image.

## Why Include Model in Image?

This deployment now uses **Option 1: Model Pre-Cached in Image**

**Advantages:**
1. ✅ **Instant startup** - No waiting for downloads
2. ✅ **Predictable deployment** - Same image = same model
3. ✅ **Works offline** - No internet required after build
4. ✅ **Simpler deployment** - Just run, no volume configuration

**Trade-offs:**
1. ⚠️ Large image size (~25GB per service)
2. ⚠️ Longer build time (15-20 minutes first build)
3. ⚠️ Requires internet during build (to download model)

## Build Process

### First Time Build
```
docker-compose build
  ↓
1. Pulls base images (Python, vLLM) - 2-5 minutes
2. Installs dependencies - 2-3 minutes
3. Downloads Chandra model (~20GB) - 10-15 minutes ⏱️
4. Caches model in image - 1 minute
5. Build complete ✅
```

**Total first build: 15-25 minutes**

### Startup After Build
```
docker-compose up
  ↓
1. Starts containers - 10 seconds
2. Loads pre-cached model into memory - 1-2 minutes
3. Ready to accept requests ✅
```

**Total startup: 2-3 minutes**

## Storage Requirements

Make sure you have:
- **Docker build cache**: 30GB
- **Final images**: 50GB (25GB × 2 services)
- **Working space**: 10GB
- **Total**: 90GB free disk space

## Network Requirements

- **Required**: During Docker build (to download model from HuggingFace)
- **Not required**: After build or during runtime
- **Download speed**: Varies (typically 50-200 MB/s from HuggingFace CDN)

## Build Commands

### Initial Build (with model download)
```bash
# Build both images with cached models
docker-compose build

# This downloads and caches the model in both images
# Takes 15-25 minutes on first build
```

### Quick Start
```bash
# Build images (first time: 15-25 min, includes model download)
docker-compose build

# Start services (startup: 2-3 min, model already cached)
docker-compose up -d

# Ready to use!
curl http://localhost:5000/health
```

## Monitoring Build Progress

```bash
# Watch build progress
docker-compose build --progress=plain

# You'll see:
# - Installing dependencies...
# - Downloading datalab-to/chandra-ocr-2...
# - Model cached successfully in image ✅
```

## Image Sizes

After build:
```bash
docker images | grep chandra

# chandra-api:cached    25GB
# chandra-vllm:cached   25GB
```

## Offline Usage

Once built, images work completely offline:
- ✅ No internet required to start
- ✅ No downloads during startup
- ✅ Model is already in the image
- ✅ Can deploy to air-gapped environments

## Comparison: Old vs New

### Old Approach (Runtime Download)
```
✗ First startup: 10-25 minutes
✗ Requires internet on every fresh deploy
✗ Unpredictable (depends on network)
✓ Smaller images (5GB)
```

### New Approach (Pre-Cached)
```
✓ First startup: 2-3 minutes
✓ Works offline after build
✓ Predictable performance
✗ Larger images (25GB)
✗ Longer build time (once)
```

## Summary

✅ **Model is now included** - Pre-downloaded during Docker build  
✅ **Instant startup** - No waiting for downloads  
✅ **Works offline** - After initial build  
⚠️ **Large images** - 25GB per service  
⚠️ **Longer build** - 15-25 minutes (one time)  

**Recommendation**: The pre-cached approach is better for production deployments where fast, predictable startup is more important than image size.

See [MODEL_DOWNLOAD.md](MODEL_DOWNLOAD.md) for more details about the caching mechanism.
