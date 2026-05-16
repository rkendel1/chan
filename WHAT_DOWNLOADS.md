# Quick Answer: What Downloads Into the Container?

## Short Answer

**NO** - The Docker image does NOT include everything. The ~20GB model is downloaded from HuggingFace on first startup.

## What's Included in Docker Image

✅ **Included during build** (~5GB total):
- Python runtime
- All Python packages (Flask, transformers, pypdfium2, etc.)
- Application code
- System dependencies (gcc, git, etc.)

## What Downloads at Runtime

⏰ **Downloaded on first startup** (~20GB, takes 5-15 minutes):
- Chandra OCR model weights
- Tokenizer files
- Model configuration

**Source**: HuggingFace Hub (`datalab-to/chandra-ocr-2`)

## Why Not Include Model in Image?

1. **Size**: Would make Docker image ~25GB (slow to build/push/pull)
2. **Flexibility**: Can easily switch model versions
3. **Updates**: Can update model without rebuilding image
4. **Standard practice**: Most ML Docker images work this way

## How to Avoid Re-downloading

The `docker-compose.yml` includes a volume mount:
```yaml
volumes:
  - ./models:/root/.cache/huggingface
```

This caches the model in the `./models` directory on your host:
- ✅ First startup: Downloads model (~20GB, 5-15 min)
- ✅ Subsequent startups: Uses cached model (instant)
- ✅ Persists across container restarts

## Timeline

### First Time
```
docker-compose up
  ↓
1. Pulls Docker images (5GB) - 2-5 minutes
2. Starts containers - 10 seconds
3. Downloads model from HuggingFace (20GB) - 5-15 minutes
4. Loads model into memory - 1-2 minutes
5. Ready to accept requests ✅
```

**Total first startup: 10-25 minutes**

### Subsequent Startups (with volume mount)
```
docker-compose up
  ↓
1. Starts containers - 10 seconds
2. Loads cached model into memory - 1-2 minutes
3. Ready to accept requests ✅
```

**Total: 2-3 minutes**

## Storage Requirements

Make sure you have:
- **Docker images**: 5GB
- **Model cache**: 25GB
- **Working space**: 5GB
- **Total**: 35GB free disk space

## Internet Requirements

- **Required**: First startup (to download model)
- **Not required**: After model is cached
- **Download speed**: Varies (typically 50-200 MB/s from HuggingFace CDN)

## Bottom Line

**The container downloads the model (~20GB) from HuggingFace on first startup**, but it's cached locally so you don't download it again. Everything else (Python packages, code) is included in the Docker image.

See [MODEL_DOWNLOAD.md](MODEL_DOWNLOAD.md) for detailed information about model downloads and caching.
