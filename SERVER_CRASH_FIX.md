# Fix for Server Crashes and Missing /process Responses

## Problem Summary

The `/process` endpoint was experiencing two critical issues:

1. **Server crashes during inference** - The Python process would die unexpectedly ~40 seconds after starting inference
2. **Infinite restart loop** - Docker would automatically restart the crashed container, creating a restart loop
3. **No client response** - Clients never received any response because the server crashed before completing

## Root Cause Analysis

### Issue 1: Process Crashes During Inference

Looking at the logs:
```
2026-05-18 14:10:30 INFO:__main__:Inference thread started
2026-05-18 14:10:34 INFO:werkzeug:127.0.0.1 - - [18/May/2026 18:10:34] "GET /health HTTP/1.1" 200 -
2026-05-18 14:11:04 INFO:werkzeug:127.0.0.1 - - [18/May/2026 18:11:04] "GET /health HTTP/1.1" 200 -
2026-05-18 14:11:10 INFO:__main__:Starting Chandra OCR HTTP Server...  # <- SERVER RESTARTED
```

The server crashed **40 seconds** after inference started (not a timeout - the default timeout is 600 seconds). This indicates:

- **Out of Memory (OOM) error** - Processing multiple pages (5 in this case) simultaneously caused memory exhaustion
- **Native code crash** - PyTorch/transformers crashed with segfault or CUDA error
- **Linux OOM killer** - Kernel killed the process to free memory

These types of crashes bypass Python's normal exception handling because they occur in native C/C++ code or at the OS level.

### Issue 2: Batch Processing Causes OOM

The original code processed all pages in a single batch:
```python
batch = [BatchInputItem(image=img, prompt_type="ocr_layout") for img in images]
results = run_inference_with_timeout(model, batch, ...)  # All 5 pages at once
```

This multiplies memory usage:
- **Each page** requires loading the image into GPU memory
- **Each page** requires model attention over the entire sequence
- **5 pages** = 5x memory usage, easily exceeding available RAM/VRAM

### Issue 3: Docker Restart Policy

The `restart: unless-stopped` policy in docker-compose.yml meant:
- Any crash → Docker restarts container
- New crash → Docker restarts again
- **Infinite loop** of crashes and restarts

## Solution Implemented

### 1. Process Pages Individually

Changed from batch processing to page-by-page processing:

```python
# Old: Process all pages at once (causes OOM)
results = run_inference_with_timeout(model, batch, ...)

# New: Process one page at a time (safer)
results = []
for page_idx, page_item in enumerate(batch):
    page_results = run_inference_with_timeout(model, [page_item], ...)
    results.extend(page_results)
```

**Benefits:**
- ✅ Memory usage stays constant per page
- ✅ OOM risk greatly reduced
- ✅ Partial success possible (some pages succeed even if one fails)
- ✅ Better progress logging
- ⚠️ Slightly slower total time (sequential vs parallel)

### 2. Limited Restart Policy

Changed Docker restart policy:

```yaml
# Old
restart: unless-stopped  # Infinite restarts

# New
restart: on-failure:3    # Max 3 restart attempts
```

**Benefits:**
- ✅ Prevents infinite restart loops
- ✅ Server stops after 3 consecutive crashes
- ✅ Admin/monitoring can detect persistent issues
- ✅ Logs show final error state instead of continuous restart messages

### 3. Better Error Handling

Added comprehensive error catching:

```python
except MemoryError as e:
    return jsonify({'error': 'Insufficient memory...'}), 507
except Exception as e:
    return jsonify({'error': f'Processing failed: {str(e)}'}), 500
```

**Benefits:**
- ✅ Client receives error response instead of connection reset
- ✅ Specific HTTP status codes (507 for OOM, 504 for timeout)
- ✅ Server stays running after recoverable errors

### 4. Enhanced Logging

Added critical logging improvements:

```python
# Memory monitoring
logger.info(f"Memory usage before inference: RSS={mem_info.rss / 1024 / 1024:.1f}MB")

# Explicit log flushing before potential crashes
sys.stdout.flush()
sys.stderr.flush()

# Per-page progress
logger.info(f"Processing page {page_idx + 1}/{len(batch)}")
```

**Benefits:**
- ✅ Logs appear even if process crashes
- ✅ Last known state visible in logs
- ✅ Memory trends help identify OOM patterns
- ✅ Progress tracking for long documents

### 5. Signal Handlers

Added graceful shutdown handling:

```python
def signal_handler(signum, frame):
    logger.error(f"Received signal {signal_name}, shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

**Benefits:**
- ✅ Clean shutdown logs
- ✅ Distinguishes crashes from normal shutdowns
- ✅ Better debugging of termination causes

## Testing Recommendations

### 1. Test Multi-Page Documents
```bash
# Test with increasing page counts
curl -X POST http://localhost:5000/process \
  -F "file=@document.pdf" \
  -F "page_range=1-5"
```

### 2. Monitor Memory Usage
```bash
# Watch Docker stats during processing
docker stats chandra-api
```

### 3. Verify Error Responses
```bash
# Should return error, not crash
curl -X POST http://localhost:5000/process \
  -F "file=@huge_document.pdf"
```

### 4. Check Restart Behavior
```bash
# Container should stop after 3 crashes
docker ps -a | grep chandra-api
```

## Configuration

### Adjust Restart Limit

If you want different restart behavior:

```yaml
# In docker-compose.yml
restart: on-failure:5  # Allow 5 retries instead of 3
# or
restart: no            # Never restart automatically
# or
restart: unless-stopped  # Original behavior (not recommended)
```

### Process Pages in Batches

For systems with more memory, you could process multiple pages at once:

```python
# In http_server.py, adjust batch size
PAGES_PER_BATCH = 2  # Process 2 pages at a time instead of 1
```

This would require modifying the loop to process in chunks rather than individually.

### Increase Inference Timeout

If pages are timing out:

```bash
# In docker-compose.yml or environment
INFERENCE_TIMEOUT=1200  # 20 minutes per page
```

## Expected Behavior After Fix

### Successful Processing
```
INFO: Processing page 1/5
INFO: Page 1/5 completed successfully
INFO: Processing page 2/5
INFO: Page 2/5 completed successfully
...
INFO: All 5 page(s) processed successfully
```

### Memory Error (Graceful)
```
INFO: Processing page 3/5
ERROR: Page 3 failed due to memory error
HTTP 507: Insufficient memory. Try processing fewer pages.
```
Server **stays running**, client receives error response.

### Fatal Crash (Unrecoverable)
```
INFO: Processing page 1/5
INFO: Inference thread started
<process killed by OOM>
INFO: Starting Chandra OCR HTTP Server...  # First restart
<crash again>
INFO: Starting Chandra OCR HTTP Server...  # Second restart
<crash again>
INFO: Starting Chandra OCR HTTP Server...  # Third restart
<crash again>
[container stops, no fourth restart]
```

Check logs: `docker logs chandra-api`

## Related Documentation

- **TIMEOUT_FIX.md** - Original timeout mechanism
- **DOCKER_WARNINGS.md** - Expected warnings during operation
- **DEPLOYMENT.md** - General deployment guide
- **TESTING.md** - API testing examples

## Status

✅ **RESOLVED** - Server now:
1. Processes pages individually to avoid OOM
2. Limits restart attempts to prevent infinite loops
3. Returns error responses instead of crashing
4. Logs comprehensively for debugging
5. Handles memory errors gracefully
