# Docker Build Disk Space Issues

## Problem

If you see errors like these during `docker-compose build`:

```
ERROR [chandra-api] exporting to image
=> => exporting layers                                                           206.8s
------
> [chandra-api] exporting to image:
------
failed to solve: failed to create temp dir: mkdir /var/lib/desktop-containerd/daemon/tmpmounts/containerd-mount3740707538: input/output error: unknown
```

or

```
failed to solve: write /var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db: input/output error: unknown
no space left on device: /Users/randy/.z.11301
```

**This is a disk space issue**, not a Docker configuration problem. The build process requires significant disk space to:
1. Download the ~20GB Chandra OCR model from HuggingFace
2. Build Docker image layers (~5-10GB)
3. Store the final Docker image (~25GB for CPU mode, ~50GB for GPU mode)
4. Maintain Docker build cache and temporary files (~10-30GB)

## Quick Fix: Free Up Disk Space

### 1. Check Current Disk Space

```bash
# Check available disk space
df -h

# Look for your Docker data directory, usually:
# - Linux: /var/lib/docker
# - macOS: /Users/<username>/Library/Containers/com.docker.docker
# - Windows: C:\ProgramData\Docker
```

**Minimum Required:**
- **CPU mode only**: 40GB free space (25GB image + 15GB working space)
- **GPU mode (both images)**: 70GB free space (50GB images + 20GB working space)

### 2. Clean Up Docker Resources

Run these commands to free up space used by old Docker resources:

```bash
# Remove all stopped containers
docker container prune -f

# Remove all unused images (not just dangling ones)
docker image prune -a -f

# Remove all unused volumes
docker volume prune -f

# Remove all unused networks
docker network prune -f

# Remove build cache (can free 10-30GB!)
docker builder prune -a -f

# Nuclear option: Remove EVERYTHING (containers, images, volumes, cache)
# WARNING: This will remove all Docker data on your system!
docker system prune -a --volumes -f
```

After cleanup, check disk space again:
```bash
df -h
```

### 3. Rebuild the Image

Once you have sufficient disk space (40GB+ free):

```bash
# Build only the CPU image (default)
docker-compose build chandra-api

# Start the service
docker-compose up -d

# Verify it's running
docker-compose ps
docker-compose logs -f chandra-api
```

## Alternative Solutions

If you still don't have enough disk space after cleanup:

### Option 1: Skip Model Caching (Download at Runtime)

Modify the `Dockerfile` to skip downloading the model during build:

1. Edit `Dockerfile` and comment out lines 36-38:

```dockerfile
# Pre-download the model during build to cache it in the image
# This adds ~20GB to the image but makes startup immediate
# Note: Model will be downloaded at runtime if not cached during build
# RUN pip install --no-cache-dir huggingface-hub && \
#     (hf download datalab-to/chandra-ocr-2 && echo "Model cached successfully in image") || \
#     echo "WARNING: Model download failed during build (likely network issue). Model will be downloaded at runtime."
```

2. Build the image (now only ~5GB instead of ~25GB):

```bash
docker-compose build chandra-api
```

3. Start the service. **The model will download on first startup** (adds 5-10 minutes to first startup):

```bash
docker-compose up -d
```

**Pros:**
- Much smaller Docker image (~5GB vs ~25GB)
- Less disk space required for build (~20GB free vs ~40GB free)

**Cons:**
- First startup is slower (5-10 minutes to download model)
- Requires internet connection on first startup
- Model is downloaded to a Docker volume (still uses ~20GB disk space eventually)

### Option 2: Use External Model Storage

Mount the model from your host system instead of storing it in the image:

1. Download the model manually to your host:

```bash
# Create a directory for the model
mkdir -p ~/chandra-models

# Download the model (requires huggingface-hub)
pip install huggingface-hub
hf download datalab-to/chandra-ocr-2 --local-dir ~/chandra-models/chandra-ocr-2
```

2. Comment out model download in `Dockerfile` (see Option 1)

3. Modify `docker-compose.yml` to mount the model directory:

```yaml
services:
  chandra-api:
    # ... existing configuration ...
    volumes:
      - ~/chandra-models:/root/.cache/huggingface
```

4. Build and start:

```bash
docker-compose build chandra-api
docker-compose up -d
```

**Pros:**
- Smallest Docker image (~5GB)
- Model shared across rebuilds (no need to re-download)
- Can reuse model for local development

**Cons:**
- Requires manual model download
- More complex setup

### Option 3: Build on a System with More Disk Space

If none of the above options work:

1. Build the image on a machine with sufficient disk space
2. Export the image: `docker save chandra-api:cached > chandra-api.tar`
3. Transfer to your target machine (via USB drive, network, etc.)
4. Import on target machine: `docker load < chandra-api.tar`
5. Start the service: `docker-compose up -d`

## Checking Disk Space Usage

To see what's using disk space in Docker:

```bash
# Overall Docker disk usage
docker system df

# Detailed breakdown
docker system df -v

# Show all images and their sizes
docker images

# Show all containers and their sizes
docker ps -a -s

# Show all volumes
docker volume ls
```

## Prevention

To avoid running out of disk space in the future:

1. **Regularly clean up Docker resources** (weekly):
   ```bash
   docker system prune -f
   ```

2. **Monitor disk space** before building:
   ```bash
   df -h | grep -E "Filesystem|/dev/"
   ```

3. **Use multi-stage builds** (already implemented in this project)

4. **Consider using `--no-cache`** when rebuilding to avoid cache accumulation:
   ```bash
   docker-compose build --no-cache chandra-api
   ```

5. **Clean up after successful builds**:
   ```bash
   docker builder prune -f
   ```

## Additional Resources

- [Docker Disk Space Management](https://docs.docker.com/config/pruning/)
- [Docker System Prune Documentation](https://docs.docker.com/engine/reference/commandline/system_prune/)
- [HuggingFace Model Cache Management](https://huggingface.co/docs/huggingface_hub/guides/manage-cache)

## Still Having Issues?

If you've tried all the above and still can't build:

1. Check if you have at least 40GB free space: `df -h`
2. Run the nuclear cleanup: `docker system prune -a --volumes -f`
3. Try Option 1 (skip model caching) for a smaller image
4. Consider upgrading your disk or using external storage
5. Open an issue on GitHub with:
   - Output of `df -h`
   - Output of `docker system df`
   - Your operating system and Docker version
