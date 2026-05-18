# Fix for Failed to Fetch Results Issue

## Problem
The `/process` endpoint was failing to return results when processing documents. The logs showed that inference started but never completed, causing requests to hang indefinitely without returning a response.

## Root Cause
The `model.generate()` call could hang indefinitely without any timeout mechanism, causing the HTTP request to never complete. This could happen due to:
- Complex or malformed documents causing the model to get stuck
- Resource constraints or memory issues
- Model generation entering an infinite loop
- External process timeouts not being propagated

## Solution
Added a robust timeout mechanism with better error handling:

### 1. Inference Timeout Wrapper
- Wrapped `model.generate()` in a thread-based timeout mechanism
- Default timeout: 600 seconds (10 minutes) - configurable via `INFERENCE_TIMEOUT` environment variable
- Returns HTTP 504 Gateway Timeout if inference exceeds the timeout
- Properly propagates exceptions from the inference thread

### 2. Improved Logging
- Added detailed logging at each stage of processing
- Added log flushing to prevent buffering issues
- Added thread-level logging to track inference progress
- Logs now clearly show when timeout occurs

### 3. Better Error Handling
- Specific handling for timeout errors with user-friendly messages
- Better exception propagation from inference thread
- Clearer error messages for debugging

## Usage

### Default Behavior
The timeout is set to 600 seconds (10 minutes) by default:
```bash
docker-compose up
```

### Custom Timeout
Set the `INFERENCE_TIMEOUT` environment variable to change the timeout (in seconds):
```bash
docker-compose up -e INFERENCE_TIMEOUT=300  # 5 minutes
```

Or in docker-compose.yml:
```yaml
services:
  chandra-api:
    environment:
      - INFERENCE_TIMEOUT=300
```

## Testing
A test suite has been added to verify the timeout mechanism works correctly:
```bash
python3 tests/test_timeout_mechanism.py
```

The test verifies:
1. Long-running inference correctly times out
2. Fast inference completes successfully
3. Exceptions are properly propagated

## Response Codes
- **200 OK**: Successful processing
- **504 Gateway Timeout**: Processing exceeded the timeout
- **500 Internal Server Error**: Other processing errors
- **503 Service Unavailable**: Model not loaded or initializing

## Monitoring
Check logs for timeout issues:
```bash
docker-compose logs -f chandra-api | grep -i "timeout\|inference"
```

## Known Limitations
- The timeout mechanism uses threads, which cannot be forcefully killed in Python
- If inference hangs, the thread will continue running in the background until completion
- However, the HTTP request will return an error to the user, preventing the client from hanging
