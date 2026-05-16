# Model Download Behavior

## Important: Model Downloads at Runtime

⚠️ **The Chandra OCR model (~20GB) is NOT included in the Docker image.**

The model is downloaded from HuggingFace Hub when:
- The container starts for the first time (vLLM mode)
- The first API request is made (HuggingFace mode)

## What Gets Downloaded

| Component | Size | Source | When |
|-----------|------|--------|------|
| **Python packages** | ~2GB | PyPI | During Docker build ✅ |
| **Chandra model** | ~20GB | HuggingFace Hub | At runtime ⏰ |
| **Tokenizer files** | ~5MB | HuggingFace Hub | At runtime ⏰ |

## Why Models Are Downloaded at Runtime

**Size**: Including the ~20GB model in the Docker image would make it huge and slow to distribute.

**Updates**: Downloading at runtime allows you to easily update to newer model versions.

**Flexibility**: You can point to different model checkpoints without rebuilding the image.

## Where Models Are Stored

### vLLM Mode (Default)
Models are cached in the vLLM container:
```
/root/.cache/huggingface/hub/
```

### HuggingFace Mode
Models are cached in the API container:
```
/root/.cache/huggingface/hub/
```

## Persistent Model Storage

To avoid re-downloading the model every time you restart containers, **mount a volume** for the model cache.

### Option 1: Update docker-compose.yml (Recommended)

Add volume mounts to persist the model cache:

```yaml
services:
  vllm-server:
    # ... existing config
    volumes:
      - ./models:/root/.cache/huggingface  # Persist models locally
    # ... rest of config

  chandra-api:
    # ... existing config
    volumes:
      - ./models:/root/.cache/huggingface  # For HF mode
    # ... rest of config
```

The docker-compose.yml already includes this volume mount:
```yaml
volumes:
  - ./models:/root/.cache/huggingface
```

### Option 2: Manual Docker Run

```bash
# Create local cache directory
mkdir -p ./models

# Run with volume mount
docker run -v $(pwd)/models:/root/.cache/huggingface \
  -p 5000:5000 chandra-api
```

## First Startup Timeline

### With vLLM (GPU required)

```
1. Container starts (instant)
2. vLLM downloads model from HuggingFace (~20GB) ⏱️ 5-15 minutes
3. vLLM loads model into GPU memory ⏱️ 1-2 minutes
4. HTTP API becomes available ✅
```

### With HuggingFace (CPU/GPU)

```
1. Container starts (instant)
2. HTTP API becomes available ✅
3. First API request triggers model download (~20GB) ⏱️ 5-15 minutes
4. Model loads into memory ⏱️ 1-2 minutes
5. Request completes ✅
```

## Pre-downloading the Model

To download the model before starting the service:

### Option 1: Using Python

```bash
# Install dependencies
pip install transformers torch

# Download model
python -c "
from transformers import AutoModelForImageTextToText, AutoProcessor
model = AutoModelForImageTextToText.from_pretrained('datalab-to/chandra-ocr-2')
processor = AutoProcessor.from_pretrained('datalab-to/chandra-ocr-2')
print('Model downloaded successfully')
"
```

### Option 2: Using HuggingFace CLI

```bash
# Install HuggingFace CLI
pip install huggingface-hub

# Download model
hf download datalab-to/chandra-ocr-2
```

### Option 3: Manual Download to Volume

```bash
# Create models directory
mkdir -p ./models

# Set cache location and download
export HF_HOME=$(pwd)/models
python -c "
from transformers import AutoModelForImageTextToText
AutoModelForImageTextToText.from_pretrained('datalab-to/chandra-ocr-2')
"

# Now start Docker with the pre-downloaded model
docker-compose up -d
```

## Network Requirements

**First startup requires internet access** to download from:
- `huggingface.co` - Model files
- `cdn.huggingface.co` - CDN for faster downloads

**After the model is downloaded:**
- No internet required (if using local vLLM)
- Models are cached locally
- Can run completely offline

## Monitoring Download Progress

### vLLM Container
```bash
# Watch vLLM logs to see download progress
docker-compose logs -f vllm-server
```

You'll see output like:
```
Downloading model: datalab-to/chandra-ocr-2
Downloading: 100%|██████████| 20.1G/20.1G [05:32<00:00, 60.4MB/s]
Loading model...
Model loaded successfully
```

### HuggingFace Mode
```bash
# Watch API logs
docker-compose logs -f chandra-api
```

## Storage Requirements

Ensure you have enough disk space:
- **Docker images**: ~5GB
- **Model cache**: ~25GB (models + tokenizers)
- **Total recommended**: 35GB free space

## Offline Usage

Once downloaded, the model is cached locally. To use offline:

1. Download model once while online
2. Use volume mounts to persist the cache
3. Containers will use cached model on subsequent starts
4. No internet required after initial download

## Troubleshooting

### "Connection Error" on First Start
- **Cause**: Can't reach HuggingFace Hub
- **Solution**: Check internet connection, try again

### "Disk quota exceeded"
- **Cause**: Not enough disk space for model
- **Solution**: Free up 30GB+ space

### "Model downloads every time"
- **Cause**: Volume mount not configured
- **Solution**: Add volume mount as shown above

### Slow Download
- **Cause**: Slow internet connection
- **Solution**: Be patient (5-15 minutes is normal) or use a faster connection

## Summary

✅ **Python packages** - Included in Docker image  
⏰ **Model files** - Downloaded on first use (~20GB, 5-15 minutes)  
💾 **Persist with volumes** - Avoid re-downloading  
🌐 **Requires internet** - Only for initial model download  
📦 **Cache location** - `/root/.cache/huggingface/hub/`

**Recommendation**: Use volume mounts (already configured in docker-compose.yml) to cache the model locally and avoid re-downloading on container restarts.
